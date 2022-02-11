from collections import OrderedDict

from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django import __version__ as django_version

from odjango.django import build_absolute_path


STANDARD_ACTIONS = ("create", "retrieve", "list", "update", "partial_update", "destroy")


class MultipleSerializerViewSet(GenericViewSet):
    """
    user mixins: from rest_framework.viewsets import mixins
    """
    flat_serializer_class = None
    retrieve_serializer_class = None
    list_serializer_class = None

    def get_serializer_class(self):
        if self.serializer_class is not None:
            return super().get_serializer_class()

        if self.action == "retrieve":
            return self.retrieve_serializer_class
        if self.action == "list":
            return self.list_serializer_class
        elif self.action in ("create", "update", "partial_update", "destroy"):
            return self.flat_serializer_class
        return self.flat_serializer_class


class PermissionViewSet(MultipleSerializerViewSet):
    # ------------------------------------- methods for dev to subclass ------------------------------------------------
    def perm_action_ok(self):
        """
        * purpose: validate action, depends on self.request.user and self.action. No need to check query dict in case
            of create or update: will be done later.
        * concerned actions: all

        Returns
        -------
        None if ok, else message

        Checklist
        ---------
        In a standard approach, this step can be skipped, already coded beneath.

        """
        if self.action == "update":
            return "update action forbidden, use partial_update"

    def perm_create_ok(self, query_dict):
        """
        * purpose: validate user can create object, looking at it's rights and at the given kwargs
        * concerned actions: create

        Returns
        -------
        None if ok, else message

        Checklist
        ---------
        If all fields are not available to creation, check no forbidden fields and return message to explain problem if
        refused.
        """
        raise Exception("not implemented")

    def perm_filter_queryset(self, queryset):
        """
        * purpose: must return all potential available objects: filter by organization, by project, ... depending on
            rights
        * concerned actions: all except create (think about what list must return, and it should be ok)
        * additional info: is applied after get_query_set and backend filters

        Checklist
        ---------
        Distinguish actions :
        * retrieve, list: read rights
        * partial_update: write rights
        * destroy: delete rights

        """
        return queryset.none()

    def perm_get_object_ok(self, obj):
        """
        * purpose: validate action by user on object, knowing we are in an authorized action, and that the base queryset
            has been filtered
        * concerned actions: retrieve, update, partial_update, destroy

        Returns
        -------
        None if ok, else message

        Checklist
        ---------
        If filter_queryset has been correctly coded, nothing should be necessary here. May however be used to calculate
        more precise rights and attach them on object.
        """
        raise Exception("not implemented")

    def perm_update_ok(self, query_dict, obj):
        """
        * purpose: validate update kwargs are ok (knowing that action is authorized for given object)
        * concerned actions: update, partial_update

        Returns
        -------
        None if ok, else message

        Checklist
        ---------
        Must check update fields are authorized. Usually two types of fields to check : admin fields and update fields.
        """
        raise Exception("not implemented")

    # ------------------------------------------- bypass methods -------------------------------------------------------
    def get_queryset_bypass_perms(self):
        return super().get_queryset()

    # ------------------------------------ methods for admin to subclass -----------------------------------------------

    def _perm_action_ok(self):
        return self.perm_action_ok()

    # ---------------------------------------------- admin methods -----------------------------------------------------
    def get_queryset(self):
        q = super().get_queryset()

        if str(self.request.query_params.get("empty", "false")).lower() == "true":
            return q.none()

        # apply permission filter
        return self.perm_filter_queryset(q)

    def check_permissions(self, request):
        super().check_permissions(request)

        # apply action check
        message = self._perm_action_ok()
        if message is not None:
            self.permission_denied(self.request, message=message)

        # apply specific actions check
        if self.action == "create":
            # hack that is maybe useless...
            data = self.request.data.copy()
            if isinstance(data, dict):
                data.pop("csrfmiddlewaretoken", None)
            message = self.perm_create_ok(data)
            if message is not None:
                self.permission_denied(self.request, message=message)

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)

        # apply permission check
        message = self.perm_get_object_ok(obj)
        if message is not None:
            self.permission_denied(self.request, message=message)

        # check partial updates (depending on query set)
        if self.action == "partial_update":
            message = self.perm_update_ok(self.request.data, obj)
            if message is not None:
                self.permission_denied(self.request, message=message)


def get_api_main_view(
        name,
        version=None,
        with_standard_docs=True,
        with_paths=True
):
    import inspect
    frm = inspect.stack()[1]
    urls = inspect.getmodule(frm[0])

    def main_view(request, format=None):
        content = OrderedDict()
        content["name"] = name
        if version is not None:
            content["version"] = version

        # prepare path
        current_path = build_absolute_path(request)

        if with_standard_docs:
            content["docs"] = current_path + "docs/"

        # make urls
        isolated_view_names, endpoint_names = [], []
        if with_paths:
            # find views and endpoints
            if int(django_version[0]) >= 2:
                isolated_view_names = [u.pattern._regex[1:] for u in urls.urlpatterns][1:]
            else:
                isolated_view_names = [u._regex[1:] for u in urls.urlpatterns][1:]
            if hasattr(urls, "router"):
                isolated_view_names = isolated_view_names[:-1]
                endpoint_names = [k[0] for k in urls.router.registry]
            isolated_view_names = set([n.strip('/$?') for n in isolated_view_names])

            # format
            content["paths"] = [
                _format_url(current_path, k, is_endpoint=False) for k in sorted(isolated_view_names)] + [
                _format_url(current_path, k, is_endpoint=True) for k in sorted(endpoint_names)
            ]

        return Response(content)

    main_view.__name__ = name

    # decorate
    main_view = api_view(["GET"])(main_view)

    return main_view


INDENT = 30


def _format_url(current_path, relative_href, is_endpoint=False):
    href_name = relative_href.strip("/")

    if len(href_name) < INDENT:
        href_name = href_name + (INDENT - len(href_name)) * " "
    return "{href_name} {current_path}{relative_href}{empty}".format(
        href_name=href_name,
        current_path=current_path,
        relative_href=relative_href,
        empty="?empty=True" if is_endpoint else ""
    )
