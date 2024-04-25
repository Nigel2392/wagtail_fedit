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
    Keyword,
    BlockFieldReplacementAdapter,
    AdapterError,
)
from ..forms import (
    PossibleRevisionFormMixin,
)
from ..utils import (
    get_model_string,
)
from wagtail.admin.admin_url_finder import (
    AdminURLFinder,
)
from ..toolbar import (
    FeditAdapterComponent,
    FeditAdapterAdminLinkButton,
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
    keywords = BlockFieldReplacementAdapter.keywords + (
        Keyword(
            "admin",
            absolute=True,
            help_text="If passed; the adapter will add a quick-link to the Wagtail Admin for this model.",
        ),
        Keyword(
            "render_method",
            optional=True,
            default="render_as_content",
            help_text="The method to call on the object to render it as content. Default is 'render_as_content'.",
        ),
    )

    def __init__(self, object, field_name: str, request: HttpRequest, **kwargs):
        super().__init__(object, field_name, request, **kwargs)
        if isinstance(self.object, Page):
            self.edit_handler = page_utils._get_page_edit_handler(
                self.object.__class__,
            )
        else:
            self.edit_handler = model_utils.get_edit_handler(
                self.object.__class__,
            )

    def get_admin_url(self) -> str:
        finder = AdminURLFinder(self.request.user)
        return finder.get_edit_url(self.object)

    def get_toolbar_buttons(self) -> list[FeditAdapterComponent]:
        buttons = super().get_toolbar_buttons()
        if not self.kwargs["admin"]:
            return buttons
        
        buttons.append(FeditAdapterAdminLinkButton(
            self.request, self,
        ))
        return buttons


    def get_form_attrs(self) -> dict:
        attrs = super().get_form_attrs()
        if isinstance(self.edit_handler, TabbedInterface):
            attrs[VARIABLES.FORM_SIZE_VAR] = "full"
        elif len(self.edit_handler.children) > 4:
            attrs[VARIABLES.FORM_SIZE_VAR] = "large"
        return attrs
    
    def get_form_context(self, **kwargs):
        context = super().get_form_context(**kwargs)
        bound_panel = self.edit_handler.get_bound_panel(
            instance=self.object, request=self.request, form=kwargs["form"],
        )
        context["edit_handler"] = bound_panel
        return context

    @property
    def form_class(self):
        cls = self.edit_handler.get_form_class()
        class RevisionModelForm(PossibleRevisionFormMixin, cls):
            pass
        return RevisionModelForm

    def form_valid(self, form):
        self.object = form.save()

    def get_form(self):
        if self.request.method == "POST":
            form = self.form_class(self.request.POST, for_user=self.request.user, instance=self.object, request=self.request)
        else:
            form = self.form_class(for_user=self.request.user, instance=self.object, request=self.request)
        return form

    def get_header_title(self):
        instance_string = get_model_string(self.object)
        return _("Edit model %(type)s '%(instance_string)s'") % {
            "type": self.object._meta.verbose_name,
            "instance_string": instance_string,
        }
    
    def get_help_text(self):
        return None
          
    def get_element_id(self) -> str:
        m = self.model
        return f"model-{m._meta.app_label}-{m._meta.model_name}-{self.object.pk}"

    def form_valid(self, form):
        self.object = form.save()

    def render_content(self, parent_context=None):
        if hasattr(parent_context, "flatten"):
            parent_context = parent_context.flatten()

        method_name = self.kwargs["render_method"]
        if not hasattr(self.object, method_name):
            raise AdapterError(
                "Object '%s' does not have any method named '%s'" % (
                    self.object.__class__.__name__,
                    method_name,
                )
            )
        method = getattr(
            self.object,
            method_name
        )
        return method(
            request=self.request,
            context=parent_context,
        )
