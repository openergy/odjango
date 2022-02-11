# Odjango rest framework package

## Documentation

### For developers of existing apps

* Don't hesitate to complete help_text fields of models and serializers : they will appear in documentation.
* To document a view: put a docstring (don't use ":" beause it is reserved for action description)
* To document an standard action: in view docstring, "{action_name}: description" (may expand on more than one line)
* To document a detail_route or list_route
    * put an action docstring
    * or in view docstring: "{action_name}: description" (will be overriden by docstring if any)
    * for inputs, use doc_detail_route and doc_list_route (odjango.rest_framework), and add doc=dict(serializer_class={SerializerClass}) in decorator kwargs
    
    
### For developers of new apps

**Add odjango's rest_framework app**

    "odjango.rest_framework_app",
    
*Must be declared before other rest_framework apps to override templates*

**Change renderer**

in "REST_FRAMEWORK" chapter:

    "DEFAULT_RENDERER_CLASSES": (
        'rest_framework.renderers.JSONRenderer',
        'odjango.rest_framework.BrowsableAPIRenderer'
        )

**Change schema class**

in "REST_FRAMEWORK" chapter:

    "DEFAULT_SCHEMA_CLASS": "odjango.rest_framework.OAutoSchema"

### For framework developers

**Browsable api renderer was subclassed**

See: renderers.BrowsableAPIRenderer

Uses: rest_framework_app static and template files
    
    declare odjango.rest_framework_app in django apps, BEFORE rest_framework (for template inheritance)
        
    "DEFAULT_RENDERER_CLASSES": (
        'rest_framework.renderers.JSONRenderer',
        'odjango.rest_framework.BrowsableAPIRenderer'
        )

#### Auto schema generator was subclassed

See inspectors.OAutoSchema

add "DEFAULT_SCHEMA_CLASS": "odjango.rest_framework.OAutoSchema" to REST_FRAMEWORK settings

#### Api main view modified

Makes a tree for root pages.
viewset.get_api_main_view

#### New detail_route and list_route coded

decorators.doc_detail_route
decorators.doc_list_route
 
 #### New odjango rest_framework app was created
 
 Purpose : store templates and static files
 