from django.db import models
from wagtail import hooks
from wagtail_fedit.templatetags import (
    fedit as templatetags,
)
from wagtail_fedit import (
    utils,
    hooks as fedit_hooks,
)
from .base import (
    BaseFEditTest,
)


class TestFieldTemplateTag(BaseFEditTest):

    def setUp(self):
        super().setUp()

        # # This might make tests fail runnning in parallel.
        # @hooks.register(fedit_hooks.REGISTER_FIELD_RENDERER)
        # def register_type_renderer(mapping):
        #     mapping[models.TextField] =\
        #         lambda request, context, instance, value: f"<p class=\"text-field\">{value}</p>"

        # This is ok.
        utils._field_renderer_map[models.TextField] =\
            lambda request, context, instance, value: f"<p class=\"text-field\">{value}</p>"

    def test_render_regular_no_custom_type_renderer(self):

        # Setup user attribute for request.
        request = self.request_factory.get("/")
        request.user = self.admin_user

        context = {
            "request": request,
            "model": self.basic_model,
            "field_name": "title",
        }

        title_node = templatetags.FieldEditNode(
            model=self.basic_model,
            getters=["title"],
        )

        self.assertHTMLEqual(
            title_node.render(context),
            self.basic_model.title
        )

    def test_render_editable_no_custom_type_renderer(self):
        # Setup user attribute for request.
        request = self.request_factory.get("/")
        request.user = self.admin_user

        context = {
            "request": request,
            "model": self.basic_model,
            "field_name": "title",
        }

        # Mark as editable.
        setattr(
            request,
            utils.FEDIT_PREVIEW_VAR,
            True,
        )

        title_node = templatetags.FieldEditNode(
            model=self.basic_model,
            getters=["title"],
        )

        rendered_title = templatetags.render_editable_field(
            request,
            self.basic_model.title,
            "title",
            self.basic_model,
            context,
        )

        self.assertHTMLEqual(
            title_node.render(context),
            rendered_title
        )

    def test_render_regular_custom_type_renderer(self):
        # Setup user attribute for request.
        request = self.request_factory.get("/")
        request.user = self.admin_user

        context = {
            "request": request,
            "model": self.basic_model,
            "field_name": "title",
        }

        body_node = templatetags.FieldEditNode(
            model=self.basic_model,
            getters=["body"],
        )

        self.assertHTMLEqual(
            body_node.render(context),
            f"<p class=\"text-field\">{self.basic_model.body}</p>"
        )

    def test_render_editable_custom_type_renderer(self):
        # Setup user attribute for request.
        request = self.request_factory.get("/")
        request.user = self.admin_user

        context = {
            "request": request,
            "model": self.basic_model,
            "field_name": "title",
        }

        # Mark as editable.
        setattr(
            request,
            utils.FEDIT_PREVIEW_VAR,
            True,
        )

        body_node = templatetags.FieldEditNode(
            model=self.basic_model,
            getters=["body"],
            inline=True,
        )

        rendered_body = templatetags.render_editable_field(
            request,
            f"<p class=\"text-field\">{self.basic_model.body}</p>",
            "body",
            self.basic_model,
            context,
            inline=True,
        )

        self.assertHTMLEqual(
            body_node.render(context),
            rendered_body
        )


