from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapters import BaseAdapter

class FeditToolbarComponent:
    template_name = None
    permissions: list[str] = []

    def __init__(self, request):
        self.request = request

    def get_context_data(self):
        return {
            "self": self,
            "request": self.request,
        }
    
    def is_shown(self):
        if not all([self.request, self.request.user.is_authenticated]):
            return False
        
        if not self.permissions:
            return True
        
        return self.request.user.has_perms(self.permissions)
    
    def render(self):
        if not self.is_shown():
            return ""

        return mark_safe(render_to_string(
            self.template_name,
            self.get_context_data(),
        ))


class FeditAdapterComponent(FeditToolbarComponent):
    def __init__(self, request, adapter: "BaseAdapter"):
        super().__init__(request)
        self.adapter = adapter

class FeditAdapterEditButton(FeditAdapterComponent):
    """
        Required button class for the edit modal to function.
        This button is handled by the script in `wagtail_fedit/js/frontend.js`
    """
    template_name = "wagtail_fedit/content/buttons/edit_adapter.html"
    permissions = [
        "wagtailadmin.access_admin",
    ]

class FeditAdapterAdminLinkButton(FeditAdapterComponent):
    """
        Required button class for the edit modal to function.
        This button is handled by the script in `wagtail_fedit/js/frontend.js`
    """
    template_name = "wagtail_fedit/content/buttons/admin_link.html"
    permissions = [
        "wagtailadmin.access_admin",
    ]

    def get_context_data(self):
        return super().get_context_data() | {
            "admin_url": self.adapter.get_admin_url(),
        }
