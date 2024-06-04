from typing import Any, TYPE_CHECKING
from django.apps import apps
from django.utils.translation import gettext as _
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.views.decorators.clickjacking import (
    xframe_options_sameorigin,
)
from django.views.generic import View
from django.shortcuts import render
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
    HttpResponse,
)
from wagtail.models import (
    RevisionMixin,
    PAGE_TEMPLATE_VAR,
    Page,
)
from wagtail.admin.views.generic import (
    WagtailAdminTemplateMixin,
)

if TYPE_CHECKING:
    from ..adapters import BaseAdapter

from ..registry import (
    registry as adapter_registry,
    RegistryLookUpError,
)
from ..utils import (
    FeditPermissionCheck,
    FeditIFrameMixin,
    FEDIT_PREVIEW_VAR,
    base_adapter_context,
    lock_info,
)
from ..errors import (
    NO_PERMISSION_ACTION,
    INVALID,
    REQUIRED,
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
            self.adapter_class: "BaseAdapter" = adapter_registry[adapter_id]
        except RegistryLookUpError:
            return HttpResponseBadRequest(
                INVALID.format(
                    _("Adapter ID")
                )
            )

        # Retrieve the model class
        try:
            self.model = apps.get_model(app_label, model_name)
        except LookupError:
            return HttpResponseBadRequest(
                INVALID.format(
                    _("Model")
                )
            )
        
        # Check if the user has permissions to view the page
        if not self.has_perms(request, self.model):
            return HttpResponseForbidden(NO_PERMISSION_ACTION.format(
                _("view this page")
            ))

        # Only fetch latest reivision if it exists
        # If not; it will be automatically created by the form.
        model_instance = self.model._default_manager.get(pk=model_id)
        if isinstance(model_instance, RevisionMixin) and model_instance.latest_revision_id:
            self.instance = model_instance.latest_revision.as_object()
        else:
            self.instance = model_instance

        LocaleMixin.setup_locale(
            self.instance,
        )

        if not field_name and self.adapter_class.field_required:
            return HttpResponseBadRequest(
                REQUIRED.format(
                    _("Field name"),
                    self.instance,
                )
            )

        if field_name and not hasattr(self.instance, field_name) and self.adapter_class.field_required:
            return HttpResponseBadRequest(
                INVALID.format(
                    _("field name"),
                    self.instance,
                )
            )

        shared_context_str: dict = request.GET.get("shared_context")
        if shared_context_str:
            self.shared_context = self.adapter_class.decode_shared_context(
                request,
                self.instance,
                field_name,
                shared_context_str,
            )
        else:
            self.shared_context = {}

        self.adapter: "BaseAdapter" = self.adapter_class(
            request=request,
            object=self.instance,
            field_name=field_name,
            **self.shared_context,
        )

        if not self.adapter.check_permissions():
            return HttpResponseForbidden(
                NO_PERMISSION_ACTION.format(
                    _("edit this field")
                )
            )

        self.lock, self.locked_for_user = lock_info(
            self.adapter.object, request.user,
        )

        setattr(
            self.request,
            FEDIT_PREVIEW_VAR,
            True,
        )

        could_respond = self.before_dispatch()
        if isinstance(could_respond, HttpResponse):
            return could_respond

        return super().dispatch(
            request,
            adapter_id=adapter_id,
            field_name=field_name,
            app_label=app_label,
            model_name=model_name,
            model_id=model_id,
        )
    
    def before_dispatch(self) -> HttpResponse | None:
        pass

    @classmethod
    def prefix_url_path(cls, name: str, *suffix: str) -> str:
        suffix_url = ""
        
        if suffix:
            suffix_url = f"{'/'.join(suffix)}"
        
        if suffix_url and not suffix_url.endswith("/"):
            suffix_url += "/"

        return f"{name}/<str:adapter_id>/<str:app_label>/<str:model_name>/<str:model_id>/<str:field_name>/{suffix_url}"
    
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
        shared_context_str = None
        if self.shared_context:
            shared_context_str =\
                self.request.GET["shared_context"]

        verbose_name = self.model._meta.verbose_name
        if self.adapter.field_required:
            verbose_name = self.adapter.meta_field.verbose_name

        extra = {}

        if isinstance(self.instance, Page):
            # Add the page template variable to the context.
            # Wagtail uses this internally; for example in `{% wagtailpagecache %}`
            extra[PAGE_TEMPLATE_VAR] = self.instance

        if "wagtail_template_page_instance" in self.adapter.kwargs:
            extra[PAGE_TEMPLATE_VAR] = self.adapter.kwargs["wagtail_template_page_instance"]

        # Form context; used for rendering the modal.
        if "form" in kwargs:
            extra.update({
                "verbose_name": verbose_name,
                "locked_for_user": self.locked_for_user,
                "shared_context": self.shared_context,
                "shared_context_str": shared_context_str,
                "form_attrs": self.adapter.get_form_attrs(),
                "locked": self.lock is not None,
                **self.adapter.get_form_context(
                    **kwargs,
                ),
            })
        # Add adapter context instead of form context
        else:
            extra = base_adapter_context(
                self.adapter,
                extra,
            )

        return super().get_context_data(**kwargs)\
            | extra
    
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

