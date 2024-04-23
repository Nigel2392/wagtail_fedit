from django.db import models
from django.http import HttpResponse
from django.utils.text import slugify
from wagtail.snippets.models import register_snippet
from django.template import Template, Context
from wagtail import blocks
from wagtail.admin.panels import (
    FieldPanel,
)
from wagtail.fields import (
    StreamField,
    StreamValue,
)
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

    def render(self, value, context=None):
        template = Template("""
            <h1>{{ heading }}</h1>
            <h2>{{ subheading }}</h2>
        """)

        context = self.get_context(value, parent_context=context)
        return template.render(Context(context))

class LinkBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=25)

    def render(self, value, context=None):
        template = Template("""
            <a href="#">{{ text }}</a>
        """)

        context = self.get_context(value, parent_context=context)
        return template.render(Context(context))

class MenuItemBlock(blocks.StructBlock):
    link = LinkBlock()

    def render(self, value, context=None):
        template = Template("""
            {% load wagtailcore_tags %}
            <li>{% include_block self.link %}</li>
        """)

        context = self.get_context(value, parent_context=context)
        return template.render(Context(context))

class FlatMenuComponent(blocks.StructBlock):
    title = blocks.CharBlock(max_length=25)
    subtitle = blocks.RichTextBlock()
    items = blocks.ListBlock(
        MenuItemBlock()
    )

    def render(self, value, context=None):
        template = Template("""
            {% load wagtailcore_tags %}
            <h1>{{ title }}</h1>
            <p>{{ subtitle }}</p>
            <ul>
                {% for item in items %}
                    {% include_block item %}
                {% endfor %}
            </ul>
        """)

        context = self.get_context(value, parent_context=context)
        return template.render(Context(context))


class BaseEditableMixin:
    def get_url(self, request):
        return f"/{slugify(self.title)}/"
    
    def serve(self, request, *args, **kwargs):
        return HttpResponse(self.body)

    def render_as_content(self, request, context=None):
        return f"<h1>{self.title}</h1><p>{self.body}</p>"

@register_snippet
class BasicModel(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content: StreamValue = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)
    related_field = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("body"),
    ]

    def render_as_content(self, request, context=None):
        return f"<h1>{self.title}</h1><p>{self.body}</p>"


@register_snippet
class EditableFullModel(BaseEditableMixin, FEditableMixin):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content: StreamValue = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)


@register_snippet
class EditableDraftModel(BaseEditableMixin, DraftStateMixin, RevisionMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content: StreamValue = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)


@register_snippet
class EditableRevisionModel(BaseEditableMixin, RevisionMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content: StreamValue = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)


@register_snippet
class EditablePreviewModel(BaseEditableMixin, PreviewableMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content: StreamValue = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)

@register_snippet
class EditableLockModel(BaseEditableMixin, WorkflowMixin, DraftStateMixin, RevisionMixin, LockableMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    content: StreamValue = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("body"),
    ]
    
    def get_permissions_policy(self):
        return ModelPermissionPolicy(self.__class__)
    
    def permissions_for_user(self, user):
        return FeditPermissionTester(
            self,
            user=user,
            policy=self.get_permissions_policy()
        )


class EditablePageModel(Page):
    body = models.TextField()
    content: StreamValue = StreamField([
        ("heading_component", HeadingComponent()),
        ("flat_menu_component", FlatMenuComponent())
    ], use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel("body")
    ]

    promote_panels = []
    settings_panels = []

    def render_as_content(self, request, context=None):
        return f"<h1>{self.title}</h1><p>{self.body}</p>"