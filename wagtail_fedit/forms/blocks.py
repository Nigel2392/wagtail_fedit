from django import forms
from django.db import models
from wagtail.models import RevisionMixin
from wagtail.blocks.base import (
    BlockField,
    BlockWidget,
    BoundBlock,
)
from wagtail import blocks

import warnings



class BlockWidgetWithErrors(BlockWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_errors = None

    def render(self, name, value, attrs=None, renderer=None):
        if not self.form_errors:
            return super().render(name, value, attrs, renderer)
        
        return self.render_with_errors(name, value, attrs, self.form_errors, renderer)


def get_block_form_class(block: blocks.Block):

    if isinstance(block, blocks.BoundBlock):
        block = block.block

    class BlockForm(BlockEditForm):
        value = BlockField(block=block, widget=BlockWidgetWithErrors(block))

    return BlockForm


class BlockEditForm(forms.Form):
    def __init__(self, *args, block: BoundBlock, parent_instance: models.Model, request = None, **kwargs):
        self.block = block
        self.request = request
        self.parent_instance = parent_instance

        if "initial" not in kwargs:
            kwargs["initial"] = {
                "value": block.value,
            }

        super().__init__(*args, **kwargs)

    def full_clean(self):
        super().full_clean()
        if self.errors:
            self.fields["value"].widget.form_errors = self.errors["value"]

    def save(self):
        block = self.cleaned_data["value"]
        self.block.value.update(block)

        if isinstance(self.parent_instance, RevisionMixin) and self.request:
            self.parent_instance = self.parent_instance.save_revision(
                user=self.request.user,
                log_action=False,
            )
        elif isinstance(self.parent_instance, RevisionMixin) and not self.request:
            warnings.warn((
                "RevisionMixin instance (%(model_type)s) provided without request," 
                "skipping revision creation and saving model instance instead."
            ) % {"model_type": type(self.parent_instance)})
            self.parent_instance.save()
        else:
            self.parent_instance.save()

        return self.block
