import re
import types
import json
import logging

from django.db.models import fields as django_fields
from django.utils.encoding import smart_text

from rest_framework import fields as rest_framework_fields
from rest_framework import serializers
from rest_framework import exceptions
from rest_framework.schemas import AutoSchema
from rest_framework.schemas.coreapi import field_to_schema
from rest_framework.compat import coreapi, coreschema
from rest_framework.utils import formatting

header_regex = re.compile('^[a-zA-Z][0-9A-Za-z_]*:')

from odjango.rest_framework.viewset import STANDARD_ACTIONS


logger = logging.getLogger(__name__)


class OAutoSchema(AutoSchema):
    """
    add "DEFAULT_SCHEMA_CLASS": "odjango.rest_framework.OAutoSchema" to REST_FRAMEWORK settings

    doc_detail_route
    doc_list_route
        serializer_class

    help_text (models and serializers)

    to bypass Serializer auto discovery, create a get_flat_serializer_fields_documentation method on view, this
        method must return a DRF coreapi schema that will be used for documentation. When used, in order to have
        initial values in browsable api post/put/patch form, put a fake serializer in get_serializer_method (for
        example DRF serializers.Serializer, and attach a get_initial method that returns an ordered dict with initial
        values)


    """
    def get_description(self, path, method):
        """
        returns a json string with as key (all are optional):
            "": global description
            action_name: action description
            "filter_fields": filter fields list
        """
        view = self.view

        # prepare sections
        sections = {"": ""}

        # find action
        action_name = getattr(view, 'action', method.lower())

        # see if docstring
        # we use view.__class__ so detail or list routes don't clash with other names (for example action)
        action_docstring = getattr(view.__class__, action_name, None).__doc__
        if action_docstring is not None:
            sections[action_name] = formatting.dedent(smart_text(action_docstring))

        # get view description
        description = view.get_view_description()

        # parse
        lines = [line for line in description.splitlines()]
        current_section = ""

        for line in lines:
            if header_regex.match(line):
                current_section, sep, lead = line.partition(':')
                # check if not already filled by docstring
                if current_section in sections:
                    continue
                # fill
                sections[current_section] = lead.strip()
            else:
                sections[current_section] += '\n' + line

        # strip all
        for k in sections:
            sections[k] = sections[k].strip()

        # manage filter fields
        filter_fields = list(getattr(self.view, "filter_fields", []))
        if hasattr(self.view, "filter_class"):
            filter_fields += list(self.view.filter_class.Meta.fields)
        sections["filter_fields"] = filter_fields

        # dump in json and return
        return json.dumps(sections)

    def get_serializer_fields(self, path, method):
        """
        Return a list of `coreapi.Field` instances corresponding to any
        request body input, as determined by the serializer class.

        ADDED BY OPENERGY: if a view has A get_flat_serializer_fields_documentation method,
            we will give priority to this method
        """
        # find action
        view = self.view
        action_name = getattr(view, 'action', method.lower())

        # find serializer
        if action_name in STANDARD_ACTIONS:  # standard actions
            # check method
            if method not in ('PUT', 'PATCH', 'POST'):
                return []

            # check if Openergy's get_flat_serializer_fields_documentation exists, use if it does
            if hasattr(view, "get_flat_serializer_fields_documentation"):
                return view.get_flat_serializer_fields_documentation(method)

            if not hasattr(view, 'get_serializer'):
                return []

            try:
                serializer = view.get_serializer()
            except exceptions.APIException:
                serializer = None
                logger.warning(
                    "get_serializer() raised an exception during schema generations. "
                    "Serializer fields will not be generated.",
                    extra=dict(
                        view=view.__class__.__name__,
                        method=method,
                        path=str(path)
                    )
                )
        else:  # custom action
            # see if input_serializer_class was given
            action_method = getattr(view, action_name, None)
            doc_kwargs = getattr(action_method, "doc", {})
            serializer_class = doc_kwargs.get("serializer_class")

            # no doc serializer class
            if serializer_class is None:
                return []

            # get serializer (see rest_framework.generic.GenericApiView.get_serializer()
            kwargs = dict(context=view.get_serializer_context())
            serializer = serializer_class(**kwargs)

        # manage list serializer
        if isinstance(serializer, serializers.ListSerializer):
            return [
                coreapi.Field(
                    name='data',
                    location='body',
                    required=True,
                    schema=coreschema.Array()
                )
            ]

        # manage non-serializer serializers
        if not isinstance(serializer, serializers.Serializer):
            return []

        # store model fields if model serializer (to retrieve default value of fields)
        if isinstance(serializer, serializers.ModelSerializer):
            model_fields = dict([(f.name, f) for f in serializer.Meta.model._meta.concrete_fields])
        else:
            model_fields = None

        # prepare fields
        fields = []
        for field in serializer.fields.values():
            if field.read_only or isinstance(field, serializers.HiddenField):
                continue

            required = field.required and method != 'PATCH'

            # prepare schema
            schema = field_to_schema(field)

            # add default (not done by rest_framework...)
            if model_fields is not None:
                model_field = model_fields.get(field.field_name)
                default = getattr(model_field, "default", django_fields.NOT_PROVIDED)

                # manage functions
                if isinstance(default, types.FunctionType):
                    default = default.__name__

                # store
                schema.default = None if default == django_fields.NOT_PROVIDED else default
            else:
                default = getattr(field, "default", rest_framework_fields.empty)

                # store
                schema.default = None if default == rest_framework_fields.empty else default

            # make field
            field = coreapi.Field(
                name=field.field_name,
                location='form',
                required=required,
                schema=schema,
                description=field.help_text  # help text was added
            )
            fields.append(field)

        return fields

    def get_filter_fields(self, path, method):
        """
        see super().get_filter_fields
        """
        return []
