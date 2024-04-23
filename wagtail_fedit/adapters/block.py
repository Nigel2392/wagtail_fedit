from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.http import HttpRequest

from wagtail.log_actions import log
from wagtail.blocks import (
    StreamValue,
)
from wagtail.models import (
    RevisionMixin,
)

from .base import (
    BlockFieldReplacementAdapter,
    AdapterError,
    Keyword,
    VARIABLES,
)
from ..forms import (
    blocks as block_forms,
)
from .. import utils
from wagtail.admin.admin_url_finder import (
    AdminURLFinder,
)
from ..toolbar import (
    FeditAdapterComponent,
    FeditAdapterAdminLinkButton,
)



class BlockAdapter(BlockFieldReplacementAdapter):
    """
    An adapter for editing Wagtail blocks.
    This will render the block and replace it on the frontend
    on successful form submission.
    """
    identifier = "block"
    usage_description = "This adapter is used to edit a block of a streamfield."
    keywords = (
        Keyword("block",
            help_text="the block instance to edit. This can be a regular block instance or a BoundBlock.",
            type_hint="blocks.Block"
        ),
        Keyword("block_id",
            optional=True,
            help_text="the ID of the block to edit, required if block is not a BoundBlock.",
            type_hint="int"
        ),
        Keyword("admin",
            absolute=True,
            help_text="if passed; the adapter will a quick- link to the Wagtail Admin for this block."
        ),
    )

    def __init__(self, object: models.Model, field_name: str, request: HttpRequest, **kwargs):
        super().__init__(object, field_name, request, **kwargs)

        self.block = self.kwargs.pop("block", None)
        if self.block:
            if not hasattr(self.block, "id") and not "block_id" in self.kwargs:
                raise AdapterError("Invalid block type, block must have an `id` attribute or provide a `block_id`")
            
            if hasattr(self.block, "id"):
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

    @cached_property
    def tooltip(self) -> str:
        return self.get_header_title()

    def get_admin_url(self) -> str:
        finder = AdminURLFinder(self.request.user)
        url = finder.get_edit_url(self.object)
        hash = f"#block-{self.kwargs['block_id']}-section"
        return f"{url}{hash}"

    def get_toolbar_buttons(self) -> list[FeditAdapterComponent]:
        buttons = super().get_toolbar_buttons()
        if not self.kwargs.get("admin", False):
            return buttons
        
        buttons.append(FeditAdapterAdminLinkButton(
            self.request, self,
        ))
        return buttons

    def get_header_title(self):

        model_string = getattr(self.object, "get_admin_display_title", None)
        if model_string:
            model_string = model_string()
        else:
            model_string = getattr(self.object, "title", str(self.object))

        return _("Edit block %(block_label)s for %(model_name)s '%(model_string)s'") % {
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
    
    def check_permissions(self):
        return super().check_permissions() and getattr(
            self.block.block.meta, "feditable", True
        )

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
        