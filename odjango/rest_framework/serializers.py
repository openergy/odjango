from rest_framework import serializers
from odjango.django import NullableCharField as NullableCharModelField, NullableTextField as NullableTextModelField, \
    ScriptField as ScriptModelField


class NullableSerializerCharField(serializers.CharField):
    def __init__(self, **kwargs):
        if "allow_null" not in kwargs:
            kwargs["allow_null"] = True
        assert kwargs["allow_null"], "NullableChar field 'allow_null' can't be set to False"
        super().__init__(**kwargs)

    def to_representation(self, value):
        """
        Transform the *outgoing* native value into primitive data.

        value should not be empty string (if returned by nullable model field), but may not be the case if value has not
         saved in db yet.
        """
        value = super().to_representation(value)
        if value == "":
            return None
        return value

    def to_internal_value(self, data):
        if data == "None":
            return ""
        return data


class ScriptSerializerField(NullableSerializerCharField):
    def to_internal_value(self, data):
        return super().to_internal_value(data).replace("\t", "    ")


mapping = serializers.ModelSerializer.serializer_field_mapping.copy()
mapping.update({
        NullableCharModelField: NullableSerializerCharField,
        NullableTextModelField: NullableSerializerCharField,
        ScriptModelField: ScriptSerializerField
    })


class NullableModelSerializer(serializers.ModelSerializer):  # obsolete, use OutilModelSerializer
    serializer_field_mapping = mapping


class OutilModelSerializer(serializers.ModelSerializer):
    serializer_field_mapping = mapping
