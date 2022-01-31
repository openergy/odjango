import uuid
import mimetypes
import os

from django.db import models
from django.http import HttpResponse
from django.contrib.contenttypes.models import ContentType


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    @classmethod
    def ct(cls):
        return ContentType.objects.get_for_model(cls)

    class Meta:
        abstract = True


def reset_db(apps=None, exclude=("authtoken", "corsheaders", "contenttypes")):
    """
    Parameters
    ----------
    apps : list of apps names to reset (except excluded). If None, will reset all apps except excluded.
    exclude : list of apps not to reset
    """
    # prepare arguments
    if apps is None:
        apps = set(ct.app_label for ct in ContentType.objects.all())
    else:
        apps = set(apps)
    exclude = set(exclude)

    # remove apps
    # sorted: to be deterministic
    for app_label in sorted(apps.difference(exclude)):
        for ct in ContentType.objects.filter(app_label=app_label).order_by("model"):
            for obj in ct.model_class().objects.order_by("pk"):
                obj.delete()


def respond_file_from_local_file(file_path):
    """https://djangosnippets.org/snippets/1710/"""
    with open(file_path, "rb") as f:
        bts = f.read()
    file_name = os.path.basename(file_path)
    content_length = os.path.getsize(file_path)
    return respond_file_from_bytes(bts, file_name, content_length=content_length)


def respond_file_from_bytes(bts, file_name, content_length=None):
    # make response
    response = HttpResponse(bts)

    # choose file_type
    file_type, file_encoding = mimetypes.guess_type(file_name)
    if file_type is None:
        file_type = "application/octet-stream"

    response["Content-Type"] = file_type
    if content_length is not None:
        response["Content-Length"] = str(content_length)
    if file_encoding is not None:
        response["Content-Encoding"] = file_encoding
    response["Content-Disposition"] = "attachment; filename=%s" % file_name

    return response

