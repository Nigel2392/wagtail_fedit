from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.action_menu import ActionMenuItem as PageActionMenuItem
from wagtail.snippets.action_menu import ActionMenuItem as SnippetActionMenuItem
from wagtail.models import PreviewableMixin
from wagtail import hooks

from ..hooks import (
    ACTION_MENU_ITEM_IS_SHOWN,
)

class WagtailFEditActionMenuItemMixin:
    name = 'action-frontend-edit'
    label = _('Frontend Edit')
    icon_name = "desktop"

    def is_shown(self, context):
        instance = context.get("instance", context.get("page", None))
        if instance is None:
            return False

        for hook in hooks.get_hooks(ACTION_MENU_ITEM_IS_SHOWN):
            result = hook(context, instance)
            if result is not None:
                return result

        return context["view"] == "edit"\
            and not context.get("locked_for_user") and (
                isinstance(instance, PreviewableMixin)
        )
    
    def get_url(self, context):
        instance = context.get("instance", context["page"])
        return reverse(
            "wagtail_fedit:editable",
            args=[instance.pk, instance._meta.app_label, instance._meta.model_name]
        )

class WagtailFEditPageActionMenuItem(WagtailFEditActionMenuItemMixin, PageActionMenuItem):
    pass

class WagtailFEditSnippetActionMenuItem(WagtailFEditActionMenuItemMixin, SnippetActionMenuItem):
    pass
   

@hooks.register('register_page_action_menu_item')
def register_wagtail_fedit_menu_item():
    return WagtailFEditPageActionMenuItem(order=1)
 
@hooks.register('register_snippet_action_menu_item')
def register_wagtail_fedit_snippet_menu_item(model_class = None):
    return WagtailFEditSnippetActionMenuItem(order=1)
