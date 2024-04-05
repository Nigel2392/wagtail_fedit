from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.templatetags.static import static
from wagtail.admin.userbar import (
    BaseItem,
    AddPageItem,
    ExplorePageItem,
    EditPageItem,
)
from wagtail import hooks
from ..toolbar import (
    FeditToolbarComponent,
)
from ..utils import (
    is_draft_capable,
    FeditPermissionCheck,
    access_userbar_model,
    FEDIT_PREVIEW_VAR,
    user_can_publish,
    user_can_unpublish,
    user_can_submit_for_moderation,
)

class FeditableModelComponent(FeditToolbarComponent):
    def __init__(self, instance):
        self.instance = instance

    def get_context_data(self, request):
        return super().get_context_data(request) | {
            "hidden": not self.instance.has_unpublished_changes,
            "action_url": reverse(
                self.action_url,
                args=[self.instance.pk, self.instance._meta.app_label, self.instance._meta.model_name],
            ),
        }

class UserBarActionPublishComponent(FeditableModelComponent):
    template_name = "wagtail_fedit/userbar/publish/buttons/publish.html"
    action_url = "wagtail_fedit:publish"
    check_for_changes = False
    
    def is_shown(self, request):
        if not super().is_shown(request):
            return False
        
        return user_can_publish(self.instance, request.user, check_for_changes=self.check_for_changes)

class UserBarActionUnpublishComponent(FeditableModelComponent):
    template_name = "wagtail_fedit/userbar/publish/buttons/unpublish.html"
    action_url = "wagtail_fedit:unpublish"
        
    def is_shown(self, request):
        if not super().is_shown(request):
            return False
        
        return user_can_unpublish(self.instance, request.user)

class UserBarActionSubmitComponent(FeditableModelComponent):
    template_name = "wagtail_fedit/userbar/publish/buttons/submit.html"
    action_url = "wagtail_fedit:submit"
    check_for_changes = False

    def is_shown(self, request):
        if not super().is_shown(request):
            return False
        
        return user_can_submit_for_moderation(self.instance, request.user, check_for_changes=self.check_for_changes)


class BaseWagtailFeditItem(BaseItem, FeditPermissionCheck):
    def __init__(self, model):
        self.model = model

    def get_context_data(self, request):
        context = super().get_context_data(request)
        context["model"] = self.model
        context["edit_url"] = reverse(
            "wagtail_fedit:editable",
            args=[
                self.model.pk,
                self.model._meta.app_label,
                self.model._meta.model_name,
            ],
        )
        return context

    def render(self, request):
        if not self.has_perms(request, self.model):
            return ""

        return super().render(request)


class WagtailFeditItem(BaseWagtailFeditItem):
    template = "wagtail_fedit/userbar/item_fedit.html"

class WagtailFeditViewLiveItem(BaseWagtailFeditItem):
    template = "wagtail_fedit/userbar/item_fedit_view_live.html"

    def get_context_data(self, request):
        context = super().get_context_data(request)
        
        if hasattr(self.model, "get_url"):
            context["live_url"] = self.model.get_url(request)
        elif hasattr(self.model, "get_absolute_url"):
            context["live_url"] = self.model.get_absolute_url()

        return context
    
class WagtailFeditPublishItem(BaseWagtailFeditItem):
    template = "wagtail_fedit/userbar/publish/item_fedit_publishing.html"

    def render(self, request):

        self.can_publish = user_can_publish(self.model, request.user, check_for_changes=False)
        self.can_unpublish = user_can_unpublish(self.model, request.user)
        self.can_submit_for_moderation = user_can_submit_for_moderation(
            self.model, request.user, check_for_changes=False,
        )

        if not self.can_publish\
                and not self.can_unpublish\
                and not self.can_submit_for_moderation:
            return ""

        return super().render(request)

    def get_context_data(self, request):

        buttons = [
            UserBarActionPublishComponent(self.model),
            UserBarActionSubmitComponent(self.model),
            UserBarActionUnpublishComponent(self.model),
        ]

        for i, button in enumerate(buttons):
            buttons[i] = button.render(request)

        buttons = list(filter(None, buttons))

        return super().get_context_data(request) | {
            "buttons": buttons,
            "can_publish": self.can_publish,
            "can_unpublish": self.can_unpublish,
            "hidden": self.can_publish or self.can_submit_for_moderation\
                and self.model.has_unpublished_changes,
            "publish_url": reverse(
                "wagtail_fedit:publish",
                args=[self.model.pk, self.model._meta.app_label, self.model._meta.model_name],
            ),
        }

def retrieve_page_model(items):
    # Retrieve page from other items...
    # sad we are not just provided with the context or page too.
    for item in items:
        if isinstance(item, (AddPageItem, ExplorePageItem, EditPageItem))\
                or hasattr(item, "page"):
            
            return item.page
    return None

@hooks.register("insert_global_admin_css")
def fedit_admin_js():
    return mark_safe(format_html(
        '<link rel="stylesheet" href="{}">',
        static("wagtail_fedit/css/userbar-menu.css"),
    ))

@hooks.register("construct_wagtail_userbar")
def add_fedit_userbar_item(request, items):
    model = (
        access_userbar_model(request) or\
        retrieve_page_model(items)
    )

    local_items = []
    
    if getattr(request, FEDIT_PREVIEW_VAR, False):
        if is_draft_capable(model):
            local_items.append(
                WagtailFeditPublishItem(model),
            )

        if hasattr(model, "get_absolute_url") or hasattr(model, "get_url"):
            local_items.append(
                WagtailFeditViewLiveItem(model),
            )

    if model and not getattr(request, FEDIT_PREVIEW_VAR, False):
        local_items.append(
            WagtailFeditItem(model),
        )

    items[:] = local_items + items



