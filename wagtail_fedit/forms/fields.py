
from typing import Type
from django.db import models
from django.utils.translation import gettext as _
from django.http import (
    HttpRequest,
)
from wagtail.admin.forms import (
    WagtailAdminModelForm,
)
from wagtail.models import (
    RevisionMixin,
)



class PossiblePreviewForm(WagtailAdminModelForm):
    def __init__(self, *args, request = None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance = save_possible_revision(instance, self.request)
        return instance

def save_possible_revision(instance: models.Model, request: HttpRequest, **kwargs) -> models.Model:
    if isinstance(instance, RevisionMixin):
        instance = instance.save_revision(
            user=request.user,
            **kwargs,
        )
        instance = instance.as_object()
    else:
        instance.save()

    return instance

def get_form_class_for_fields(form_model: models.Model, form_fields: list[str]) -> Type[WagtailAdminModelForm]:

    if hasattr(form_model, "get_fedit_form"):
        return form_model.get_fedit_form(form_fields)

    class Form(PossiblePreviewForm):
        class Meta:
            model = form_model
            fields = form_fields

    return Form
