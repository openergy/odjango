from contextlib import contextmanager

from oclients import ClientResponseError
from rest_framework.exceptions import APIException


@contextmanager
def propagate_client_errors():
    try:
        yield
    except ClientResponseError as e:
        class CustomError(APIException):
            status_code = e.code
        raise CustomError(detail=e.message)
