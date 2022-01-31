import warnings

from rest_framework.decorators import action


def doc_detail_route(methods=None, **kwargs):
    def decorator(func):
        # if (methods is None) or (len(methods) != 1):
        #     warnings.warn("one and only one method must be declared on a detail route for proper documentation "
        #                   "(got %s for '%s' function)" % (str(methods), func.__name__))
        doc = kwargs.pop("doc", {})
        func.doc = doc
        return action(methods=methods, detail=True, **kwargs)(func)
    return decorator


def doc_list_route(methods=None, **kwargs):
    def decorator(func):
        # if (methods is None) or (len(methods) != 1):
        #     warnings.warn("one and only one method must be declared on a list route for proper documentation "
        #                   "(got %s for '%s' function)" % (str(methods), func.__name__))
        doc = kwargs.pop("doc", {})
        func.doc = doc
        return action(methods=methods, detail=False, **kwargs)(func)
    return decorator
