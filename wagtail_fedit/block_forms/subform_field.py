from typing import Any, Type
from django import forms
from django.http import (
    HttpRequest,
)
from wagtail import blocks
from .utils import get_block_name

class SubformValidationError(forms.ValidationError):
    def __init__(self, message, code=None, params=None):
        if isinstance(message, dict):
            self.subform_errors = message
            message = list(message.values())
        else:
            self.subform_errors = {}
        super().__init__(message, code, params)

    def __repr__(self):
        return str(self.subform_errors)


class SubFormWidget(forms.Widget):
    def __init__(self,
            block:   blocks.BoundBlock,
            form:    forms.Form,
            request: HttpRequest,
            attrs=None,
        ):
        self.block = block
        self.form = form
        self.request = request
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        return self.form.as_p()
    
    def value_from_datadict(self, data, files, name):
        return self.form.__class__(data=data, files=files, prefix=name, block=self.block, request=self.request)

    def format_value(self, value: Any):
        return value

    @property
    def media(self):
        return self.form.media
    

class BlockEditSubFormField(forms.Field):
    def __init__(self,
            block: blocks.BoundBlock,
            form: Type[forms.Form],
            request: HttpRequest, 
            *args,
            **kwargs
        ):
        self.block:   blocks.BoundBlock = block
        self.request: HttpRequest = request

        if self.request.method == "POST":
            self.form = form(prefix=self.block_name, data=request.POST, block=block, request=request)
        else:
            self.form = form(prefix=self.block_name, block=block, request=request)

        super().__init__(*args, **kwargs)
        self.widget = SubFormWidget(block, self.form, request)

    @property
    def block_name(self):
        return get_block_name(self.block)

    def validate(self, value: Any):
        super().validate(value)

        if not value.is_valid():
            raise SubformValidationError(value.errors)

    def clean(self, value: Any) -> Any:
        value = super().clean(value)
        return value.save()
