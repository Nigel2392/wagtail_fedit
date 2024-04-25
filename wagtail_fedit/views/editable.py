from typing import Any
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils import translation
from django.urls import reverse
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponse,
)
from wagtail.admin import messages
from wagtail.log_actions import (
    registry,
)
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.actions.publish_page_revision import PublishPageRevisionAction
from wagtail.actions.publish_revision import PublishRevisionAction
from wagtail.actions.unpublish_page import UnpublishPageAction
from wagtail.actions.unpublish import UnpublishAction
from wagtail.models import (
    RevisionMixin,
    PreviewableMixin,
    DraftStateMixin,
    WorkflowMixin,
    WorkflowState,
    PageLogEntry,
    ModelLogEntry,
    Page,
)
from ..utils import (
    FEDIT_PREVIEW_VAR,
    USERBAR_MODEL_VAR,
    LOG_ACTION_TEMPLATES_AVAILABLE,
    FeditPermissionCheck,
    with_userbar_model,
    # user_can_publish,
    # user_can_unpublish,
    # user_can_submit_for_moderation,
    # lock_info,
)
from ..errors import (
    NO_PERMISSION_VIEW,
    NO_PERMISSION_ACTION,
    NO_WORKFLOW_STATE,
    OBJECT_LOCKED,
    OBJECT_NOT_LIVE,
    ACTION_MISSING,
    INVALID_ACTION,
    MISSING_REQUIRED_SUPERCLASSES,
    NO_UNPUBLISHED_CHANGES,
)
from .mixins import (
    ObjectViewMixin,
    LockViewMixin,
    LocaleMixin,
)


MAX_LOG_ENTRIES_DISPLAYED = 5


def get_unpublish_action(object):
    if isinstance(object, Page):
        return UnpublishPageAction
    return UnpublishAction


def get_publish_action(object):
    if isinstance(object, Page):
        return PublishPageRevisionAction
    return PublishRevisionAction



class BaseFeditView(LocaleMixin, ObjectViewMixin, FeditPermissionCheck, TemplateView):
    def dispatch(self, request: HttpRequest, object_id: Any, app_label: str, model_name: str) -> HttpResponse:
        if self.error_response:
            return self.error_response

        if not self.has_perms(request, self.object):
            return HttpResponseForbidden(NO_PERMISSION_VIEW)

        if issubclass(self.model, RevisionMixin) and self.object.latest_revision_id:
            instance: RevisionMixin  = self.object
            revision: RevisionMixin = instance.latest_revision
            self.object = revision.as_object()
            self.is_preview = True
        else:
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
            raise ValueError(MISSING_REQUIRED_SUPERCLASSES.format(self.model))

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # # Check if lock applies to this user
        # if not self.locked_for_user:
        self.request = with_userbar_model(self.request, self.object)

        object: PreviewableMixin = self.object
        return object.make_preview_request(original_request=self.request, extra_request_attrs={
            FEDIT_PREVIEW_VAR: True,
            USERBAR_MODEL_VAR: self.object,
        })
    

