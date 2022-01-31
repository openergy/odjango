# https://docs.djangoproject.com/en/2.0/ref/request-response/#django.http.HttpRequest.build_absolute_uri


def build_host_path(request):
    absolute_uri = request.build_absolute_uri()
    full_path = request.get_full_path()
    return absolute_uri[:-len(full_path)]


def build_base_path(request):
    host_path = build_host_path(request)
    server_path = request.path[:-len(request.path_info)]
    return host_path + server_path


def build_absolute_path(request):
    """
    absolute uri without query args
    """
    return build_host_path(request) + request.path
