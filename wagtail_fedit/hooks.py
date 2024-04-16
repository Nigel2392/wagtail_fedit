def prefix(name):
    """
        Default prefix for wagtail_fedit hooks.
    """
    return f"wagtail_fedit.{name}"



CONSTRUCT_ADAPTER_TOOLBAR = prefix("construct_adapter_toolbar")
"""
### wagtail_fedit.construct_adapter_toolbar
Construct the toolbar for the given adapter.
This is used to display the edit icon for the given adapter.
"""


REGISTER_TYPE_RENDERER   = prefix("register_type_renderer")
"""
### wagtail_fedit.register_type_renderer
Register a custom renderer for a type.

Example of how this type of renderer can be used:

```python
@hooks.register(REGISTER_TYPE_RENDERER)
def register_renderers(renderer_map):

    # This is a custom renderer for the Page model.
    # It will render the Page model as a simple h2 tag.
    renderer_map[Page] = lambda request, context, instance, value: format_html(
        '<h2>{0}</h2>',
        value.title
    )
```
"""

REGISTER_CSS = prefix("register_css")
"""
### wagtail_fedit.register_css
Register a custom CSS file to be included when the utils.FEDIT_PREVIEW_VAR is set to True.

Example of how this hook is used in wagtail_hooks.py:
    
    ```python
    @hooks.register(REGISTER_CSS)
    def register_css(request):
        return [
            format_html(
                '<link rel="stylesheet" href="{0}">',
                static('css/custom.css')
            ),
        ]
    ```
"""

REGISTER_JS = prefix("register_js")
"""
### wagtail_fedit.register_js
Register a custom JS file to be included when the utils.FEDIT_PREVIEW_VAR is set to True.
This can be used to register custom adapter JS.

Example of how this hook is used in wagtail_hooks.py:
    
    ```python
    @hooks.register(REGISTER_JS)
    def register_js(request):
        return [
            format_html(
                '<script src="{0}"></script>',
                static('js/custom.js')
            ),
        ]
    ```
"""


REGISTER_FIELD_RENDERER  = prefix("register_field_renderer")
"""
### wagtail_fedit.register_field_renderer
Register a custom renderer for a field.

Example of how this type of renderer is used in wagtail_hooks/renderers.py:

```python
@hooks.register(REGISTER_FIELD_RENDERER)
def register_renderers(renderer_map):

    # This is a custom renderer for RichText fields.
    # It will render the RichText field as a RichText block.
    renderer_map[RichTextField] =\
        lambda request, context, instance, value: richtext(value)
```
"""


FIELD_EDITOR_SIZE = prefix("field_editor_size")
"""
### wagtail_fedit.field_editor_size
Control the size of the editor for the given model-field type.

Example of how this hook is called:
    
    ```python
    for hook in hooks.get_hooks(FEDIT_FIELD_EDITOR_SIZE):
        size = hook(model_instance, model_field)
        if size:
            return size
    ```
"""


EXCLUDE_FROM_RELATED_FORMS = prefix("exclude_related_forms")
"""
### wagtail_fedit.exclude_related_forms
Exclude the given model type from the related forms.
This is used internally to exclude the Page, Image, and Document models from the related forms.
This way; the user will have the actual widget for the field instead of the related form.

Example of how this hook is called and how it is used internally:

```python
def use_related_form(field: models.Field) -> bool:
    for hook in hooks.get_hooks(EXCLUDE_FROM_RELATED_FORMS):
        if hook(field):
            return False
    return True

    
@hooks.register(EXCLUDE_FROM_RELATED_FORMS)
def exclude_related_forms(field):
    if field.related_model in [Page, Image, Document]:
        return True
    return False
```
"""


ACTION_MENU_ITEM_IS_SHOWN = prefix("action_menu_item_is_shown")
"""
### wagtail_fedit.action_menu_item_is_shown
Decide if the action menu item should be shown for the given instance.

Return None if you cannot decide, False if you want to hide the item, and True if you want to show the item.

Example of how this hook is called:

```python
for hook in hooks.get_hooks(ACTION_MENU_ITEM_IS_SHOWN):
    result = hook(context, instance)
    if result is not None:
        return result # <- bool
```
"""
