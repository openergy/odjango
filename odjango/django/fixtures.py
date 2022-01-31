from functools import wraps


def disable_for_loaddata(signal_handler):
    """
    Decorator that turns off signal handlers when loading fixture data.
    No need to decorate other signals than post_save (pre_save is not called during fixtures - and nothing is deleted).
    http://stackoverflow.com/questions/15624817/have-loaddata-ignore-or-disable-post-save-signals

    """

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if ("raw" not in kwargs) or kwargs["raw"]:  # signal is not concerned or fixture
            return
        signal_handler(*args, **kwargs)
    return wrapper
