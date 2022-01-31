from rest_framework.generics import get_object_or_404

from .filter import DatatablesFilterBackend
from .pagination import OPagination


def get_object_bypass_filters(view, bypass_all=False):
    """
    Parameters
    ----------
    view: given view
    bypass_all: boolean, default False
        if False, will only bypass user filters, and will check object permission
        if True, will also bypass dev filters ("queryset" variable will directly be used, without applying django
        workflow queryset.get()) and won't check object permission

    Returns
    -------

    """
    # Perform the lookup filtering.
    lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field

    assert lookup_url_kwarg in view.kwargs, (
        'Expected view %s to be called with a URL keyword argument '
        'named "%s". Fix your URL conf, or set the `.lookup_field` '
        'attribute on the view correctly.' %
        (view.__class__.__name__, lookup_url_kwarg)
    )

    filter_kwargs = {view.lookup_field: view.kwargs[lookup_url_kwarg]}

    # get queryset
    if bypass_all:  # no filters
        queryset = view.queryset
    else:  # dev filters
        queryset = view.get_queryset()

    # find instance
    instance = get_object_or_404(queryset, **filter_kwargs)

    # may raise a permission denied
    if not bypass_all:
        view.check_object_permissions(view.request, instance)

    return instance


def filter_paginate_respond_from_queryset(view, queryset, serializer_cls, filtering_view_cls=None):
    # filter if filtering_view_cls is given
    if filtering_view_cls is not None:
        for backend in list(filtering_view_cls.filter_backends):
            queryset = backend().filter_queryset(view.request, queryset, filtering_view_cls)

    # paginate (see mixins.ListViewSet)
    page = view.paginate_queryset(queryset)
    serializer = serializer_cls(page, many=True)
    return view.get_paginated_response(serializer.data)


def datatables_filter_paginate_respond_from_iterable(elements, view, serializer_cls=None):
    """
    Parameters
    ----------
    elements: list or iterator (objects if serializer_cls else serialized dictionaries)

    filter is only performed by DatatablesFilterBackend (iterable filter not available in standard filter backends)
    """
    # serialize
    if serializer_cls is not None:
        serialized = serializer_cls(instance=elements, many=True).data
    else:
        serialized = elements
        
    # filter
    filtered = DatatablesFilterBackend.filter_list(view.request, serialized, view=view)

    # paginate
    paginator = OPagination()
    paginated = paginator.paginate_list(filtered, view.request, view=view)

    # respond
    return paginator.get_paginated_response(paginated)
