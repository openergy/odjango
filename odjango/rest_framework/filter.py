import logging
from operator import itemgetter

from django.db import models
from django.core.exceptions import FieldError

from rest_framework import serializers
from rest_framework.filters import BaseFilterBackend

logger = logging.getLogger(__name__)


class FilterError(Exception):
    pass


class OrderSerializer(serializers.Serializer):
    column = serializers.IntegerField()
    dir = serializers.ChoiceField(["asc", "desc"])


class ColumnSerializer(serializers.Serializer):
    data = serializers.CharField()
    name = serializers.CharField(allow_blank=True)
    searchable = serializers.BooleanField()
    orderable = serializers.BooleanField()
    search_value = serializers.CharField(allow_blank=True)
    search_regex = serializers.CharField(allow_blank=True)


class DatatablesFilterSerializer(serializers.Serializer):
    """
    https://www.datatables.net/manual/server-side
    """
    search_value = serializers.CharField(allow_blank=True)
    search_regex = serializers.CharField(allow_blank=True)
    order = serializers.ListField(child=OrderSerializer())
    columns = serializers.ListField(child=ColumnSerializer())

    def to_internal_value(self, data):
        datatables_data = dict()

        # search value and regex
        datatables_data["search_value"] = data["search[value]"]
        datatables_data["search_regex"] = data["search[regex]"]

        # order
        order = []
        i = 0
        while True:
            # create dict
            try:
                _order = dict(column=data["order[%i][column]" % i])
            except KeyError:
                break

            # fill info
            _order["dir"] = data["order[%i][dir]" % i]

            # store
            order.append(_order)

            # increment
            i += 1
        datatables_data["order"] = order

        # columns
        columns = []
        i = 0
        while True:
            # create dict
            try:
                col = dict(data=data["columns[%i][data]" % i])
            except KeyError:
                break

            # skip if column doesn't have data
            if col["data"] != "":
                # fill info
                col["name"] = data["columns[%i][name]" % i]
                col["searchable"] = data["columns[%i][searchable]" % i]
                col["orderable"] = data["columns[%i][orderable]" % i]
                col["search_value"] = data["columns[%i][search][value]" % i]
                col["search_regex"] = data["columns[%i][search][regex]" % i]

                # store
                columns.append(col)

            # increment
            i += 1
        datatables_data["columns"] = columns

        return super().to_internal_value(datatables_data)


class DatatablesFilterBackend(BaseFilterBackend):
    """
    https://www.datatables.net/manual/server-side
    """
    @classmethod
    def _get_raw_data(cls, request):
        """
        will return None if method is not a datatables filter method
        """
        if (request.content_type == "application/json") and (request.method.lower() == "post"):
            return request.data
        else:
            return request.query_params

    @classmethod
    def is_draw(cls, data):
        return "draw" in data

    @classmethod
    def _get_filter_serializer_data(cls, raw_data):
        filter_serializer = DatatablesFilterSerializer(data=raw_data)
        filter_serializer.is_valid(raise_exception=True)
        return filter_serializer.validated_data

    @classmethod
    def filter_list(cls, request, l, view):
        """
        list contain objects (with attributes, not items)
        filter is applied if and only if 'draw' is in query_params
        datatables_records_total: is monkey-patched to view
        filter should be applied after django-filter (so datatables_records_total is meaningful)
        """
        # TODO: implement per-column filtering
        # get data
        raw_data = cls._get_raw_data(request)

        # check if filter is applied
        if (raw_data is None) or (not cls.is_draw(raw_data)):
            return l

        # transform generator to list, if needed
        l = list(l)

        # serialize and check validity
        data = cls._get_filter_serializer_data(raw_data)

        # monkey patch view to store records_total
        view.datatables_records_total = len(l)

        # filter in columns
        # TODO: manage errors => client error not server error
        # TODO: implement nested
        search_value = data['search_value']
        columns = data["columns"]
        if search_value != "":
            filtered_list = []
            for item in l:
                for c in columns:
                    if c['searchable']:
                        obj_attr = item.get(c['data'])
                        if obj_attr is None:
                            pass
                        elif not isinstance(obj_attr, str):
                            raise RuntimeError('not implemented type: %s' % type(obj_attr))
                        else:
                            # todo: make accent insensitive
                            if search_value.lower() in str(obj_attr).lower():
                                filtered_list.append(item)
                                break
            l = filtered_list

        # order
        # TODO: manage errors => client error not server error
        # TODO: implement nested
        for o in data["order"]:
            # get column
            column = data["columns"][o["column"]]

            # get direction
            reverse = o["dir"] == "desc"  # serializer has already checked it was asc or desc

            # check is orderable
            if not column["orderable"]:
                logger.error(
                    "was asked to order a non-orderable column did not order",
                    extra=dict(column=column["data"])
                )
                continue

            # order
            # https://docs.python.org/3.5/howto/sorting.html#sortinghowto
            # TODO: catch attribute error here
            try:
                l = sorted(l, key=itemgetter(column["data"]), reverse=reverse)
            except KeyError:
                msg = "Unknown sort key: '%s'." % column["data"]
                if len(l) > 0:
                    msg += "\n(Available keys for object 0: %s.)" % list(l[0].keys())
                raise serializers.ValidationError(detail=msg)

        return l

    def filter_queryset(self, request, queryset, view):
        """
        filter is applied if and only if 'draw' is in query_params
        datatables_records_total: is monkey-patched to view
        filter should be applied after django-filter (so datatables_records_total is meaningful)
        """
        # TODO: implement per-column filtering
        # get raw data
        raw_data = self._get_raw_data(request)

        # check if filter is applied
        if (raw_data is None) or (not self.is_draw(raw_data)):
            return queryset

        # serialize and check validity
        data = self._get_filter_serializer_data(raw_data)

        # monkey patch view to store records_total
        view.datatables_records_total = queryset.count()

        # filter
        if data["search_value"] != "":
            q = models.Q()
            for column in data["columns"]:
                if not column["searchable"]:
                    continue
                filter_name = column["data"].replace(".", "__")
                # todo: make accent insensitive
                q |= models.Q(**{"%s__icontains" % filter_name: data["search_value"]})
            try:
                queryset = queryset.filter(q)
            except FieldError as e:
                raise serializers.ValidationError(detail=str(e)) from None

        # order
        # TODO: manage errors => client error not server error
        order_fields = []
        for o in data["order"]:
            # get column name
            column = data["columns"][o["column"]]

            # check is orderable
            if not column["searchable"]:
                logger.error(
                    "was asked to order a non-orderable column did not order",
                    extra=dict(column=column["data"])
                )
                continue

            # store ordering field
            order_fields.append("%s%s" % ("" if o["dir"] == "asc" else "-", column["data"].replace(".", "__")))

        if len(order_fields) > 0:
            queryset = queryset.order_by(*order_fields)

        return queryset