class BaseActionView(LockViewMixin, BaseFeditView):
    template_name         = "wagtail_fedit/editor/action_confirm.html"
    required_superclasses = [DraftStateMixin]
    action_icon            = None
    action_text            = None
    title_format           = None
    action_help_text_title = None
    action_help_text       = None

    def get_action(self) -> str:
        return self.action_text
    
    def get_action_value(self) -> str:
        return f"{self.__class__.__name__.lower()}"

    def get_action_title(self) -> str:
        return self.title_format.format(self.object)
    
    def get_action_help_text_title(self) -> str:
        return self.action_help_text_title
    
    def get_action_help_text(self) -> str:
        return self.action_help_text
    
    def get_action_icon(self) -> str:
        return self.action_icon
    
    def setup(self, request: HttpRequest, object_id: Any, app_label: str, model_name: str) -> HttpResponse:
        super().setup(request, object_id, app_label, model_name)
        self.policy = self.object.permissions_for_user(request.user)

        if not isinstance(self.object, tuple(self.required_superclasses)):
            self.error_response = HttpResponseBadRequest(
                MISSING_REQUIRED_SUPERCLASSES.format(
                    self.model.__name__, ", ".join(
                        [cls.__name__ for cls in self.required_superclasses],
                    )
                )
            )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(**kwargs) | {
            "action": self.get_action_value(),  # e.g. "publishview"
            "action_text": self.get_action(),
            "action_title": self.get_action_title(),
            "action_help_text_title": self.get_action_help_text_title(),
            "action_help_text": self.get_action_help_text(),
            "action_icon": self.get_action_icon(),
            "cancel_url": reverse(
                "wagtail_fedit:editable",
                args=[self.object.pk, self.model._meta.app_label, self.model._meta.model_name],
            ),
        }

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
        
    def check_policy(self, request: HttpRequest, policy: FeditPermissionCheck) -> None:
        pass

    def action(self, request: HttpRequest) -> HttpResponse:
        raise NotImplementedError("Subclasses must implement this method")
    
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        
        if getattr(settings, "WAGTAIL_WORKFLOW_ENABLED", True) and issubclass(self.model, WorkflowMixin):
            # Retrieve current workflow state if set, default to last workflow state
            self.workflow_state = (
                self.object.current_workflow_state
                or self.object.workflow_states.order_by("created_at").last()
            )
        else:
            self.workflow_state = None

        try:
            self.check_policy(request, self.policy)
        except ValueError as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)

        # Check if lock applies to this user
        if self.locked_for_user:
            messages.error(request, OBJECT_LOCKED)
            return self.redirect_to_failsafe_url(request)
        
        if "action" not in request.POST:
            messages.error(request, ACTION_MISSING)
            return redirect(request.path)
        
        if request.POST["action"] != self.get_action_value():
            messages.error(request, INVALID_ACTION.format(request.POST["action"]))
            return redirect(request.path)
        
        return self.action(request)


class PublishView(BaseActionView):
    template_name = "wagtail_fedit/editor/action_publish_confirm.html"
    required_superclasses = [DraftStateMixin, RevisionMixin]
    action_text = _("Publish")
    action_icon = "fedit-eye-open"

    def get_action_title(self):
        return _("Publishing {} \"{}\"").format(self.object._meta.verbose_name, self.object)

    def get_action_help_text_title(self):
        return _("About publishing")

    def get_action_help_text(self):
        s = [
            _("Publishing this object will make it visible to users on the site."),
            _("That means that any changes you make will be immediately visible to everyone."),
        ]

        if self.policy.can_unpublish():
            s.append(_("You can always choose to unpublish it."))

        return s
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        log_entry_count = 0
        log_entry_model = registry.get_log_model_for_model(self.object.__class__)
        if issubclass(log_entry_model, PageLogEntry):
            log_entries = log_entry_model.objects\
                .filter(page=self.object)\
                .order_by("-timestamp")
            
            context["view_more_url"] = reverse(
                "wagtailadmin_pages:history",
                args=[self.object.pk],
            )
                
        elif issubclass(log_entry_model, ModelLogEntry):
            log_entries = log_entry_model.objects\
                .filter(object_id=self.object.pk)\
                .filter(content_type=ContentType.objects.get_for_model(self.object))\
                .order_by("-timestamp")
                
        else:
            log_entries = None

        has_existing_published = log_entries.filter(action="wagtail.publish").exists()
        if log_entries and has_existing_published:
            log_entries = log_entries.filter(
                timestamp__gt=models.Subquery(
                    log_entries.filter(action="wagtail.publish")\
                               .values("timestamp")\
                               .order_by("-timestamp")[:1]
                )
            )

            log_entries = log_entries.select_related(
                "revision", "user", "user__wagtail_userprofile",
            )

            # if not self.request.user.is_superuser or\
            #    not self.request.user.is_staff:
            #     log_entries = log_entries.filter(user=self.request.user)

            if isinstance(self.object, Page):
                log_entries = log_entries.select_related("page")
            else:
                log_entries = log_entries.select_related("content_type")

            log_entry_count = log_entries.count()
            log_entries = log_entries[:MAX_LOG_ENTRIES_DISPLAYED]


        context.update({
            "log_entries": log_entries,
            "has_more_entries": log_entry_count > MAX_LOG_ENTRIES_DISPLAYED,
            "log_entry_count": log_entry_count,
            "last_published_at": self.object.last_published_at,
            "is_page": isinstance(self.object, Page),
            
            "LOG_ACTION_TEMPLATES_AVAILABLE": LOG_ACTION_TEMPLATES_AVAILABLE,
        })

        return context

    def check_policy(self, request: HttpRequest, policy: FeditPermissionCheck) -> None:
        if not policy.can_publish():
            raise ValueError(str(NO_PERMISSION_ACTION.format(
                _("publish")
            )))
        
        if self.locked_for_user:
            raise ValueError(str(OBJECT_LOCKED))
        
        if not self.object.has_unpublished_changes:
            raise ValueError(str(NO_UNPUBLISHED_CHANGES))

    def action(self, request: HttpRequest) -> HttpResponse:
        latest_revision = self.object.latest_revision

        if not latest_revision:
            latest_revision = self.object.save_revision(
                user=request.user,
            )

        action = get_publish_action(self.object)(
            revision=latest_revision,
            user=request.user,
        )

        action.execute()

        if latest_revision:
            self.object = latest_revision.as_object()

        return self.redirect_to_success_url(request)


