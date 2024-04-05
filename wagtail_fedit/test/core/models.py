from django.db import models
from django.http import HttpResponse
from django.utils.text import slugify
from wagtail.snippets.models import register_snippet
from wagtail import blocks
from wagtail.fields import StreamField
from wagtail.models import (
    Page,
    LockableMixin,
    RevisionMixin,
    PreviewableMixin,
    WorkflowMixin,
    DraftStateMixin,
)
from wagtail_fedit.models import (
    FEditableMixin,
    FeditPermissionTester,
    ModelPermissionPolicy,
)

class HeadingComponent(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=25)
    subheading = blocks.CharBlock(max_length=40)

class LinkBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=25)

class MenuItemBlock(blocks.StructBlock):
    link = LinkBlock()

class FlatMenuComponent(blocks.StructBlock):
    title = blocks.CharBlock(max_length=25)
    subtitle = blocks.RichTextBlock()
    items = blocks.ListBlock(
        MenuItemBlock()
    )


class BaseEditableMixin:
    def get_url(self, request):
        return f"/{slugify(self.title)}/"
    
    def serve(self, request, *args, **kwargs):
        return HttpResponse(self.body)
        
@register_snippet
class BasicModel(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)

@register_snippet
class EditableFullModel(BaseEditableMixin, FEditableMixin):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)


@register_snippet
class EditableDraftModel(BaseEditableMixin, DraftStateMixin, RevisionMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)


@register_snippet
class EditableRevisionModel(BaseEditableMixin, RevisionMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)


@register_snippet
class EditablePreviewModel(BaseEditableMixin, PreviewableMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)

@register_snippet
class EditableLockModel(BaseEditableMixin, WorkflowMixin, DraftStateMixin, RevisionMixin, LockableMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)

    
    def get_permissions_policy(self):
        return ModelPermissionPolicy(self.__class__)
    
    def permissions_for_user(self, user):
        return FeditPermissionTester(
            self,
            user=user,
            policy=self.get_permissions_policy()
        )
