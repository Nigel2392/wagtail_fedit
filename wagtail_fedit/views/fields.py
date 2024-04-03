from typing import Any, Type
from django.db import models
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import View
from django.http import (
    HttpRequest,
    HttpResponseBadRequest,
    JsonResponse,
    HttpResponse,
)
from django.apps import apps

from wagtail.log_actions import log
from wagtail.models import (
    RevisionMixin, 
)
from wagtail.admin.views.generic import WagtailAdminTemplateMixin

import uuid

from ..templatetags.fedit import (
    BlockEditNode,
    render_editable_field,
)
from ..forms import (
    blocks as block_forms,
    fields as field_forms,
)
from ..utils import (
    FeditPermissionCheck,
    use_related_form,
    get_field_content,
)



@method_decorator(xframe_options_sameorigin, name="dispatch")
class EditFieldView(FeditPermissionCheck, WagtailAdminTemplateMixin, View):
    template_name = "wagtail_fedit/editor/field_iframe.html"

    def dispatch(self, request: HttpRequest, field_name = None, app_label = None, model_name = None, model_id = None) -> None:
        if not all([field_name, model_name, app_label, model_id]):
            return HttpResponseBadRequest("Missing required parameters")

        self.model = apps.get_model(app_label, model_name)
        if not self.has_perms(request, self.model):
            return HttpResponseBadRequest("You do not have permission to view this page")

        if issubclass(self.model, RevisionMixin):
            model_instance = self.model.objects.get(pk=model_id)
            self.instance = model_instance.latest_revision.as_object()
        else:
            self.instance = self.model._default_manager.get(pk=model_id)

        self.field_name = field_name
        self.model_name = model_name
        self.app_label = app_label
        self.model_id = model_id
        self.original_instance = self.instance
        self.field_value = getattr(self.instance, self.field_name)
        self.initial_field_value = self.field_value
        self.meta_field: models.Field = self.model._meta.get_field(self.field_name)

        keys = request.GET.keys()
        self.data = BlockEditNode.unpack(*keys, request=request)

        # Check if the field is a relation and if the value is a model
        # for the field instead of the form for the relation.
        if self.meta_field.is_relation and use_related_form(self.meta_field):
            # If the field is a model, we want to edit the model itself
            # We can do this by getting the fields from the model
            self.instance = self.field_value
            self.form_class = field_forms.get_form_class_for_fields(
                self.meta_field.related_model,
                getattr(
                    self.meta_field.related_model,
                    "fedit_fields", "__all__"
                ),
            )
        else:
            self.form_class = field_forms.get_form_class_for_fields(
                self.model,
                [field_name],
            )

        return super().dispatch(request, field_name, model_name, app_label, model_id)

    def get_header_title(self):
        meta_field: models.Field = self.model._meta.get_field(self.field_name)

        model_string = field_forms.get_model_string(self.original_instance)
        if self.original_instance != self.instance:
            instance_string = field_forms.get_model_string(self.instance)
            return _("Edit model %(instance_string)s for %(model_name)s %(model_string)s") % {
                "instance_string": instance_string,
                "model_name": self.model._meta.verbose_name,
                "model_string": model_string,
            }

        return _("Edit field %(field_name)s for %(model_name)s %(model_string)s") % {
            "field_name": meta_field.verbose_name,
            "model_name": self.model._meta.verbose_name,
            "model_string": model_string,
        }
    
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
    
    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "form_attrs": {
                "data-original-pk": self.original_instance.pk,
                "data-original-model": self.model_name,
                "data-original-app": self.app_label,
                "data-original-field": self.field_name,
                "data-is-relation": self.meta_field.is_relation\
                    and isinstance(self.field_value, models.Model),
            },
        }

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Can omit data from context - we are not rendering the content.
        form = self.form_class(request=request, instance=self.instance)
        return self.render_to_response(
            self.get_context_data(form=form),
            success=True,
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        form = self.form_class(request.POST, request=request, instance=self.instance)
        if form.is_valid():
            self.instance = form.save()
            
            # add data to context
            context = self.get_context_data(form=form, **self.data)

            # Check if we are saving a relation
            if self.instance.pk != self.original_instance.pk:
                self.meta_field.save_form_data(self.original_instance, self.instance)
                field_forms.save_possible_revision(self.original_instance, request)

            extra_log_kwargs = {}
            if isinstance(self.original_instance, RevisionMixin):
                extra_log_kwargs["revision"] = self.original_instance.latest_revision

            data = {
                "verbose_field_name": self.meta_field.verbose_name,
                "field_name": self.field_name,
                "model_id": self.model_id,
                "model_name": self.model_name,
                "app_label": self.app_label,
                "model_verbose": str(self.model._meta.verbose_name),
                "model_string": str(field_forms.get_model_string(self.original_instance)),
                "old": str(self.initial_field_value),
                "new": str(getattr(
                    self.original_instance,
                    self.field_name
                )),
            }

            uid = uuid.uuid4()
            if self.original_instance.pk != self.instance.pk:
                data.update({
                    "edited_model_string": str(field_forms.get_model_string(self.instance)),
                    "edited_model_verbose": str(self.instance._meta.verbose_name),
                    "edited_model_id": self.instance.pk,
                    "edited_model_name": self.instance._meta.model_name,
                    "edited_app_label": self.instance._meta.app_label,
                })

                log(
                    instance=self.instance,
                    action="wagtail_fedit.related_changed",
                    user=request.user,
                    uuid=uid,
                    data=data,
                    content_changed=True,
                )
            
            log(
                instance=self.original_instance,
                action="wagtail_fedit.edit_field",
                user=request.user,
                title=self.get_header_title(),
                uuid=uid,
                data=data,
                content_changed=True,
                **extra_log_kwargs,
            )

            content = get_field_content(
                request,
                self.original_instance,
                self.meta_field,
                context
            )

            # Render the frame HTML
            html = render_editable_field(
                self.request, content,
                self.field_name, self.original_instance,
                context=context,
                **self.data,
            )

            return JsonResponse({
                "success": True,
                "html": html,
            })

        return JsonResponse({
            "success": False,
            "errors": form.errors,
            "html": render_to_string(
                "wagtail_fedit/editor/field_iframe.html",
                context=self.get_context_data(form=form),
                request=request,
            )
        })

