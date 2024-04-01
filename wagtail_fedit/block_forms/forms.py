from django import forms
from django.http import (
    HttpRequest,
)
from django.db import models
from wagtail import blocks
from wagtail.models import RevisionMixin
import inspect

from . import utils
from .subform_field import (
    BlockEditSubFormField,
    SubformValidationError,
)
from .field_conversions import (
    block_map, look_for_conversions,
)


def get_field_for_block(field_name, parent_instance: blocks.BoundBlock, block: blocks.Block, request: HttpRequest):

    if not utils.can_fedit(block):
        # Marked as not editable on the frontend.
        return None

    elif type(block) in block_map:
        widget = None
        field = block_map[type(block)]
        
        if isinstance(field, tuple):
            field, widget = field
        
        if isinstance(field, dict):
            field = field["func"](block, request)

        if inspect.isfunction(field):
            field = field(block, request)

        if type(field) == type:
            field = field(
                widget=widget,
                required=getattr(block.meta, "required", False),
                label=getattr(block.meta, "label", None),
                help_text=getattr(block.meta, "help_text", None),
            )

    elif isinstance(block, blocks.StructBlock):

        form_class = get_form_class(
            parent_instance.value.bound_blocks[field_name],
            block,
            request,
            base_class=BaseBlockEditForm
        )

        if not form_class:
            return None

        field = BlockEditSubFormField(
            parent_instance.value.bound_blocks[field_name],
            form_class,
            request,
        )

    elif hasattr(block, "field"):
        field = block.field

    else:
        return None
        # raise ValueError("Invalid block type: %s" % type(block))
    
    return field



def get_form_class(instance: blocks.BoundBlock, block: blocks.Block, request, base_class=None):
    look_for_conversions()

    if not base_class:
        base_class = BlockEditForm

    if hasattr(block, "fedit_form_class"):
        return block.fedit_form_class()

    if isinstance(block, blocks.StructBlock):
        fields = []
        for field_name, sub in block.child_blocks.items():

            #if isinstance(sub, (blocks.StructBlock, blocks.StreamBlock, blocks.ListBlock, blocks.RichTextBlock)):
            #    continue
            field = get_field_for_block(field_name, instance, sub, request)
            if not field:
                continue

            field.help_text = getattr(sub.meta, "help_text", field.help_text)

            fields.append(
                (field_name, field)
            )

        return type(
            block.__class__.__name__ + "Form",
            (base_class,),
            dict(fields),
        )
    
    field = get_field_for_block("value", instance, block, request)
    if not field:
        return None
    
    field.label = block.label
    field.help_text = getattr(block.meta, "help_text", field.help_text)

    return type(
        block.__class__.__name__ + "Form",
        (base_class,),
        {"value": field},
    )



class BaseBlockEditForm(forms.Form):
    def __init__(self, *args, block: blocks.BoundBlock, request: HttpRequest, **kwargs):
        self.block = block
        self.request = request
        self._subform_errors = {}
        kwargs["initial"] = utils.get_initial_for_form(block, block)
        super().__init__(*args, **kwargs)

    # def add_error(self, field: str | None, error: forms.ValidationError | str) -> None:
    #     if isinstance(error, SubformValidationError):
    #         self._subform_errors[field] = error.subform_errors
    #     else:
    #         super().add_error(field, error)
# 
    # def has_error(self, field: str, code: str | None = ...) -> bool:
    #     return super().has_error(field, code) or field in self._subform_errors

    def clean(self):
        cleaned_data = super().clean()

        if hasattr(self.block, "fedit_clean"):
            self.block.fedit_clean(cleaned_data, self.parent_instance)
            return cleaned_data
    
        if isinstance(self.block, blocks.BoundBlock):
            block = self.block.block
            if hasattr(block, "fedit_clean"):
                block.fedit_clean(cleaned_data, self.parent_instance)
                return cleaned_data
            
            if isinstance(self.block.value, blocks.StructValue):
                for field_name, sub in block.child_blocks.items():
                    if field_name not in cleaned_data:
                        continue

                    value = cleaned_data.get(field_name)
                    if isinstance(value, blocks.BoundBlock):
                        value = value.value
                    try:
                        if hasattr(sub, "field"):
                            value = sub.field.clean(value)
                        else:
                            value = sub.clean(value)
                        
                        if isinstance(value, blocks.BoundBlock):
                            value = value.value

                        cleaned_data[field_name] = value

                    except blocks.StructBlockValidationError as e:
                        sub = block.child_blocks[field_name]
                        for name, b in sub.child_blocks.items():
                            if name in e.block_errors:
                                errors = e.block_errors[name]
                                del e.block_errors[name]
                                e.block_errors[b.label] = errors

                        for name, errors in e.block_errors.items():
                            self.add_error(field_name, f"{name}: {', '.join(errors)}")

            else:
                self.cleaned_data["value"] = block.clean(cleaned_data["value"])

        return cleaned_data
    
    @property
    def errors(self):
        errors = super().errors
        errors.update(self._subform_errors)
        return errors

    def save(self):
        block = self.block

        if hasattr(block, "fedit_save"):
            block.fedit_save(self.cleaned_data, self.parent_instance)
        else:

            if isinstance(block, blocks.BoundBlock):

                if hasattr(block.block, "fedit_save"):
                    block.block.fedit_save(self.cleaned_data, self.parent_instance)


                if isinstance(block.value, blocks.StructValue):
                    for field_name, value in self.cleaned_data.items():
                        block.value[field_name] = utils.value_for_form(
                            block.value[field_name],
                            block.block.child_blocks[field_name],
                            value
                        )

                else:
                    value = self.cleaned_data["value"]
                    # fieldblock special method - great!
                    block.value = block.block.value_from_form(value)
            else:
                raise ValueError("Invalid block type: %s" % type(block))

        return block

class BlockEditForm(BaseBlockEditForm):
    def __init__(self, *args, parent_instance: models.Model, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_instance = parent_instance

    def save(self):
        block = super().save()
        self.parent_instance.full_clean()

        if isinstance(self.parent_instance, RevisionMixin):
            self.parent_instance = self.parent_instance.save_revision(
                user=self.request.user,
            )
        else:
            self.parent_instance = self.parent_instance.save()
        return block
        