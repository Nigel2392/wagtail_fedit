import uuid
from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.http import HttpRequest

from wagtail.log_actions import log
from wagtail.models import RevisionMixin
from wagtail import hooks

from .base import (
    BaseAdapter,
    VARIABLES,
)
from ..hooks import (
    FIELD_EDITOR_SIZE,
)
from ..utils import (
    use_related_form,
    model_diff,
    get_model_string,
    get_field_content,
    is_draft_capable,
    FeditIFrameMixin,
)
from ..forms import (
    fields as field_forms,
)



class FieldAdapter(BaseAdapter):
    identifier = "field"

    def __init__(self, object, field_name: str, request: HttpRequest, **kwargs):
        super().__init__(object, field_name, request, **kwargs)

        self.original_object = object
        self.initial_field_value = self.field_value

        if self.meta_field.is_relation and use_related_form(self.meta_field):
            # If the field is a model, we want to edit the model itself
            # We can do this by getting the fields from the model
            self.object = self.field_value
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


    def get_header_title(self):
        meta_field: models.Field = self.model._meta.get_field(self.field_name)

        model_string = get_model_string(self.original_object)
        if self.original_object != self.object:
            instance_string = get_model_string(self.object)
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
    
    def get_help_text(self):
        if is_draft_capable(self.original_object)\
                and is_draft_capable(self.object)\
                and model_diff(self.object, self.original_object):
            return {
                "status": "warning",
                "heading": FeditIFrameMixin.HEADING_SUPPORTS_DRAFTS,
                "title": FeditIFrameMixin.TITLE_SUPPORTS_DRAFTS,
                "text": mark_safe(_("You must publish %(model)s and the related object of type %(related_verbose_name)s (%(related_model)s) to make any changes visible.") % {
                    "model": get_model_string(self.original_object, publish_url=True, request=self.request),
                    "related_verbose_name": self.object._meta.verbose_name,
                    "related_model": get_model_string(self.object, publish_url=True, request=self.request),
                })
            }

        elif is_draft_capable(self.original_object)\
                and not is_draft_capable(self.object)\
                and model_diff(self.object, self.original_object):
            return {
                "status": "warning",
                "heading": FeditIFrameMixin.HEADING_SUPPORTS_DRAFTS,
                "title": FeditIFrameMixin.TITLE_SUPPORTS_DRAFTS,
                "text": mark_safe(FeditIFrameMixin.TEXT_PUBLISH_DRAFTS % {
                    "model": get_model_string(self.original_object, publish_url=True, request=self.request),
                })
            }
        
        elif not is_draft_capable(self.original_object)\
                and is_draft_capable(self.object)\
                and model_diff(self.object, self.original_object):
            return {
                "status": "warning",
                "heading": _("Publishing related object required."),
                "title": _("The object you are editing supports drafts."),
                "text": mark_safe(_("You must publish the related object of type %(type)s (%(model)s) to make any changes visible.") % {
                    "type": self.original_object._meta.verbose_name,
                    "model": get_model_string(self.original_object, publish_url=True, request=self.request),
                })
            }

        return super().get_help_text()
          
    def get_element_id(self) -> str:
        m = self.model
        return f"field-{self.field_name}-{m._meta.app_label}-{m._meta.model_name}-{self.object.pk}"
      
    def get_form_attrs(self) -> dict:
        attrs = super().get_form_attrs()

        size = getattr(self.object, f"{VARIABLES.PY_SIZE_VAR}_{self.field_name}", None)
        if not size:

            for hook in hooks.get_hooks(FIELD_EDITOR_SIZE):
                size = hook(self.object, self.meta_field)
                if size:
                    break
            
        if not size \
          and self.meta_field.is_relation \
          and use_related_form(self.meta_field):
            size = "full"
        
        if size:
            return attrs | {
                VARIABLES.FORM_SIZE_VAR: size,
            }
        
        return attrs

    def get_form(self):
        if self.request.method == "POST":
            form = self.form_class(self.request.POST, request=self.request, instance=self.object)
        else:
            form = self.form_class(request=self.request, instance=self.object)
        return form

    def form_valid(self, form):
        self.object = form.save()

        # Check if we are saving a relation
        if model_diff(self.object, self.original_object):
            self.meta_field.save_form_data(self.original_object, self.object)
            field_forms.save_possible_revision(self.original_object, self.request)

        extra_log_kwargs = {}
        if isinstance(self.original_object, RevisionMixin):
            extra_log_kwargs["revision"] = self.original_object.latest_revision

        with translation.override(None):
            data = {
                "verbose_field_name": str(self.meta_field.verbose_name),
                "field_name": self.field_name,
                "model_id": self.object.pk,
                "model_name": self.object._meta.model_name,
                "app_label": self.object._meta.app_label,
                "model_verbose": str(self.model._meta.verbose_name),
                "model_string": str(get_model_string(self.original_object)),
                "old": str(self.initial_field_value),
                "new": str(getattr(
                    self.original_object,
                    self.field_name
                )),
            }

            uid = uuid.uuid4()
            if self.original_object.pk != self.object.pk:
                data.update({
                    "edited_model_string": str(get_model_string(self.object)),
                    "edited_model_verbose": str(self.object._meta.verbose_name),
                    "edited_model_id": self.object.pk,
                    "edited_model_name": self.object._meta.model_name,
                    "edited_app_label": self.object._meta.app_label,
                })

                log(
                    instance=self.object,
                    action="wagtail_fedit.related_changed",
                    user=self.request.user,
                    uuid=uid,
                    data=data,
                    content_changed=True,
                )

            log(
                instance=self.original_object,
                action="wagtail_fedit.edit_field",
                user=self.request.user,
                uuid=uid,
                data=data,
                content_changed=True,
                **extra_log_kwargs,
            )


    def render_content(self, parent_context=None):
        return get_field_content(
            self.request,
            self.original_object,
            self.meta_field,
            parent_context,
        )
