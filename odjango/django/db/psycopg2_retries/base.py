from django.db.backends.postgresql.base import psycopg2_version, PSYCOPG2_VERSION, INETARRAY_OID, INETARRAY,\
    DatabaseWrapper as BaseDatabaseWrapper

from django.db.utils import InterfaceError
from psycopg2 import InterfaceError as InterfaceErrorPsycopg2, OperationalError as OperationalErrorPsycopg,\
    DatabaseError as DatabaseErrorPsycopg, IntegrityError as IntegrityErrorPsycopg
from django import db
import logging
import time

logger = logging.getLogger(__name__)


class CursorWithRetries:
    def __init__(self, cursor, database, name):
        self.cursor = cursor
        self.db = database
        self.name = name

    def __getattr__(self, item):
        return getattr(self.cursor, item)
        
    def execute(self, sql, params=None):
        for i in range(10):
            try:
                if params is None:
                    return self.cursor.execute(sql)
                else:
                    return self.cursor.execute(sql, params)
            except (db.utils.IntegrityError, IntegrityErrorPsycopg):
                raise
            except (db.utils.OperationalError, OperationalErrorPsycopg, InterfaceError, InterfaceErrorPsycopg2,
                    db.utils.DatabaseError, DatabaseErrorPsycopg):
                from django.core.exceptions import ObjectDoesNotExist
                if i == 9:
                    raise
                logger.warning("Connection to the db lost, reconnecting and retrying", exc_info=True)
                # exponential backoff
                if i != 0:
                    time.sleep(0.5*(2**i))
                self.db.close()
                self.db.connect()
                self.cursor = self.db.dev_create_cursor(name=self.name, with_wrapper=False)


class DatabaseWrapper(BaseDatabaseWrapper):
    def create_cursor(self, name=None):
        return self.dev_create_cursor(name=name, with_wrapper=True)

    # same function, but return a normal cursor
    def dev_create_cursor(self, name=None, with_wrapper=True):
        for i in range(10):
            try:
                if with_wrapper:
                    return CursorWithRetries(super().create_cursor(name=name), self, name)
                else:
                    return super().create_cursor(name=name)
            except (InterfaceError, InterfaceErrorPsycopg2, OperationalErrorPsycopg, db.utils.OperationalError,
                    db.utils.DatabaseError, DatabaseErrorPsycopg):
                if i == 9:
                    raise
                logger.warning("Connection to the db lost, reconnecting and retrying", exc_info=True)
                # exponential backoff
                if i != 0:
                    time.sleep(0.5*(2**i))
                self.close()
                self.connect()

    def connect(self):
        for i in range(10):
            try:
                return super().connect()
            except (InterfaceError, InterfaceErrorPsycopg2, OperationalErrorPsycopg, db.utils.OperationalError,
                    db.utils.DatabaseError, DatabaseErrorPsycopg):
                if i == 9:
                    raise
                logger.warning("Connection to the db lost, reconnecting and retrying", exc_info=True)
                # exponential backoff
                if i != 0:
                    time.sleep(0.5*(2**i))
                self.close()
