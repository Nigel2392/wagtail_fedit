from typing import Any, TYPE_CHECKING
from collections import namedtuple
from urllib.parse import urlencode
from django.db import models
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

from wagtail.models import (
    DraftStateMixin,
    WorkflowMixin,
    LockableMixin,
    PreviewableMixin
)
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.blocks.stream_block import StreamValue
from wagtail.blocks.list_block import ListValue
from wagtail import (
    hooks,
    blocks,
    VERSION as WAGTAIL_VERSION,
)

from .toolbar import (
    FeditAdapterComponent,
    FeditAdapterEditButton,
)
from .hooks import (
    EXCLUDE_FROM_RELATED_FORMS,
    REGISTER_TYPE_RENDERER,
    REGISTER_FIELD_RENDERER,
    CONSTRUCT_ADAPTER_TOOLBAR,
)


if TYPE_CHECKING:
    from .adapters.base import BaseAdapter


TEMPLATE_TAG_NAME = "fedit"
FEDIT_PREVIEW_VAR = "_wagtail_fedit_preview"
USERBAR_MODEL_VAR = "_wagtail_fedit_userbar_model"
LOG_ACTION_TEMPLATES_AVAILABLE = WAGTAIL_VERSION < (6, 1, 0)


class FeditPermissionCheck:
    @staticmethod
    def has_perms(request: HttpRequest, model: Any) -> bool:

        user = request
        if isinstance(request, HttpRequest):
            user = request.user
        
        if (
            not user.is_authenticated\
            or not user.has_perm("wagtailadmin.access_admin")\
            or not user.has_perm(f"{model._meta.app_label}.change_{model._meta.model_name}")    
        ):
            return False
        
        return True


class FeditIFrameMixin:
    ERROR_TITLE = _("Validation Errors")

    HEADING_SUPPORTS_DRAFTS = _("Publishing Required")
    TITLE_SUPPORTS_DRAFTS = _("The object you are editing supports drafts.")
    TEXT_PUBLISH_DRAFTS = _("You must publish %(model)s to make any changes visible.")

    HEADING_NO_DRAFTS = _("No Publishing Required")
    TITLE_NO_DRAFTS = _("The object you are editing does not support drafts.")
    TEXT_NO_DRAFTS = _("You are not required to publish this object to make this change visible.")


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["help_text"] = self.get_help_text()
        context["error_title"] = self.get_error_title()
        return context
    
    def get_error_title(self) -> str:
        return self.ERROR_TITLE

    def get_help_text(self) -> str:
        # No relations. Maybe draft support.
        if is_draft_capable(getattr(self, "absolute_instance", self.object)):
            return {
                "status": "warning",
                "heading": self.HEADING_SUPPORTS_DRAFTS,
                "title": self.TITLE_SUPPORTS_DRAFTS,
                "text": mark_safe(self.TEXT_PUBLISH_DRAFTS % {
                    "model": get_model_string(getattr(self, "absolute_instance", self.object), publish_url=True, request=self.request),
                })
            }
        
        return {
            "status": "info",
            "heading": self.HEADING_NO_DRAFTS,
            "title": self.TITLE_NO_DRAFTS,
            "text": mark_safe(self.TEXT_NO_DRAFTS)
        }


def use_related_form(field: models.Field) -> bool:
    """
    Check if a field should be included in the related forms.
    Internally used to make sure we use widgets instead
    of rendering a form for a Page, Image or Document model.
    """
    for hook in hooks.get_hooks(EXCLUDE_FROM_RELATED_FORMS):
        if hook(field):
            return False
    return True


def access_userbar_model(request: HttpRequest) -> models.Model:
    """
    Retrieve the model set for the userbar in the request.
    """
    if not hasattr(request, USERBAR_MODEL_VAR):
        return None
    
    return getattr(request, USERBAR_MODEL_VAR)

def with_userbar_model(request: HttpRequest, model: models.Model) -> HttpRequest:
    """
    Set the model to be available in the userbar.
    The request is shared easily between these contexts - might as well use it.
    """
    setattr(request, USERBAR_MODEL_VAR, model)
    return request

def get_block_name(block):
    """
    Return the block's type name for a block in a StreamField or ListBlock.
    eg. "heading", "paragraph", "image", "item", "column", etc.
    """
    if isinstance(block, StreamValue.StreamChild):
        return block.block_type
    elif isinstance(block, ListValue.ListChild):
        return "item"
    elif isinstance(block, ListValue):
        return block.block.name
    elif isinstance(block, (blocks.StructValue, blocks.BoundBlock)):
        return block.block.name
    else:
        raise ValueError("Unknown block type: %s" % type(block))
    
def get_block_path(block):
    """
    Get the current path part of a block in a StreamField or ListBlock.
    """
    if isinstance(block, StreamValue.StreamChild):
        return block.id
    elif isinstance(block, ListValue.ListChild):
        return block.id
    elif isinstance(block, ListValue):
        return block.block.name
    elif isinstance(block, (blocks.StructValue, blocks.BoundBlock)):
        return block.block.name
    else:
        raise ValueError("Unknown block type: %s" % type(block))

