import logging
import io
import sys
import traceback

_logger = logging.getLogger(__name__)


def apply_migrations(no_input=False):
    from django.core.management import execute_from_command_line
    execute_from_command_line(["", "migrate"] + (["--noinput"] if no_input else []))


def collect_static():
    from django.core.management import execute_from_command_line
    execute_from_command_line(["", "collectstatic", "--noinput"])


def initialize_django_files(migrations=True, static=True):
    """
    only for sqlite config
    """
    # redirect stdout to logger
    with io.StringIO() as fo, io.StringIO() as fe:
        stdout, stderr = sys.stdout, sys.stderr
        # redirect
        sys.stdout = fo
        sys.stderr = fe
        try:
            # migrations
            if migrations:
                print("Applying migrations.")
                apply_migrations(no_input=True)
                print("Migrations have been applied.\n")

            # collect static
            if static:
                print("Collecting static.")
                collect_static()
                print("Static files have been collected.\n")

        except:
            # sys.exit(1) may be called, which fails silently.... We therefore hack to re-raise
            raise Exception(traceback.format_exc()) from None

        finally:
            # log
            msg = fo.getvalue()
            if len(msg) > 0:
                _logger.info(msg)
            msg = fe.getvalue()
            if len(msg) > 0:
                _logger.error(msg)

            # restore standard outputs
            sys.stdout, sys.stderr = stdout, stderr
