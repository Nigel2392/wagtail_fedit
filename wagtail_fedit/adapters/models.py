from django.utils.translation import gettext_lazy as _
from django.http import HttpRequest

from wagtail.models import Page
from wagtail.admin.panels import (
    page_utils,
    model_utils,
    TabbedInterface,
)

from .base import (
    VARIABLES,
    BlockFieldReplacementAdapter,
    AdapterError,
)
from ..utils import (
    get_model_string,
)


class ModelAdapter(BlockFieldReplacementAdapter):
    """
    An adapter for editing any model.
    This will render the model and replace it on the frontend
    on successful form submission.
    """
    template_name = "wagtail_fedit/editor/adapter_edit_handler.html"
    identifier = "model"
    field_required = False
    usage_description = _("This adapter is used for directly editing a model instance.")

    def __init__(self, object, field_name: str, request: HttpRequest, **kwargs):
        super().__init__(object, field_name, request, **kwargs)
        if isinstance(self.object, Page):
            self.edit_handler = page_utils._get_page_edit_handler(self.object.__class__)
        else:
            self.edit_handler = model_utils.get_edit_handler(self.object.__class__)

    def get_form_attrs(self) -> dict:
        attrs = super().get_form_attrs()
        if isinstance(self.edit_handler, TabbedInterface):
            attrs[VARIABLES.FORM_SIZE_VAR] = "full"
        elif len(self.edit_handler.children) > 4:
            attrs[VARIABLES.FORM_SIZE_VAR] = "large"
        return attrs
        
    def get_header_title(self):
        instance_string = get_model_string(self.object)
        return _("Edit model %(instance_string)s") % {
            "instance_string": instance_string,
        }
    
    def get_help_text(self):
        return None
          
    def get_element_id(self) -> str:
        m = self.model
        return f"model-{m._meta.app_label}-{m._meta.model_name}-{self.object.pk}"
    
    def get_form_context(self, **kwargs):
        context = super().get_form_context(**kwargs)
        bound_panel = self.edit_handler.get_bound_panel(
            instance=self.object, request=self.request, form=kwargs["form"],
        )
        context["edit_handler"] = bound_panel
        return context

    @property
    def form_class(self):
        return self.edit_handler.get_form_class()

    def get_form(self):
        if self.request.method == "POST":
            form = self.form_class(self.request.POST, for_user=self.request.user, instance=self.object)
        else:
            form = self.form_class(for_user=self.request.user, instance=self.object)
        return form

    def form_valid(self, form):
        self.object = form.save()

    def render_content(self, parent_context=None):
        if hasattr(parent_context, "flatten"):
            parent_context = parent_context.flatten()

        if not hasattr(self.object, "render_as_content"):
            raise AdapterError(
                f"Object {self.object} does not have a render_as_content method"
            )
        
        return self.object.render_as_content(
            request=self.request,
            context=parent_context,
        )
