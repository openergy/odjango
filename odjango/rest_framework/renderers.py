import json
from collections import OrderedDict
import textwrap
from django import forms
from django.core.paginator import Page
from rest_framework import serializers
from rest_framework.request import override_method

from rest_framework.renderers import BrowsableAPIRenderer as RFBrowsableAPIRenderer
from rest_framework.schemas.coreapi import SchemaGenerator

from odjango.django import build_base_path


class BrowsableAPIRenderer(RFBrowsableAPIRenderer):
    """
    declare odjango.rest_framework_app in django apps, BEFORE rest_framework (for template inheritance)

    "DEFAULT_RENDERER_CLASSES": (
        'rest_framework.renderers.JSONRenderer',
        'odjango.rest_framework.BrowsableAPIRenderer'
        ),
    """
    describe_update = True  # will display partial updates and updates

    def show_form_for_method(self, view, method, request, obj):
        """
        We describe all allowed_methods, instead of filtering by permission.
        """
        return method in view.allowed_methods

    def get_rendered_html_form(self, data, view, method, request):
        # We neutralized this function so that it does not get called when calling super().get_context(..)
        # which caused bugs with marshmallow
        if method.lower() in ("put", "post", "patch"):
            return

        # fallback to default rest framework method
        return super().get_rendered_html_form(data, view, method, request)

    def get_raw_data_form(self, data, view, method, request):
        """
        Returns a form that allows for arbitrary content types to be tunneled
        via standard HTML forms.
        (Which are typically application/x-www-form-urlencoded)
        """
        if method == "PUT":
            return
        # See issue #2089 for refactoring this.
        serializer = getattr(data, 'serializer', None)
        if serializer and not getattr(serializer, 'many', False):
            instance = getattr(serializer, 'instance', None)
            if isinstance(instance, Page):
                instance = None
        else:
            instance = None

        with override_method(view, request, method) as request:
            # Check permissions
            if not self.show_form_for_method(view, method, request, instance):
                return

            # If possible, serialize the initial content for the generic form
            default_parser = view.parser_classes[0]
            renderer_class = getattr(default_parser, 'renderer_class', None)
            doc = False
            if hasattr(view, 'action') and \
                    isinstance(view.action, str) and \
                    'serializer_class' in getattr(getattr(view, view.action, None), 'doc', {}):
                serializer = getattr(view, view.action).doc["serializer_class"]()
                doc = True
            elif hasattr(view, 'get_serializer') and renderer_class:
                # View has a serializer defined and parser class has a
                # corresponding renderer that can be used to render the data.

                if method in ('PUT', 'PATCH'):
                    serializer = view.get_serializer(instance=instance)
                else:
                    serializer = view.get_serializer()

            if serializer is not None:
                # Render the raw data content
                renderer = renderer_class()
                accepted = self.accepted_media_type
                context = self.renderer_context.copy()
                context['indent'] = 4

                # strip HiddenField from output
                data = serializer.data.copy()
                if not doc:
                    for name, field in serializer.fields.items():
                        if isinstance(field, serializers.HiddenField) or (
                            method in ('PUT', 'PATCH', 'POST') and field.read_only
                        ) or (
                            method in ('PUT', 'PATCH') and getattr(view, "update_can_write_fields", None)
                            and name not in view.update_can_write_fields and (
                                    view.update_can_admin_fields is None or name not in view.update_can_admin_fields
                            )
                        ) or (
                            method == 'POST' and hasattr(view, "create_fields") and name not in view.create_fields
                        ):
                            data.pop(name, None)
                content = renderer.render(data, accepted, context)
                # Renders returns bytes, but CharField expects a str.
                content = content.decode()
            else:
                content = None

            # Generate a generic form that includes a content type field,
            # and a content field.
            media_types = [parser.media_type for parser in view.parser_classes]
            choices = [(media_type, media_type) for media_type in media_types]
            initial = media_types[0]

            class GenericContentForm(forms.Form):
                _content_type = forms.ChoiceField(
                    label='Media type',
                    choices=choices,
                    initial=initial,
                    widget=forms.Select(attrs={'data-override': 'content-type'})
                )
                _content = forms.CharField(
                    label='Content',
                    widget=forms.Textarea(attrs={'data-override': 'content'}),
                    initial=content,
                    required=False
                )

            return GenericContentForm()

    def get_context(self, data, accepted_media_type, renderer_context):
        # call parent
        context = super().get_context(data, accepted_media_type, renderer_context)

        # store request
        request = context["request"]

        # calculate paths
        base_path = build_base_path(request)

        # find schema data for given request
        schema_object = extract_schema_object(request)

        # iter links
        documentation = OrderedDict(
            description=None,  # will be filled later
            paths=OrderedDict()
        )
        for action_name, action_info in schema_object.links.items():
            # register action
            _register_action(
                documentation,
                action_name,
                action_info,
                base_path,
                self.describe_update
            )

            # store global description (we do it only for list actions - but could be done with another)
            if action_name == "list":
                documentation["description"] = get_global_description(action_info)

        # we now manage detail or list routes with more than one method (this creates a new link)
        for action_name, action_data_info in schema_object.data.items():
            items_nb = len(action_data_info.links)
            methods = []
            for i, (_, action_info) in enumerate(action_data_info.links.items()):
                methods.append(action_info.action)
                if (i+1) == items_nb:  # we only use info of last item (to prevent redundancy)
                    _register_action(
                        documentation,
                        action_name,
                        action_info,
                        base_path,
                        self.describe_update,
                        methods=methods
                    )

        # store in context
        context["documentation"] = documentation

        return context


