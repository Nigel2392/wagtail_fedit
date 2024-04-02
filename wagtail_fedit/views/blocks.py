from typing import Any
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import View
from django.urls import reverse
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    JsonResponse,
    HttpResponse,
)
from django.apps import apps

from wagtail.fields import StreamValue
from wagtail.models import RevisionMixin, Page
from wagtail.admin.views.generic import WagtailAdminTemplateMixin
from wagtail.log_actions import log
from ..templatetags.fedit import BlockEditNode
from .. import forms as block_forms
from .. import utils



@method_decorator(xframe_options_sameorigin, name="dispatch")
class EditBlockView(utils.FeditPermissionCheck, WagtailAdminTemplateMixin, View):
    template_name = "wagtail_fedit/editor/block_iframe.html"

    def dispatch(self, request: HttpRequest, block_id = None, field_name = None, model_id = None, model_name = None, app_label = None) -> None:

        self.edit_args = ["block_id", "field_name", "model_id", "model_name", "app_label"]
        if not all([block_id, field_name, model_id, model_name, app_label]):
            return HttpResponseBadRequest("Missing required parameters")
        
        self.block_id = block_id
        self.field_name = field_name
        self.model_id = model_id
        self.model_name = model_name
        self.app_label = app_label
        self.has_block = BlockEditNode.unpack("has_block", request=request)["has_block"].lower() == "true"


        self.model = apps.get_model(self.app_label, self.model_name)
        if not self.has_perms(request, self.model):
            return HttpResponseBadRequest("You do not have permission to view this page")


        if issubclass(self.model, RevisionMixin):
            self.model_instance = self.model.objects.get(pk=self.model_id)
            self.instance = self.model_instance.latest_revision.as_object()
        else:
            self.instance = self.model._default_manager.get(pk=self.model_id)
            self.model_instance = self.instance


        self.streamfield: StreamValue = getattr(self.instance, self.field_name)
        result = utils.find_block(self.block_id, self.streamfield)
        if not result:
            # raise ValueError("Block not found; did you provide the correct block ID?")
            return HttpResponseBadRequest("Block not found; did you provide the correct block ID?")


        self.block, self.contentpath = result
        self.form_class = block_forms.get_block_form_class(self.block.block)


        if not self.form_class:
            return HttpResponseBadRequest("Invalid block type")

        return super().dispatch(request, block_id, field_name, model_id, model_name, app_label)

    def get_page_title(self):

        model_string = getattr(self.instance, "get_admin_display_title", None)
        if model_string:
            model_string = model_string()
        else:
            model_string = getattr(self.instance, "title", str(self.instance))

        return _("Edit block %(block_label)s for %(model_name)s %(model_string)s") % {
            "block_label": self.block.block.label,
            "model_name": self.model._meta.verbose_name,
            "model_string": model_string,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        must = {
            "request": self.request,
            # "wagtail_fedit_instance": instance,
            "contentpath": self.contentpath,
            "block_id": self.block_id,
            "field_name": self.field_name,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "app_label": self.app_label,
            "block": self.block,
            "instance": self.instance,
            "streamfield": self.streamfield,
            "has_block": self.has_block,
            "wagtail_fedit_instance": self.instance,
            "wagtail_fedit_has_block": self.has_block,
            "edit_url": BlockEditNode.get_edit_url(
                self.block_id, self.field_name, self.instance,
            ),
            "form_attrs": {
                "data-block-id": self.block_id,
                "data-block-name": self.block.block.name,
            },
        }
        can = {
            "form_class": self.form_class,
        }

        if isinstance(self.instance, Page):
            admin_edit_url = reverse(
                "wagtailadmin_pages:edit",
                args=[self.instance.pk],
            )
            admin_edit_url = f"{admin_edit_url}#block-{self.block_id}-section"
        else:
            admin_edit_url = None

        must["admin_edit_url"] = admin_edit_url

        context.update(must)
        for key, value in can.items():
            context.setdefault(key, value)

        return context
    
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

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        form = self.form_class(block=self.block, parent_instance=self.instance, request=request)
        # Safe to omit data from context - we are not rendering the content.
        return self.render_to_response(
            self.get_context_data(form=form),
            success=True,
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        form = self.form_class(request.POST, block=self.block, parent_instance=self.instance, request=request)

        # Set the preview flag to mark as editable block when re-rendering.
        setattr(request, utils.FEDIT_PREVIEW_VAR, True)

        valid = form.is_valid()
        if valid:
            self.block = form.save()
        else:
            # We are not rendering the content, so we can omit data from context.
            return JsonResponse({
                "success": False,
                "errors": form.errors,
                "html": render_to_string(
                    "wagtail_fedit/editor/block_iframe.html",
                    context=self.get_context_data(form=form),
                    request=request,
                )
            })
        
        extra_log_kwargs = {}
        if isinstance(self.instance, RevisionMixin):
            extra_log_kwargs["revision"] = self.instance.latest_revision

        meta_field = self.model._meta.get_field(self.field_name)
        
        log(
            instance=self.instance,
            action="wagtail_fedit.edit_block",
            user=request.user,
            title=self.get_page_title(),
            data={
                "block_id": self.block_id,
                "field_name": self.field_name,
                "model_id": self.model_id,
                "model_name": self.model_name,
                "app_label": self.app_label,
                "verbose_field_name": str(meta_field.verbose_name),
                "block_label": str(self.block.block.label),
            },
            content_changed=True,
            **extra_log_kwargs,
        )

        # Add the data to the context and render the block.

        if self.has_block:
            keys = request.GET.keys()
            data = BlockEditNode.unpack(*keys, request=request)
            for key in self.edit_args:
                data.pop(key, None)

            node = BlockEditNode(
                None,
                self.block,
                block_id=self.block_id,
                field_name=self.field_name,
                model=self.instance,
                **data,
            )

            context = self.get_context_data()
            html = node.render(context)
        else:
            keys = request.GET.keys()
            data = BlockEditNode.unpack(*keys, request=request)
            html = self.block.block.render(self.block.value, self.get_context_data(**dict(data)))

        return JsonResponse({
            "success": True,
            "html": html,
        })

