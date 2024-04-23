from typing import Any
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import View
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
    HttpResponse,
)
from django.apps import apps
from wagtail.models import (
    RevisionMixin,
    PAGE_TEMPLATE_VAR,
    Page,
)
from wagtail.admin.views.generic import WagtailAdminTemplateMixin

from ..adapters import (
    adapter_registry,
    BaseAdapter,
    RegistryLookUpError,
)
from ..utils import (
    FeditPermissionCheck,
    FeditIFrameMixin,
    FEDIT_PREVIEW_VAR,
    lock_info,
)
from .mixins import (
    LocaleMixin,
)

@method_decorator(xframe_options_sameorigin, name="dispatch")
class BaseAdapterView(FeditIFrameMixin, FeditPermissionCheck, WagtailAdminTemplateMixin, View):
    ERROR_TITLE = _("Validation Errors")

    def dispatch(self, 
            request:    HttpRequest,
            adapter_id: str = None,
            app_label:  str = None,
            model_name: str = None,
            model_id:   Any = None,
            field_name: str = None,
        ) -> None:

        # Fetch the adapter class from the registry
        try:
            self.adapter_class: BaseAdapter = adapter_registry[adapter_id]
        except RegistryLookUpError:
            return HttpResponseBadRequest("Invalid adapter ID")

        # Retrieve the model class
        try:
            self.model = apps.get_model(app_label, model_name)
            if not self.has_perms(request, self.model):
                return HttpResponseForbidden("You do not have permission to view this page")
        except LookupError:
            return HttpResponseBadRequest("Invalid model")

        # Only fetch latest reivision if it exists
        # If not; it will be automatically created by the form.
        model_instance = self.model._default_manager.get(pk=model_id)
        if isinstance(model_instance, RevisionMixin) and model_instance.latest_revision_id:
            self.instance = model_instance.latest_revision.as_object()
        else:
            self.instance = model_instance

        LocaleMixin.setup_locale(self.instance)

        if not field_name and self.adapter_class.field_required:
            return HttpResponseBadRequest("Field name is required for object")

        if field_name and not hasattr(self.instance, field_name) and self.adapter_class.field_required:
            return HttpResponseBadRequest("Invalid field name for object")

        shared_context = request.GET.get("shared_context")
        if shared_context:
            self.shared_context = self.adapter_class.decode_shared_context(
                request,
                self.instance,
                field_name,
                shared_context,
            )
        else:
            self.shared_context = {}

        self.adapter = self.adapter_class(
            request=request,
            object=self.instance,
            field_name=field_name,
            **self.shared_context,
        )

        self.lock, self.locked_for_user = lock_info(
            self.adapter.object, request.user,
        )

        setattr(
            self.request,
            FEDIT_PREVIEW_VAR,
            True,
        )

        return super().dispatch(
            request,
            adapter_id=adapter_id,
            field_name=field_name,
            app_label=app_label,
            model_name=model_name,
            model_id=model_id,
        )
    
    @property
    def template_name(self):
        return self.adapter.get_template_names()
    
    def render_to_response(self, context: dict[str, Any], success: bool = True, extra: dict = None, **response_kwargs: Any) -> HttpResponse:
        if not extra:
            extra = {}

        extra.update({
            "success": success,
        })

        context.update(extra)

        return render(
            self.request,
            self.template_name,
            context,
        )
            
    def get_header_title(self):
        return self.adapter.get_header_title()

    def get_help_text(self):
        return self.adapter.get_help_text()
    
    def get_context_data(self, **kwargs):
        shared_context = None
        if self.shared_context:
            shared_context =\
                self.request.GET["shared_context"]

        verbose_name = self.model._meta.verbose_name
        if self.adapter.field_required:
            verbose_name = self.adapter.meta_field.verbose_name

        extra = {}
        if "form" in kwargs:
            extra.update(
                self.adapter.get_form_context(
                    **kwargs,
                ),
            )

        if isinstance(self.instance, Page):
            # Add the page template variable to the context.
            # Wagtail uses this internally; for example in `{% wagtailpagecache %}`
            extra[PAGE_TEMPLATE_VAR] = self.instance

        return super().get_context_data(**kwargs) | {
            "verbose_name": verbose_name,
            "locked_for_user": self.locked_for_user,
            "shared_context": shared_context,
            "form_attrs": self.adapter.get_form_attrs(),
            "locked": self.lock is not None,
            **extra,
        }
    
class AdapterRefetchView(BaseAdapterView):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data()

        return JsonResponse({
            "success": True,
            "refetch": True,
            **self.adapter\
              .get_response_data(
                  context,
              ),
        })

class EditAdapterView(BaseAdapterView):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Can omit data from context - we are not rendering the content.
        form = self.adapter.get_form()

        return self.render_to_response(
            self.get_context_data(
                form=form,
            ),
            success=True,
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        form = self.adapter.get_form()

        if not form.is_valid() or self.locked_for_user:

            self.adapter.form_invalid(form)

            return JsonResponse({
                "success": False,
                "errors": form.errors,
                "locked": self.locked_for_user,
                "html": render_to_string(
                    self.template_name,
                    context=self.get_context_data(
                        form=form,
                    ),
                    request=request,
                )
            }, status=423 if self.locked_for_user else 400)

        
        self.adapter.form_valid(form)

        context = self.get_context_data()

        return JsonResponse({
            "success": True,
            **self.adapter\
              .get_response_data(context),
        })

