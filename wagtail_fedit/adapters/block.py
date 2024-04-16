from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.http import HttpRequest

from wagtail.log_actions import log
from wagtail.blocks import (
    StreamValue,
    BoundBlock,
)
from wagtail.models import (
    RevisionMixin,
)

from .base import (
    BaseAdapter,
    AdapterError,
    VARIABLES,
)
from ..forms import (
    blocks as block_forms,
)
from .. import utils




class BlockAdapter(BaseAdapter):
    identifier = "block"
    required_kwargs = ["block"]
    js_constructor = "wagtail_fedit.editors.BlockEditor"

    def __init__(self, object: models.Model, field_name: str, request: HttpRequest, **kwargs):
        super().__init__(object, field_name, request, **kwargs)

        self.block = self.kwargs.pop("block", None)
        if self.block:
            if not isinstance(self.block, BoundBlock):
                raise AdapterError("Invalid block type")

            self.kwargs["block_id"] = self.block.id
        else:
            block_id = self.kwargs.get("block_id", None)
            if block_id is None:
                raise AdapterError("Block ID is required")
            
            self.streamfield: StreamValue = getattr(self.object, self.field_name)
            result = utils.find_block(block_id, self.streamfield)
            if not result:
                raise AdapterError("Block not found; did you provide the correct block ID?")
            
            self.block, _ = result

    def get_header_title(self):

        model_string = getattr(self.object, "get_admin_display_title", None)
        if model_string:
            model_string = model_string()
        else:
            model_string = getattr(self.object, "title", str(self.object))

        return _("Edit block %(block_label)s for %(model_name)s %(model_string)s") % {
            "block_label": self.block.block.label,
            "model_name": self.model._meta.verbose_name,
            "model_string": model_string,
        }
    
    def get_element_id(self) -> str:
        return f"block-{self.kwargs['block_id']}-section"
    
    def get_form_attrs(self) -> dict:

        size = getattr(self.block.block.meta, VARIABLES.PY_SIZE_VAR, None)
        if size:
            return super().get_form_attrs() | {
                VARIABLES.FORM_SIZE_VAR: size,
            }
        
        return {}

    def get_form(self):

        self.form_class = block_forms.get_block_form_class(self.block.block)

        if self.request.method == "POST":
            form = self.form_class(self.request.POST, block=self.block, parent_instance=self.object, request=self.request)
        else:
            form = self.form_class(block=self.block, parent_instance=self.object, request=self.request)
        return form
    
    def form_valid(self, form: block_forms.BlockEditForm):
        self.block = form.save()

        extra_log_kwargs = {}
        if isinstance(self.object, RevisionMixin):
            extra_log_kwargs["revision"] = self.object.latest_revision

        with translation.override(None):
            log(
                instance=self.object,
                action="wagtail_fedit.edit_block",
                user=self.request.user,
                title=self.get_header_title(),
                data={
                    "block_id": self.kwargs["block_id"],
                    "field_name": self.field_name,
                    "model_id": self.object.pk,
                    "model_name": self.object._meta.model_name,
                    "app_label": self.object._meta.app_label,
                    "verbose_field_name": str(self.meta_field.verbose_name),
                    "block_label": str(self.block.block.label),
                },
                content_changed=True,
                **extra_log_kwargs,
            )

    @classmethod
    def render_from_kwargs(cls, context, **kwargs):
        if "block" not in kwargs:
            raise AdapterError("Block is required")
        
        block = kwargs.pop("block")
        if not hasattr(block, "render"):
            raise AdapterError("Invalid block type, missing render method")
        
        return block.render(context)

    def render_content(self, parent_context: dict = None) -> str:
        parent_context = parent_context or {}
        if hasattr(parent_context, "flatten"):
            parent_context = parent_context.flatten()

        parent_context.update(self.kwargs)

        return self.block.render(parent_context)
        