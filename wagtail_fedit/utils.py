from typing import Any
from django.db import models
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from wagtail import hooks
from wagtail.models import DraftStateMixin
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.blocks.stream_block import StreamValue
from wagtail.blocks.list_block import ListValue
from wagtail import blocks

from .hooks import (
    EXCLUDE_FROM_RELATED_FORMS,
    REGISTER_TYPE_RENDERER,
    REGISTER_FIELD_RENDERER,
)


FEDIT_PREVIEW_VAR = "_wagtail_fedit_preview"
USERBAR_MODEL_VAR = "_wagtail_fedit_userbar_model"


class FeditPermissionCheck:
    @staticmethod
    def has_perms(request: HttpRequest, model: Any) -> bool:
        
        if (
            not request.user.is_authenticated\
            or not request.user.has_perm("wagtailadmin.access_admin")\
            or not request.user.has_perm(f"{model._meta.app_label}.change_{model._meta.model_name}")    
        ):
            return False
        
        return True


class FeditHelpTextMixin:
    HEADING_SUPPORTS_DRAFTS = _("Publishing Required")
    TITLE_SUPPORTS_DRAFTS = _("The object you are editing supports drafts.")
    TEXT_PUBLISH_DRAFTS = _("You must publish %(model)s to make any changes visible.")

    HEADING_NO_DRAFTS = _("No Publishing Required")
    TITLE_NO_DRAFTS = _("The object you are editing does not support drafts.")
    TEXT_NO_DRAFTS = _("You are not required to publish this object to make this change visible.")


    def get_help_text(self) -> str:
        # No relations. Maybe draft support.
        if is_draft_capable(self.instance):
            return {
                "status": "info",
                "heading": self.HEADING_SUPPORTS_DRAFTS,
                "title": self.TITLE_SUPPORTS_DRAFTS,
                "text": mark_safe(self.TEXT_PUBLISH_DRAFTS % {
                    "model": get_model_string(self.instance, publish_url=True, request=self.request),
                })
            }
        
        return {
            "status": "info",
            "heading": self.HEADING_NO_DRAFTS,
            "title": self.TITLE_NO_DRAFTS,
            "text": mark_safe(self.TEXT_NO_DRAFTS)
        }


def use_related_form(field: models.Field) -> bool:
    for hook in hooks.get_hooks(EXCLUDE_FROM_RELATED_FORMS):
        if hook(field):
            return False
    return True


def access_userbar_model(request: HttpRequest) -> models.Model:

    if not hasattr(request, USERBAR_MODEL_VAR):
        return None
    
    return getattr(request, USERBAR_MODEL_VAR)

def with_userbar_model(request: HttpRequest, model: models.Model) -> HttpRequest:
    setattr(request, USERBAR_MODEL_VAR, model)
    return request

def get_block_name(block):
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

    return content

def is_draft_capable(model):
    return isinstance(model, DraftStateMixin)\
        or type(model) == type\
        and issubclass(model, DraftStateMixin)

def saving_relation(m1, m2):
    return not (
        m1._meta.app_label == m2._meta.app_label
        and m1._meta.model_name == m2._meta.model_name\
        and m1.pk == m2.pk
    )


def get_model_string(instance: models.Model, publish_url: bool = False, request: HttpRequest = None, target = "_blank") -> str:
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

        else:
            finder = AdminURLFinder(request)
            admin_url = finder.get_edit_url(instance)

        if admin_url:
            model_string = mark_safe(
                f'<a href="{admin_url}" target="{target}">{model_string}</a>'
            )

    return model_string

