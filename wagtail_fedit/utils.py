from typing import Any
from django.http import HttpRequest
from django.db import models
from wagtail import hooks
from wagtail.blocks.stream_block import StreamValue
from wagtail.blocks.list_block import ListValue
from wagtail import blocks

from .hooks import (
    EXCLUDE_FROM_RELATED_FORMS,
    REGISTER_TYPE_RENDERER,
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




def _look_for_renderers():
    global _looked_for_renderers
    if not _looked_for_renderers:
        for hook in hooks.get_hooks(REGISTER_TYPE_RENDERER):
            hook(_renderer_map)
        _looked_for_renderers = True

_renderer_map = {}
_looked_for_renderers = False

def get_field_content(request, model_instance, field_name, context, content=None):

    if not content:
        # Check for a rendering method if it exists
        if hasattr(model_instance, f"render_fedit_{field_name}"):
            content = getattr(model_instance, f"render_fedit_{field_name}")(request, context=context)
        else:
            content = getattr(model_instance, field_name)

    for k, v in _renderer_map.items():
        if isinstance(content, k):
            content = v(request, context, content)

    # The content might be a streamblock etc, we can render it as a block
    # if isinstance(content, (blocks.BoundBlock, blocks.StructValue)):
    if hasattr(content, "render_as_block"):
        content = content.render_as_block(context)

    return content

