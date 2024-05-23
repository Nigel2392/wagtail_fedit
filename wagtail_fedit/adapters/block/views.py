from typing import (
    TYPE_CHECKING,
)
from django import forms
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import (
    render,
)
from django.utils import translation
from django.utils.translation import (
    gettext_lazy as _,
)
from wagtail.blocks import (
    BlockWidget,
    StreamValue,
    StreamBlock,
    ListBlock,
)
from wagtail.blocks.list_block import (
    ListValue,
)
from wagtail.log_actions import (
    log,
)
from wagtail.models import (
    RevisionMixin,
)
from ...utils import (
    insert_many,
    save_revision,
)
from ...views import (
    BaseAdapterView,
)

if TYPE_CHECKING:
    from .adapter import (
        BlockAdapter,
    )


class BlockMoveAdapterView(BaseAdapterView):
    adapter: "BlockAdapter"
    
    def post(self, request, *args, **kwargs):

        if not self.adapter.kwargs["movable"]:
            return JsonResponse({
                "error": "Block is not movable"
            })
        
        action = self.request.GET.get("action")
        idx = self.adapter.block_index
        parent = self.adapter.parent
        if action.lower() == "up":
            if idx > 0 and idx < len(parent):
                if isinstance(parent, StreamValue):
                    parent._raw_data[idx], parent._raw_data[idx - 1] = parent._raw_data[idx - 1], parent._raw_data[idx]
                    parent[idx], parent[idx - 1] = parent[idx - 1], parent[idx]
                elif isinstance(parent, ListValue):
                    parent.bound_blocks[idx], parent.bound_blocks[idx - 1] = parent.bound_blocks[idx - 1], parent.bound_blocks[idx]
            else:
                return JsonResponse({"error": "Cannot move block up"})

        elif action.lower() == "down":
            if idx < len(parent) - 1 and idx >= 0:
                if isinstance(parent, StreamValue):
                    parent._raw_data[idx], parent._raw_data[idx + 1] = parent._raw_data[idx + 1], parent._raw_data[idx]
                    parent[idx], parent[idx + 1] = parent[idx + 1], parent[idx]
                elif isinstance(parent, ListValue):
                    parent.bound_blocks[idx], parent.bound_blocks[idx + 1] = parent.bound_blocks[idx + 1], parent.bound_blocks[idx]
                # if isinstance(parent, StreamValue):
                    # parent._raw_data[idx], parent._raw_data[idx + 1] = parent._raw_data[idx + 1], parent._raw_data[idx]
            else:
                return JsonResponse({"error": "Cannot move block down"})
        else:
            return JsonResponse({"error": "Invalid action"})
        
        self.adapter.object = save_revision(
            self.adapter.object,
            self.request.user,
        )

        with translation.override(None):
            log(
                instance=self.adapter.object,
                action="wagtail_fedit.move_block",
                user=self.request.user,
                data={
                    "model_id": self.adapter.object.pk,
                    "model_name": self.adapter.object._meta.model_name,
                    "app_label": self.adapter.object._meta.app_label,
                    "field_name": self.adapter.meta_field.verbose_name,
                    "block_label": self.adapter.block.block.label,
                    "block_id": self.adapter.kwargs["block_id"],
                    "direction": action,
                },
                content_changed=True,
            )

        return JsonResponse({
            "success": True,
        })
    
class BlockAddAdapterView(BaseAdapterView):
    adapter: "BlockAdapter"
    template_name = "wagtail_fedit/editor/block_adapter_iframe.html"

    def before_dispatch(self) -> HttpResponse | None:
        if isinstance(self.adapter.parent, StreamValue):
            self.blank_value = StreamValue(self.adapter.parent.stream_block, [])
            self.parent_block: StreamBlock = self.adapter.parent.stream_block
        elif isinstance(self.adapter.parent, ListValue):
            self.blank_value: ListBlock = ListValue(self.adapter.parent.list_block, [])
            self.parent_block = self.adapter.parent.list_block
        else:
            return HttpResponseBadRequest("Invalid parent block type: %s" % type(self.adapter.parent))

    def get_header_title(self):

        model_string = getattr(self.adapter.object, "get_admin_display_title", None)
        if model_string:
            model_string = model_string()
        else:
            model_string = getattr(self.adapter.object, "title", str(self.adapter.object))

        label = self.parent_block.label
        if not label:
            label = self.parent_block.__class__.__name__

        return _("Adding block to '%(block_label)s' for %(model_name)s '%(model_string)s'") % {
            "block_label": label,
            "model_name": self.model._meta.verbose_name,
            "model_string": model_string,
        }


    def get(self, request, *args, errors=None, **kwargs):

        widget = BlockWidget(self.parent_block)
        form_html = widget.render_with_errors(
            "wagtail-fedit-block-add",
            self.blank_value,
            errors=errors,
        )
        context = self.get_context_data(
            form_html=form_html,
            media=widget.media,
        )
        return self.render_to_response(context)


    def post(self, request, *args, **kwargs):
        value = self.parent_block.value_from_datadict(
            self.request.POST,
            self.request.FILES,
            prefix="wagtail-fedit-block-add",
        )

        try:
            self.parent_block.clean(value)
        except forms.ValidationError as e:
            return self.get(request, errors=e)

        insert_many(
            self.adapter.parent,
            self.adapter.block_index,
            value,
        )

        self.adapter.object = save_revision(
            self.adapter.object,
            self.request.user,
        )

        return JsonResponse({
            "success": True,
        })
    