def find_block(block_id, field, contentpath=None):
    """
    Find a block in a StreamField or ListBlock by its ID.
    """
    if contentpath is None:
        contentpath = []

    # Check and cast field to iterable if necessary, but do not append non-StreamValue names to contentpath here.
    if not isinstance(field, StreamValue) and not hasattr(field, "__iter__"):
        field = [field]

    # Adjust for ListValue to get the iterable bound_blocks.
    if isinstance(field, ListValue):
        field = field.bound_blocks

    for block in field:
        # Determine the block's name only if needed to avoid premature addition to contentpath.
        block_name = get_block_path(block)
        
        if getattr(block, "id", None) == block_id:
            # Append the block name here as it directly leads to the target.
            return block, contentpath + [block_name]
        
        # Prepare to check children without altering the current path yet.
        if isinstance(block.value, blocks.StructValue):
            for _, value in block.value.bound_blocks.items():
                found, found_path = find_block(block_id, value, contentpath + [block_name])
                if found:
                    return found, found_path

        elif isinstance(block.value, (StreamValue, StreamValue.StreamChild, ListValue)):
            found, found_path = find_block(block_id, block.value, contentpath + [block_name])
            if found:
                return found, found_path

    # Return None and the current path if no block is found at this level.
    return None, contentpath



_renderer_map = {}
_field_renderer_map = {}
_looked_for_renderers = False


def _look_for_renderers():
    global _looked_for_renderers
    if not _looked_for_renderers:
        for hook in hooks.get_hooks(REGISTER_TYPE_RENDERER):
            hook(_renderer_map)

        for hook in hooks.get_hooks(REGISTER_FIELD_RENDERER):
            hook(_field_renderer_map)

        _looked_for_renderers = True


def get_field_content(request, instance, meta_field: models.Field, context, content=None):
    """
    Return the content for a field on a model.
    Also checks the model for a rendering method.
    The method should be named `render_fedit_{field_name}`.
    We wil also check for any hooks which may convert the content.
    """
    _look_for_renderers()

    if isinstance(meta_field, str):
        meta_field = instance._meta.get_field(meta_field)

    if hasattr(context, "flatten"):
        context = context.flatten()

    if not content:
        # Check for a rendering method if it exists
        if hasattr(instance, f"render_fedit_{meta_field.name}"):
            content = getattr(instance, f"render_fedit_{meta_field.name}")(request, context=context)
        else:
            content = getattr(instance, meta_field.name)

    for k, v in _field_renderer_map.items():
        if isinstance(meta_field, k):
            content = v(request, context, instance, content)
            break

    for k, v in _renderer_map.items():
        if isinstance(content, k):
            content = v(request, context, instance, content)
            break

    # The content might be a streamblock etc, we can render it as a block
    # if isinstance(content, (blocks.BoundBlock, blocks.StructValue)):
    if hasattr(content, "render_as_block"):
        content = content.render_as_block(context)

    # The content might otherwise have a render method.
    elif hasattr(content, "render"):
        content = content.render(context)

    return content

def is_draft_capable(model):
    """
    Check if a model is capable of drafts.
    """
    return isinstance(model, DraftStateMixin)\
        or type(model) == type\
        and issubclass(model, DraftStateMixin)

def model_diff(m1, m2):
    """
    Check if two model instances are different based on their type and primary key.
    Does not check for differences in the model's fields.
    This is used to determine if a relation is being saved.
    """
    return not (
        m1._meta.app_label == m2._meta.app_label
        and m1._meta.model_name == m2._meta.model_name\
        and m1.pk == m2.pk
    )


def edit_url(instance: models.Model, request: HttpRequest, hash = None, **params) -> str:
    """
        Return the edit URL for a given object and user (or request instead of user.)
        If none exists and the model is an instance of PreviewableMixin;
        return the wagtail_fedit:editable url; else an empty string.
    """

    user = request.user
    finder = AdminURLFinder(user)
    admin_url = finder.get_edit_url(instance)

    if not admin_url:

        # Check if the instance is a PreviewableMixin
        # and the user has permission to edit it.
        if isinstance(instance, PreviewableMixin)\
                and _can_edit(request, instance):
            
            admin_url = reverse(
                "wagtail_fedit:editable",
                args=[
                    instance.pk,
                    instance._meta.app_label,
                    instance._meta.model_name
                ],
            )
        else:
            return ""

    data = urlencode(params)
    if params:
        admin_url = f"{admin_url}?{data}"

    if hash:
        admin_url = f"{admin_url}#{hash}"
    
    return admin_url


