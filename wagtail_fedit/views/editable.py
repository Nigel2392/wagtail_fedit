from typing import Any, Union
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.apps import apps
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponse,
)

from wagtail.admin.views.generic import WagtailAdminTemplateMixin
from wagtail.models import (
    RevisionMixin,
    PreviewableMixin,
    DraftStateMixin,
)
from .. import forms as block_forms
from ..utils import (
    FEDIT_PREVIEW_VAR,
    USERBAR_MODEL_VAR,
    FeditPermissionCheck,
    with_userbar_model,
)


class BaseFeditView(FeditPermissionCheck, TemplateView):
    def dispatch(self, request: HttpRequest, object_id: Any, app_label: str, model_name: str) -> HttpResponse:

        self.model = apps.get_model(app_label, model_name)
        self.model_object = self.model._default_manager.get(pk=object_id)

        if not self.has_perms(request, self.model):
            return HttpResponseBadRequest("You do not have permission to view this page")

        if issubclass(self.model, (RevisionMixin, PreviewableMixin)):
            instance: RevisionMixin  = self.model_object
            revision: Union[PreviewableMixin, RevisionMixin] = instance.latest_revision
            self.object = revision.as_object()
            self.is_preview = True
        else:
            self.object = self.model_object
            self.is_preview = False

        try:
            self.checks(request, self.object)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        return super().dispatch(request, object_id, app_label, model_name)
    
    def checks(self, request: HttpRequest, object: Any) -> None:
        pass

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(**kwargs) | {
            "object": self.object,
            "model": self.model,
        }

class FEditableView(BaseFeditView):

    def checks(self, request: HttpRequest, object: Any) -> None:
        super().checks(request, object)
        if not isinstance(self.object, PreviewableMixin):
            raise ValueError("Model {} does not inherit from PreviewableMixin, cannot edit.".format(self.model))

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.request = with_userbar_model(self.request, self.object)
        object: PreviewableMixin = self.object
        return object.make_preview_request(original_request=self.request, extra_request_attrs={
            FEDIT_PREVIEW_VAR: True,
            USERBAR_MODEL_VAR: self.object,
        })
        

class FeditablePublishView(WagtailAdminTemplateMixin, BaseFeditView):
    template_name = "wagtail_fedit/editor/publish_confirm.html"
    object: DraftStateMixin

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(**kwargs) | {
            "model_verbose_name": self.object._meta.verbose_name,
            "object": self.object,
            "publish_url": reverse(
                "wagtail_fedit:publish",
                args=[self.object.pk, self.model._meta.app_label, self.model._meta.model_name],
            ),
            "edit_url": reverse(
                "wagtail_fedit:editable",
                args=[self.object.pk, self.model._meta.app_label, self.model._meta.model_name],
            ),
        }
    
    def get_header_title(self):
        return _("Publishing {} \"{}\"").format(self.object._meta.verbose_name, self.object)

    def checks(self, request: HttpRequest, object: Any) -> None:
        if not isinstance(self.object, DraftStateMixin):
            raise ValueError("Model {} does not inherit from DraftStateMixin, cannot publish.".format(self.model))
    
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:

        if "publish" not in request.POST:
            return HttpResponseBadRequest("You must confirm the publish action")
        
        latest_revision = None
        if isinstance(self.object, RevisionMixin):
            latest_revision = self.object.latest_revision

        self.object.publish(
            revision=latest_revision,
            user=request.user,
            skip_permission_checks=False,
        )

        if latest_revision:
            self.object = latest_revision.as_object()

        # messages.success(
        #     request,
        #     _("Published {} \"{}\"").format(
        #         self.object._meta.verbose_name,
        #         self.object
        #     )
        # )
            
        if hasattr(self.object, "get_url"):
            return redirect(self.object.get_url(request))
        
        elif hasattr(self.object, "url"):
            return redirect(self.object.url)
        
        elif hasattr(self.object, "get_absolute_url"):
            return redirect(self.object.get_absolute_url())
        
        return redirect(reverse(
            "wagtail_fedit:editable",
            args=[self.object.pk, self.model._meta.app_label, self.model._meta.model_name],
        ))
