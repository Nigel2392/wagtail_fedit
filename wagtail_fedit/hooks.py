def prefix(name):
    return f"wagtail_fedit.{name}"


CONSTRUCT_BLOCK_TOOLBAR  = prefix("construct_block_toolbar")


CONSTRUCT_FIELD_TOOLBAR  = prefix("construct_field_toolbar")

"""
Register a custom renderer for a type.
"""
REGISTER_TYPE_RENDERER   = prefix("register_type_renderer")

"""
Register a custom renderer for a field.
This can be used to say; automatically render your RichText value. (wagtail_hooks/renderers.py)
"""
REGISTER_FIELD_RENDERER  = prefix("register_field_renderer")


EXCLUDE_FROM_RELATED_FORMS = prefix("exclude_related_forms")


"""
Decide if the action menu item should be shown for the given instance.
"""

ACTION_MENU_ITEM_IS_SHOWN = prefix("action_menu_item_is_shown")