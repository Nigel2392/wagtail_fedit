from django import forms
from django.http import (
    HttpRequest,
)

from wagtail import blocks
from wagtail import hooks

from globlocks.blocks import BaseBlockConfiguration
import inspect

from ..hooks import REGISTER_BLOCK_HOOK_NAME
from .subform_field import BlockEditSubFormField



block_map = {
    blocks.CharBlock: (forms.CharField, forms.TextInput),
    blocks.TextBlock: (forms.CharField, forms.Textarea),
    blocks.IntegerBlock: forms.IntegerField,
    blocks.FloatBlock: forms.FloatField,
    blocks.DecimalBlock: forms.DecimalField,
    blocks.BooleanBlock: forms.BooleanField,
    blocks.DateBlock: forms.DateField,
    blocks.TimeBlock: forms.TimeField,
    blocks.DateTimeBlock: forms.DateTimeField,
    blocks.URLBlock: forms.URLField,
    blocks.EmailBlock: forms.EmailField,
    blocks.ChoiceBlock: lambda block, request: forms.ChoiceField(choices=block._constructor_kwargs["choices"]),
    blocks.MultipleChoiceBlock: lambda block, request: forms.MultipleChoiceField(choices=block._constructor_kwargs["choices"]),
    blocks.RawHTMLBlock: (forms.CharField, forms.Textarea),
    blocks.RichTextBlock: lambda block, request: block.field,
}

_looked_for_conversions = False

def look_for_conversions():
    global _looked_for_conversions
    if _looked_for_conversions:
        return

    _looked_for_conversions = True

    for hook in hooks.get_hooks(REGISTER_BLOCK_HOOK_NAME):
        hook(block_map)
