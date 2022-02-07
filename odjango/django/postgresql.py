import logging

from django.db.utils import InterfaceError, OperationalError, InternalError
from django import db
from psycopg2 import OperationalError as OperationalErrorPsycopg

logger = logging.getLogger(__name__)


class PostgresqlDatabaseRetry:
    def __init__(self, retries_nb):
        self.retries_nb = retries_nb

    def __call__(self, f):
        def wrapped_function(*args, **kwargs):
            for i in range(self.retries_nb):
                try:
                    return f(*args, **kwargs)
                except InterfaceError:
                    logger.warning("Connection to the db lost, reconnection and retrying", exc_info=True)
                    db.connection.close()
                except (OperationalError, OperationalErrorPsycopg, InternalError):
                    logger.warning("Database error, closing connection and retrying", exc_info=True)
                    db.connection.close()

            return f(*args, **kwargs)

        return wrapped_function
