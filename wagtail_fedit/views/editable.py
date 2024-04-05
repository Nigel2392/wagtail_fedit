from typing import Any, Union, Type
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.urls import reverse
from django.apps import apps
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponse,
)
from wagtail.admin import messages
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.actions.publish_page_revision import PublishPageRevisionAction
from wagtail.actions.publish_revision import PublishRevisionAction
from wagtail.actions.unpublish_page import UnpublishPageAction
from wagtail.actions.unpublish import UnpublishAction
from wagtail.admin.views.generic import WagtailAdminTemplateMixin
from wagtail.permission_policies import ModelPermissionPolicy
from wagtail.models import (
    RevisionMixin,
    PreviewableMixin,
    DraftStateMixin,
    WorkflowMixin,
    WorkflowState,
    Page,
)
from .. import forms as block_forms
from ..utils import (
    FEDIT_PREVIEW_VAR,
    USERBAR_MODEL_VAR,
    FeditPermissionCheck,
    with_userbar_model,
    user_can_publish,
    user_can_unpublish,
    user_can_submit_for_moderation,
)

from ..toolbar import (
    FeditToolbarComponent,
)



def get_unpublish_action(object):
    if isinstance(object, Page):
        return UnpublishPageAction
    return UnpublishAction


def get_publish_action(object):
    if isinstance(object, Page):
        return PublishPageRevisionAction
    return PublishRevisionAction


class FeditableModelComponent(FeditToolbarComponent):
    def __init__(self, instance):
        self.instance = instance


class ActionPublishComponent(FeditableModelComponent):
    template_name = "wagtail_fedit/editor/buttons/publish.html"
    check_for_changes: bool = True

    def get_context_data(self, request):
        return super().get_context_data(request) | {
            "hidden": not self.instance.has_unpublished_changes,
        }
    
    def is_shown(self, request):
        if not super().is_shown(request):
            return False
        
        return user_can_publish(self.instance, request.user, check_for_changes=self.check_for_changes)

class ActionUnpublishComponent(FeditableModelComponent):
    template_name = "wagtail_fedit/editor/buttons/unpublish.html"
    
    def is_shown(self, request):
        if not super().is_shown(request):
            return False
        
        return user_can_unpublish(self.instance, request.user)
    
class ActionSubmitComponent(FeditableModelComponent):
    template_name = "wagtail_fedit/editor/buttons/submit.html"
    check_for_changes: bool = True

    def get_context_data(self, request):
        return super().get_context_data(request) | {
            "hidden": not self.instance.has_unpublished_changes,
        }

    def is_shown(self, request):
        if not super().is_shown(request):
            return False
        
        return user_can_submit_for_moderation(self.instance, request.user, check_for_changes=self.check_for_changes)

class BaseFeditView(FeditPermissionCheck, TemplateView):
    def dispatch(self, request: HttpRequest, object_id: Any, app_label: str, model_name: str) -> HttpResponse:
        try:
            self.model = apps.get_model(app_label, model_name)
            self.model_object = self.model._default_manager.get(pk=object_id)
        except (self.model.DoesNotExist, LookupError):
            return HttpResponseBadRequest("Invalid model provided")

        if not self.has_perms(request, self.model):
            return HttpResponseForbidden("You do not have permission to view this page")

        if issubclass(self.model, RevisionMixin) and self.model_object.latest_revision_id:
            instance: RevisionMixin  = self.model_object
            revision: RevisionMixin = instance.latest_revision
            self.object = revision.as_object()
            self.is_preview = True
        else:
            self.object = self.model_object
            self.is_preview = False

        try:
            self.checks(request, self.object)
        except ValueError as e:
            return HttpResponseForbidden(str(e))

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
    

