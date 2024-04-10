from django.db import models
from wagtail import hooks

import copy

from wagtail_fedit import (
    hooks as fedit_hooks,
    utils,
)

from .base import BaseFEditTest


class TestUtils(BaseFEditTest):
    def setUp(self):
        super().setUp()
        # Wrap output from textfield in paragraph.
        utils._field_renderer_map[models.TextField] =\
            lambda request, context, instance, value:\
                f"<p class=\"text-field\">{value}</p>"
        
        @hooks.register(fedit_hooks.EXCLUDE_FROM_RELATED_FORMS)
        def exclude_related_forms(field: models.Field):
            return field.related_model == self.full_model.__class__

    def test_get_field_content(self):
        request = self.request_factory.get("/")
        self.assertEqual(
            utils.get_field_content(request, self.basic_model, "title", {}),
            self.basic_model.title
        )
        self.assertEqual(
            utils.get_field_content(request, self.basic_model, "body", {}),
            f"<p class=\"text-field\">{self.basic_model.body}</p>"
        )

    def test_permission_check(self):
        self.assertTrue(
            utils.FeditPermissionCheck.has_perms(self.admin_user, self.basic_model)
        )
        self.assertFalse(
            utils.FeditPermissionCheck.has_perms(self.regular_user, self.basic_model)
        )
        self.assertFalse(
            utils.FeditPermissionCheck.has_perms(self.anonymous_user, self.basic_model)
        )

    def test_use_related_form(self):

        basic_field = models.ForeignKey(
            self.basic_model.__class__,
            on_delete=models.CASCADE,
        )

        full_field = models.ForeignKey(
            self.full_model.__class__,
            on_delete=models.CASCADE,
        )

        self.assertTrue(
            utils.use_related_form(basic_field)
        )
        self.assertFalse(
            utils.use_related_form(full_field)
        )

    def test_get_set_userbar_model(self):
        request = self.request_factory.get("/")

        self.assertIsNone(
            utils.access_userbar_model(request)
        )

        utils.with_userbar_model(request, self.basic_model)
        
        self.assertEqual(
            utils.access_userbar_model(request),
            self.basic_model
        )

    def test_is_draft_capable(self):
        self.assertTrue(utils.is_draft_capable(self.draft_model))
        self.assertFalse(utils.is_draft_capable(self.basic_model))

    def test_model_type_difference(self):
        self.assertTrue(
            utils.model_diff(self.full_model, self.basic_model)
        )
        self.assertFalse(
            utils.model_diff(self.full_model, self.full_model)
        )

        other_full_model = copy.deepcopy(self.full_model)
        other_full_model.title = "Other Title"

        self.assertFalse(
            utils.model_diff(self.full_model, other_full_model)
        )
