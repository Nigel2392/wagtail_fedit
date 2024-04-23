
from typing import Type
from django import forms
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

from ..hooks import (
    REGISTER_FIELD_WIDGETS,
)

from wagtail import hooks



_looked_for_widgets = False
_widgets = {}


def _look_for_widgets():
    global _looked_for_widgets
    if not _looked_for_widgets:
        _looked_for_widgets = True
        for fn in hooks.get_hooks(REGISTER_FIELD_WIDGETS):
            _widgets.update(fn(_widgets))


def get_widget_for_field(field: models.Field) -> Type[forms.Widget]:
    """
    Return a widget for a field.
    """
    _look_for_widgets()
    global _widgets

    if isinstance(field, models.ForeignKey):
        field = field.related_model
        widget = _widgets.get(field)
    else:
        widget = _widgets.get(field.__class__)

    if widget is None:
        pass

    return widget


def save_possible_revision(instance: models.Model, request: HttpRequest, **kwargs) -> models.Model:
    """
    Save an instance as a revision if the model supports it.
    """
    if isinstance(instance, RevisionMixin):
        instance = instance.save_revision(
            user=request.user,
            **kwargs,
        )
        instance = instance.as_object()
    else:
        instance.save()

    return instance


def get_form_class_for_fields(form_model: models.Model, form_fields: list[str]) -> Type["PossibleRevisionForm"]:
    """
    Return a form class for a model with specific fields.
    This is similar to django's modelform_factory, but with the added benefit of using the custom widgets.
    It also keeps the revision functionality in mind.
    """

    if hasattr(form_model, "get_fedit_form"):
        return form_model.get_fedit_form(form_fields)
    
    if form_fields == "__all__" or tuple(form_fields) == ("__all__", ):
        form_fields = [f.name for f in form_model._meta.fields]
    
    form_widgets = {}
    for field_name in form_fields:
        field = form_model._meta.get_field(field_name)
        widget = get_widget_for_field(field)
        if widget:
            form_widgets[field_name] = widget

    class RevisionForm(PossibleRevisionForm):
        class Meta:
            model = form_model
            fields = form_fields
            widgets = form_widgets

    return RevisionForm


class PossibleRevisionFormMixin:
    """
    A form that can save a revision if the model is a RevisionMixin.
    Otherwise resorts to the default save method; this saves the (live) instance.
    """
    def __init__(self, *args, request = None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        self.instance = super().save(commit=False)
        if commit:
            self.instance = save_possible_revision(
                self.instance,
                self.request,
            )
        return self.instance


class PossibleRevisionForm(PossibleRevisionFormMixin, WagtailAdminModelForm):
    pass