def _register_action(
        documentation,
        action_name,
        action_info,
        base_path,
        describe_update,
        methods=None
):
    # continue if update shouldn't be described
    if not describe_update and action_name == "update":
        return

    # find url
    path = action_info.url
    url = base_path + path

    # see if already
    if path not in documentation["paths"]:
        documentation["paths"][path] = OrderedDict(
            url=url,
            actions=OrderedDict()  # name, description
        )

    # store action description
    documentation["paths"][path]["actions"][action_name] = get_action_description(
        action_name,
        action_info,
        methods=methods
    )


def extract_schema_object(request):
    # generate schema
    schema = SchemaGenerator().get_schema()

    # path_info: https://docs.djangoproject.com/en/2.0/ref/request-response/#django.http.HttpRequest.path_info
    path_info = request.path_info

    # iter path and return last node
    current_node = schema
    for i, element in enumerate(path_info.strip("/").split("/")):
        # todo: check that we can't fin an element too early (maybe check for i value - must be == to len(elements) ?
        if element not in current_node.data:
            continue

        current_node = current_node.data[element]

    return current_node


def get_action_description(action_name, action_info, methods=None):
    """
    if methods is given, will bypass action_info method (used if two actions with same method - for some detail or list
    routes)
    """
    # load
    try:
        description_d = json.loads(action_info.description)
    except json.decoder.JSONDecodeError:
        description_d = {}

    # method
    methods = [action_info.action.upper()] if methods is None else [m.upper() for m in methods]
    description = "%s\n\n" % ", ".join(methods)

    # description
    if len(description_d.get(action_name, "")) > 0:
        description += "description\n%s\n\n" % textwrap.indent(description_d[action_name], "  ")

    # parse fields, separating required and optional
    required, optional = [], []
    for field_info in action_info.fields:
        field_description = get_field_description(field_info)

        # store in appropriate list
        required.append(field_description) if field_info.required else optional.append(field_description)

    # complete description
    for (name, descriptions_l) in (
            ("required", required),
            ("optional", optional)
    ):
        if len(descriptions_l) > 0:
            description += "%s fields\n" % name
            for field_str in descriptions_l:
                description += "  %s\n" % field_str
            description += "\n"

    return description


def get_field_description(field_info):
    # name
    field_description = "%s:" % field_info.name

    # type
    field_type = field_info.schema.__class__.__name__.lower()
    if field_type == "enum":
        field_description += " enum(%s)" % ", ".join(
            [(str(f) if not isinstance(f, str) else "'%s'" % f) for f in field_info.schema.enum])
    else:
        field_description += " %s" % field_type

    # default
    default = field_info.schema.default
    if default is not None:
        field_description += ", default " + (("'%s'" % default) if isinstance(default, str) else str(default))

    # description
    if field_info.description is not None:
        field_description += ", %s" % field_info.description.strip()

    return field_description


def get_global_description(action_info):
    description = ""
    description_d = json.loads(action_info.description)

    if len(description_d[""]) > 0:
        description += "description\n%s\n" % textwrap.indent(description_d[""], "  ")

    # filter_fields
    if len(description_d["filter_fields"]) > 0:
        if len(description) > 0:
            description += "\n"
        description += "filter fields\n  %s" % "\n  ".join(description_d["filter_fields"])

    return None if len(description) == 0 else description