def get_model_string(instance: models.Model, publish_url: bool = False, request: HttpRequest = None, target = "_blank", **params) -> str:
    """
    Get a string representation of a model instance. If the instance has a
    `get_admin_display_title` method, it will be used to get the string
    representation.
    If that method does not exist, the `title` attribute will be used.
    If the `title` attribute does not exist, the string representation of the
    instance will be used.
    If `publish_url` is True, the string will be wrapped in an anchor tag
    linking to the publish view for the instance.
    Permissions will not be checked. This is the responsibility of the caller.
    """
    model_string = getattr(instance, "get_admin_display_title", None)
    if model_string:
        model_string = model_string()
    else:
        model_string = getattr(instance, "title", str(instance))

    if publish_url:

        if is_draft_capable(instance):
            admin_url = reverse(
                "wagtail_fedit:publish",
                args=[
                    instance.pk,
                    instance._meta.app_label,
                    instance._meta.model_name
                ],
            )

            data = urlencode(params)
            if params:
                admin_url = f"{admin_url}?{data}"

        else:
            admin_url = edit_url(instance, request, **params)

        if admin_url:
            model_string = mark_safe(
                f'<a href="{admin_url}" target="{target}">{model_string}</a>'
            )

    return model_string

def _can_edit(request, obj: models.Model):
    """
    Check if the user has appropriate permissions to edit an object.
    Also requires the current request be on the `wagtail_fedit:editable` url
    (Or the preview variable to be True)
    """
    if not request or not obj:
        return False
    
    return (
        FeditPermissionCheck.has_perms(request, obj)\
        and getattr(request, FEDIT_PREVIEW_VAR, False)
    )

def user_can_publish(instance, user, check_for_changes: bool = True):
    """
    Check if a user can publish an object.
    Mostly comes from PagePermissionTester.can_publish
    """
    if not isinstance(instance, DraftStateMixin):
        return False
    
    if not instance.has_unpublished_changes\
        and check_for_changes:
        return False

    if hasattr(instance, "permission_policy"):
        return instance.permission_policy.user_has_permission(user, "publish")
    
    if not hasattr(instance, "permissions_for_user"):
        return False

    return instance.permissions_for_user(user).can_publish()

def user_can_unpublish(instance, user):
    """
    Check if a user can unpublish an object.
    Mostly comes from PagePermissionTester.can_unpublish
    """
    if not isinstance(instance, DraftStateMixin):
        return False
    
    if not hasattr(instance, "permissions_for_user"):
        return False
    
    return instance.permissions_for_user(user).can_unpublish()

def user_can_submit_for_moderation(instance, user, check_for_changes: bool = True):
    """
    Check if a user can submit an object for moderation.
    Mostly comes from PagePermissionTester.can_submit_for_moderation
    """
    if not getattr(settings, "WAGTAIL_WORKFLOW_ENABLED", True):
        return False

    if not instance.has_unpublished_changes\
        and check_for_changes:
        return False

    if not isinstance(instance, WorkflowMixin):
        return False
    
    if not hasattr(instance, "permissions_for_user"):
        return False
    
    return instance.permissions_for_user(user).can_submit_for_moderation()


_lock_info = namedtuple("lock_info", ["lock", "locked_for_user"])

def lock_info(object, user) -> _lock_info:
    """
        Returns the Lock instance (if any) and whether it is locked for the given user.
    """
    if isinstance(object, LockableMixin):
        lock = object.get_lock()
        locked_for_user = lock is not None and lock.for_user(
            user
        )
    else:
        lock = None
        locked_for_user = False

    return _lock_info(lock, locked_for_user)


def wrap_adapter(request: HttpRequest, adapter: "BaseAdapter", context: dict, run_context_processors: bool = False) -> str:
    if not context:
        context = {}

    items: list[FeditAdapterComponent] = [
        *adapter.get_toolbar_buttons(),
        FeditAdapterEditButton(request, adapter),
    ]

    for hook in hooks.get_hooks(CONSTRUCT_ADAPTER_TOOLBAR):
        hook(items=items, adapter=adapter)

    items = [item.render() for item in items]
    items = list(filter(None, items))

    reverse_kwargs = {
        "adapter_id": adapter.identifier,
        "app_label": adapter.object._meta.app_label,
        "model_name": adapter.object._meta.model_name,
        "model_id": adapter.object.pk,
    }

    if adapter.field_name is not None:
        reverse_kwargs["field_name"] = adapter.field_name

    shared = adapter.encode_shared_context()
    js_constructor = adapter.get_js_constructor()
    
    return render_to_string(
        "wagtail_fedit/content/editable_adapter.html",
        {
            "identifier": adapter.identifier,
            "adapter": adapter,
            "buttons": items,
            "shared": shared,
            "unique_id": adapter.get_element_id(),
            "js_constructor": js_constructor,
            "shared_context": adapter.kwargs,
            "parent_context": context,
            "edit_url": reverse(
                "wagtail_fedit:edit",
                kwargs=reverse_kwargs,
            ),
        },
        request=request if run_context_processors else None,
    )
