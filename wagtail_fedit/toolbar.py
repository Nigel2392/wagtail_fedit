from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

class FeditToolbarComponent:
    template_name = None
    permissions: list[str] = []

    def __init__(self):
        pass

    def get_context_data(self, request):
        return {
            "self": self,
            "request": request,
        }
    
    def is_shown(self, request):
        if not all([request, request.user.is_authenticated]):
            return False
        
        if not self.permissions:
            return True
        
        return request.user.has_perms(self.permissions)
    
    def render(self, request):
        if not self.is_shown(request):
            return ""

        return mark_safe(render_to_string(
            self.template_name,
            self.get_context_data(request),
        ))


class FeditBlockEditButton(FeditToolbarComponent):
    """
        Required button class for the edit modal to function.
        This button is handled by the script in `wagtail_fedit/js/frontend.js`
    """
    template_name = "wagtail_fedit/content/buttons/edit_block.html"
    permissions = [
        "wagtailadmin.access_admin",
    ]


class FeditFieldEditButton(FeditToolbarComponent):
    """
        Required button class for the edit modal to function.
        This button is handled by the script in `wagtail_fedit/js/frontend.js`
    """
    template_name = "wagtail_fedit/content/buttons/edit_field.html"
    permissions = [
        "wagtailadmin.access_admin",
    ]
