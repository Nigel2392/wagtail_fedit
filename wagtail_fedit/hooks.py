def prefix(name):
    """
        Default prefix for wagtail_fedit hooks.
    """
    return f"wagtail_fedit.{name}"


"""
### wagtail_fedit.construct_block_toolbar
Construct the toolbar for the given block.
This is used to display the edit icon in the block.

How it is called:

```python
for hook in hooks.get_hooks(CONSTRUCT_BLOCK_TOOLBAR):
    hook(request=request, items=items, model=model, block_id=block_id, field_name=field_name)
```
"""
CONSTRUCT_BLOCK_TOOLBAR  = prefix("construct_block_toolbar")


"""
### wagtail_fedit.construct_field_toolbar
Construct the toolbar for the given field.
This is used to display the edit icon in the field.

How it is called:

```python
for hook in hooks.get_hooks(CONSTRUCT_FIELD_TOOLBAR):
    hook(request=request, items=items, model=model, field_name=field_name)
```
"""
CONSTRUCT_FIELD_TOOLBAR  = prefix("construct_field_toolbar")


"""
### wagtail_fedit.register_type_renderer
Register a custom renderer for a type.

Example of how this type of renderer can be used:

```python
@hooks.register(REGISTER_TYPE_RENDERER)
def register_renderers(renderer_map):

    # This is a custom renderer for the Page model.
    # It will render the Page model as a simple h2 tag.
    renderer_map[Page] = lambda request, context, instance: format_html(
        '<h2>{0}</h2>',
        instance.title
    )
```
"""
REGISTER_TYPE_RENDERER   = prefix("register_type_renderer")


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
REGISTER_FIELD_RENDERER  = prefix("register_field_renderer")


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
EXCLUDE_FROM_RELATED_FORMS = prefix("exclude_related_forms")


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
ACTION_MENU_ITEM_IS_SHOWN = prefix("action_menu_item_is_shown")