class UnpublishView(BaseActionView):
    required_superclasses = [DraftStateMixin]
    action_icon = "fedit-eye-closed"
    action_text = _("Unpublish")
    action_help_text_title = _("About unpublishing")
    action_help_text = [
        _("Unpublishing this object will make it invisible to users on the site."),
        _("That means that it will no longer be visible to anyone."),
        _("You can always choose to publish it again."),
    ]

    def get_action_title(self):
        return _("Unpublishing {} \"{}\"").format(self.object._meta.verbose_name, self.object)
    
    def check_policy(self, request: HttpRequest, policy: FeditPermissionCheck) -> None:
        if not policy.can_unpublish():
            raise ValueError(str(NO_PERMISSION_ACTION.format(
                _("unpublish")
            )))
        
        if self.locked_for_user:
            raise ValueError(str(OBJECT_LOCKED))
        
        if not self.object.live:
            raise ValueError(str(OBJECT_NOT_LIVE))
 
    def action(self, request: HttpRequest) -> HttpResponse:
        if not self.object.live:
            messages.error(request, OBJECT_NOT_LIVE)
            return self.get(request)
        
        action = get_unpublish_action(self.object)(
            self.object,
            user=request.user,
        )

        action.execute()

        return self.redirect_to_failsafe_url(request)


class SubmitView(BaseActionView):
    required_superclasses = [DraftStateMixin, WorkflowMixin, RevisionMixin]
    action_icon = "fedit-check-list"
    action_text = _("Submit for moderation")
    action_help_text_title = _("About submitting for moderation")
    action_help_text = [
        _("Submitting this object for moderation will make it invisible to users on the site."),
        _("That means that it will no longer be visible to anyone."),
        _("You can always choose to publish it again."),
    ]

    def get_action_title(self):
        return _("Submitting {} \"{}\" for moderation").format(self.object._meta.verbose_name, self.object)

    def check_policy(self, request: HttpRequest, policy: FeditPermissionCheck) -> None:
        if not policy.can_submit_for_moderation():
            raise ValueError(str(NO_PERMISSION_ACTION.format(
                _("submit for moderation")
            )))
        
        if not self.object.has_unpublished_changes:
            raise ValueError(str(NO_UNPUBLISHED_CHANGES))
   
    def action(self, request: HttpRequest) -> HttpResponse:
        
        latest_revision = getattr(self.object, "latest_revision", None)
        if not latest_revision:
            latest_revision = self.object.save_revision(
                user=request.user,
            )

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


class CancelView(BaseActionView):
    required_superclasses = [DraftStateMixin, WorkflowMixin]
    action_icon = "fedit-stop-sign"
    action_text = _("Cancel Workflow")
    action_help_text_title = _("About cancelling workflows")
    action_help_text = [
        _("Cancelling the workflow for this object will remove it from the moderation process."),
        _("That means that it will no longer be visible to anyone."),
        _("You can always choose to submit it for moderation again."),
    ]

    def get_action_title(self):
        return _("Cancelling workflow for {} \"{}\"").format(self.object._meta.verbose_name, self.object)

    def check_policy(self, request: HttpRequest, policy: FeditPermissionCheck) -> None:
        if not self.workflow_state:
            raise ValueError(str(NO_WORKFLOW_STATE))
        
        if not self.workflow_state.user_can_cancel(request.user):
            raise ValueError(str(NO_PERMISSION_ACTION.format(
                _("cancel the workflow")
            )))

    def action(self, request: HttpRequest) -> HttpResponse:
        if self.workflow_state:
            self.workflow_state.cancel(user=self.request.user)
            return self.redirect_to_success_url(request)
        
        return self.get(request)
