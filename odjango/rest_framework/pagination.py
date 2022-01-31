import logging
from collections import OrderedDict

from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from rest_framework import serializers


logger = logging.getLogger(__name__)


class PaginationError(Exception):
    pass


class OPaginationSerializer(serializers.Serializer):
    draw = serializers.IntegerField(default=None)
    start = serializers.IntegerField(default=0)
    length = serializers.IntegerField(default=None)

    def to_internal_value(self, data):
        pagination_data = dict()
        for field in ("draw", "start", "length"):
            if field in data:
                pagination_data[field] = data[field]
        return super().to_internal_value(pagination_data)


class OPagination(BasePagination):
    default_max_length = 1000  # fixme: put this a a plugin variable
    # https://www.django-rest-framework.org/api-guide/pagination/#setting-the-pagination-style

    draw = None
    length = None
    records_total = None
    records_filtered = None
    start = None
    error = None

    def _get_pagination_serializer_data(self, request):
        # get data
        if request.method == "GET":
            data = request.query_params
        elif request.method == "POST":
            data = request.data
        else:
            raise PaginationError("Unknown method for datatable method: %s." % request.method)

        pagination_serializer = OPaginationSerializer(data=data)
        pagination_serializer.is_valid(raise_exception=True)
        return pagination_serializer.validated_data

    def _get_max_length(self, view):
        return (self.default_max_length if (view is None or not (hasattr(view, "pagination_max_length"))) else
                view.pagination_max_length)

    def _get_length(self, view, data):
        max_length = self._get_max_length(view)
        return max_length if data["length"] is None else min(max_length, data["length"])

    def _set_data(self, data, view=None):
        self.length = self._get_length(view, data)
        self.draw = data["draw"]
        self.start = data["start"]

    def _filter_data(self, l):
        return l[self.start:-1 if (self.length == -1) else self.start+self.length]

    def paginate_list(self, l, request, view=None):
        # transform generator to list, if needed
        l = list(l)

        # serializer
        data = self._get_pagination_serializer_data(request)

        # set data
        self._set_data(data, view)

        self.records_total = (len(l) if ((view is None) or (not hasattr(view, "datatables_records_total")))
                              else view.datatables_records_total)  # has been monkey patched if datatables filter
        self.records_filtered = len(l)

        return self._filter_data(l)

    def paginate_queryset(self, queryset, request, view=None):
        # check queryset is ordered
        if not queryset.ordered:
            #  queryset is not ordered, and order may be non-deterministic. We force ordering to pk.
            # https://docs.djangoproject.com/en/2.2/topics/pagination/#paginator-objects
            # to order on a more relevant field, you may for example use ordering model Meta:
            #   https://docs.djangoproject.com/en/2.2/ref/models/options/#ordering
            queryset = queryset.order_by("-pk")

        # serializer
        data = self._get_pagination_serializer_data(request)

        # set data
        self._set_data(data, view)

        count = queryset.count()
        self.records_total = (count if ((view is None) or (not hasattr(view, "datatables_records_total")))
                              else view.datatables_records_total)  # has been monkey patched if datatables filter
        self.records_filtered = count

        return self._filter_data(queryset)

    def get_paginated_response(self, data):
        # fixme: add page num and number of records returned (max and current page)
        return Response(OrderedDict([
            ("draw", self.draw),
            ("recordsTotal", self.records_total),
            ("recordsFiltered", self.records_filtered),
            ("start", self.start),
            ("data", data)
        ]))

    def to_html(self):
        raise RuntimeError('not implemented')