@method_decorator(xframe_options_sameorigin, name="dispatch")
class FeditablePublishView(WagtailAdminTemplateMixin, BaseFeditView):
    template_name = "wagtail_fedit/editor/publish_confirm.html"
    buttons: list[Type[FeditToolbarComponent]] = [
        ActionPublishComponent,
        ActionSubmitComponent,
        ActionUnpublishComponent,
    ]
    object: DraftStateMixin


    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:

        buttons = []

        for button in self.buttons:
            buttons.append(button(self.object).render(self.request))

        buttons = list(filter(None, buttons))

        return super().get_context_data(**kwargs) | {
            "buttons": buttons,
            "object": self.object,
            "model_verbose_name": self.object._meta.verbose_name,
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

        policy = self.object.permissions_for_user(request.user)

        if not isinstance(self.object, DraftStateMixin):
            raise ValueError("Model {} does not inherit from DraftStateMixin, cannot publish.".format(self.model))
        
        if getattr(settings, "WAGTAIL_WORKFLOW_ENABLED", True) and issubclass(self.model, WorkflowMixin):
            # Retrieve current workflow state if set, default to last workflow state
            self.workflow_state = (
                self.object.current_workflow_state
                or self.object.workflow_states.order_by("created_at").last()
            )
        else:
            self.workflow_state = None


        if request.POST.get("action-publish") == "1"\
                and policy.can_publish()\
                and self.object.has_unpublished_changes:
            return self.publish(request)
        
        if request.POST.get("action-unpublish") == "1" and policy.can_unpublish():
            return self.unpublish(request)
        
        if request.POST.get("action-submit") == "1"\
                and policy.can_submit_for_moderation()\
                and isinstance(self.object, WorkflowMixin)\
                and self.object.has_unpublished_changes:
            return self.submit_for_moderation(request)
        
        if request.POST.get("action-cancel") == "1"\
                and self.workflow_state\
                and self.workflow_state.user_can_cancel(self.request.user):
            return self.cancel_workflow(request)
        
        messages.error(request, _("Invalid form submission"))
        return self.get(request, *args, **kwargs)
    
    def publish(self, request: HttpRequest) -> HttpResponse:
        latest_revision = None
        if isinstance(self.object, RevisionMixin):
            latest_revision = self.object.latest_revision

        action = get_publish_action(self.object)(
            revision=latest_revision,
            user=request.user,
        )

        action.execute()

        if latest_revision:
            self.object = latest_revision.as_object()

        return self.redirect_to_success_url(request)
    
    def unpublish(self, request: HttpRequest) -> HttpResponse:
        if not self.object.live:
            messages.error(request, _("This object is not live"))
            return self.get(request)
        
        action = get_unpublish_action(self.object)(
            self.object,
            user=request.user,
        )

        action.execute()

        return self.redirect_to_failsafe_url(request)
    
    def submit_for_moderation(self, request: HttpRequest) -> HttpResponse:
        if (
            self.workflow_state
            and self.workflow_state.status == WorkflowState.STATUS_NEEDS_CHANGES
        ):
            # If the workflow was in the needs changes state, resume the existing workflow on submission
            self.workflow_state.resume(self.request.user)
        else:
            # Otherwise start a new workflow
            workflow = self.object.get_workflow()
            workflow.start(self.object, self.request.user)

        return self.redirect_to_success_url(request)

    def cancel_workflow(self, request: HttpRequest) -> HttpResponse:
        if self.workflow_state:
            self.workflow_state.cancel(user=self.request.user)
            return self.redirect_to_success_url(request)
        
        return self.get(request)

    def redirect_to_success_url(self, request: HttpRequest) -> HttpResponse:
        if hasattr(self.object, "get_url"):
            return redirect(self.object.get_url(request))
        
        elif hasattr(self.object, "get_absolute_url"):
            return redirect(self.object.get_absolute_url())
        
        return redirect(reverse(
            "wagtail_fedit:editable",
            args=[self.object.pk, self.model._meta.app_label, self.model._meta.model_name],
        ))

    def redirect_to_failsafe_url(self, request: HttpRequest) -> HttpResponse:
        try:
            finder = AdminURLFinder(request.user)
            edit_url = finder.get_edit_url(self.object)
            return redirect(edit_url)
        except Exception:
            return redirect(reverse(
                "wagtail_fedit:editable",
                args=[self.object.pk, self.model._meta.app_label, self.model._meta.model_name],
            ))
