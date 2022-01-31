from django.db import models


class FieldsError(Exception):
    pass


def _nullable_to_python(value):
    if value == "":
        return None
    return value


def _nullable_to_db(value):
    if value is None:
        return ""
    return value


class NullableCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        null = kwargs.get("null", False)
        if null:
            raise FieldsError("Can't set null of a text or char field to True.")

        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection, context=None):  # context: compat with old rest_framework
        """
        https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.Field.from_db_value
        """
        return _nullable_to_python(value)

    def to_python(self, value):
        """
        https://docs.djangoproject.com/en/1.8/howto/custom-model-fields/#converting-values-to-python-objects
        (not very clear but works...)
        """
        return _nullable_to_python(value)

    def get_prep_value(self, value):
        """
        https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.Field.get_prep_value
        """
        value = super().get_prep_value(value)
        return _nullable_to_db(value)


class NullableTextField(models.TextField):
    def __init__(self, *args, **kwargs):
        null = kwargs.get("null", False)
        if null:
            raise FieldsError("Can't set null of a text or char field to True.")
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection, context=None):  # context: compat with old rest_framework
        """
        https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.Field.from_db_value
        https://docs.djangoproject.com/en/1.8/howto/custom-model-fields/#converting-values-to-python-objects
        """
        return _nullable_to_python(value)

    def to_python(self, value):
        """
        https://docs.djangoproject.com/en/1.8/howto/custom-model-fields/#converting-values-to-python-objects
        (not very clear but works...)
        """
        return _nullable_to_python(value)

    def get_prep_value(self, value):
        """
        https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.Field.get_prep_value
        https://docs.djangoproject.com/en/1.8/howto/custom-model-fields/#converting-values-to-python-objects
        """
        value = super().get_prep_value(value)
        return _nullable_to_db(value)


class ScriptField(NullableTextField):
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return value.replace("\t", "    ")
