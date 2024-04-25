from django.test import TestCase
from django.db import models
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.auth.models import (
    User,
    Permission,
    AnonymousUser,
)
from wagtail.models import (
    Page,
)
from ..models import (
    BasicModel,
    EditablePageModel,
    EditableFullModel,
    EditableDraftModel,
    EditableRevisionModel,
    EditablePreviewModel,
    EditableLockModel,
)

import urllib.parse

from wagtail_fedit.adapters import BaseAdapter

TEST_BLOCK_DATA = [
    {
        "type": "heading_component",
        "value": {
            "heading": "This is pretty cool!!!",
            "subheading": "RIGHT?! FUCK YES!"
        },
        "id": "0bc9f67e-f116-48a6-9ca1-6c11d39b54e8"
    },
    {
        "type": "heading_component",
        "value": {
            "heading": "AWESOME!!",
            "subheading": "RIGHT?!"
        },
        "id": "d543a6bf-34dc-4365-a3fa-d302561930ae"
    },
    {
        "type": "heading_component",
        "value": {
            "heading": "WORKS NOW!",
            "subheading": "!!!!!!!!!!!!1"
        },
        "id": "c49abcae-3c66-4fc7-979d-35407226b9f5"
    },
    {
        "type": "heading_component",
        "value": {
            "heading": "Heading!!!!",
            "subheading": "Subheading"
        },
        "id": "7bd7bc3a-1d2d-4182-8726-b257beace968"
    },
    {
        "type": "heading_component",
        "value": {
            "heading": "Hey!",
            "subheading": "Subheading!"
        },
        "id": "74a94baa-acf4-49ab-be5f-9c8a70cbc623"
    },
    {
        "type": "flat_menu_component",
        "value": {
            "title": "Test Title123123! HAHA!",
            "subtitle": "<p data-block-key=\"306j3\">i am so<b><i> happy</i></b></p>",
            "items": [
                {
                    "type": "item",
                    "value": {
                        "link": {
                            "text": "Test Item 1"
                        }
                    },
                    "id": "c757f54d-0df5-4b35-8a06-4174f180ec41"
                },
                {
                    "type": "item",
                    "value": {
                        "link": {
                            "text": "Test Item 2"
                        }
                    },
                    "id": "ec3d73d1-fd01-49ba-840a-d44586ac0025"
                },
                {
                    "type": "item",
                    "value": {
                        "link": {
                            "text": "Test Item 3"
                        }
                    },
                    "id": "a98a19c6-2ead-4e69-9ea2-3158c7e82976"
                },
                {
                    "type": "item",
                    "value": {
                        "link": {
                            "text": "Test Item 4"
                        }
                    },
                    "id": "db7183a2-d9dd-4fbd-9e42-fd2b9ebf0458"
                }
            ]
        },
        "id": "3e9144fd-5fa5-47f8-917e-8fe87c15da01"
    }
]



class BaseFEditTest(TestCase):
    # Block ID for a sub-block present in test data.
    BLOCK_ID = "c757f54d-0df5-4b35-8a06-4174f180ec41"
    
    def setUp(self):
        super().setUp()

        self.request_factory = RequestFactory()
        root_page: Page = Page.add_root(title="Root Page")
        self.page_model = root_page.add_child(
            instance=EditablePageModel(
                title="Editable Page",
                body="Editable Page Body",
                content=TEST_BLOCK_DATA,
                url_path="/home/editable-page/",
            )
        )
        self.full_model = EditableFullModel.objects.create(
            title="Full Model",
            body="Full Model Body",
            content=TEST_BLOCK_DATA,
        )
        self.draft_model = EditableDraftModel.objects.create(
            title="Draft Model",
            body="Draft Model Body",
            content=TEST_BLOCK_DATA,
        )
        self.revision_model = EditableRevisionModel.objects.create(
            title="Revision Model",
            body="Revision Model Body",
            content=TEST_BLOCK_DATA,
        )
        self.preview_model = EditablePreviewModel.objects.create(
            title="Preview Model",
            body="Preview Model Body",
            content=TEST_BLOCK_DATA,
        )
        self.basic_model = BasicModel.objects.create(
            title="Basic Model",
            body="Basic Model Body",
            content=TEST_BLOCK_DATA,
        )

        # Additional models for other functionality
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@localhost",
            password="admin"
        )
        self.other_admin_user = User.objects.create_superuser(
            username="other_admin",
            email="other_admin@localhost",
            password="other_admin"
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@localhost",
            password="regular"
        )
        self.anonymous_user = AnonymousUser()
        self.regular_user.user_permissions.add(Permission.objects.get(
            codename="access_admin",
            content_type__app_label="wagtailadmin"
        ))

        self.lock_model = EditableLockModel.objects.create(
            title="Lock Model",
            body="Lock Model Body",
            content=TEST_BLOCK_DATA,
            locked=True,
            locked_by=self.admin_user,
            has_unpublished_changes=True,
        )

        self.basic_model.related_field = self.basic_model.__class__.objects.create(
            title="Related Field",
            body="Related Field Body",
            content=TEST_BLOCK_DATA,
        )

        self.basic_model.save()
        
        self.models: list[models.Model] = [
            self.full_model,
            self.draft_model,
            self.revision_model,
            self.preview_model,
            self.basic_model,
        ]

    def get_editable_url(self, object_id, app_label, model_name):
        url_name = "editable"
        return reverse(
            f"wagtail_fedit:{url_name}",
            kwargs={
                "object_id": object_id,
                "app_label": app_label,
                "model_name": model_name
            }
        )

    def get_url_for(self, url_name, app_label, model_name, model_id):
        return reverse(
            f"wagtail_fedit:{url_name}",
            kwargs={
                "object_id": model_id,
                "app_label": app_label,
                "model_name": model_name,
            }
        )
    
    def get_refetch_url(self, adapter_id, app_label, model_name, model_id, field_name = None):
        url_name = "refetch"
        kwgs = {
            "adapter_id": adapter_id,
            "app_label": app_label,
            "model_name": model_name,
            "model_id": model_id,
        }

        if field_name:
            kwgs["field_name"] = field_name

        return reverse(
            f"wagtail_fedit:{url_name}",
            kwargs=kwgs
        )

    def get_field_url(self, field_name, app_label, model_name, model_id):
        url_name = "edit"
        return reverse(
            f"wagtail_fedit:{url_name}",
            kwargs={
                "adapter_id": "field",
                "field_name": field_name,
                "app_label": app_label,
                "model_name": model_name,
                "model_id": model_id
            }
        )
    
    def get_model_url(self, app_label, model_name, model_id):
        url_name = "edit"
        return reverse(
            f"wagtail_fedit:{url_name}",
            kwargs={
                "adapter_id": "model",
                "app_label": app_label,
                "model_name": model_name,
                "model_id": model_id
            }
        )


    def get_block_url(self, block_id, field_name, app_label, model_name, model_id):
        url_name = "edit"
        url = reverse(
            f"wagtail_fedit:{url_name}",
            kwargs={
                "adapter_id": "block",
                "field_name": field_name,
                "app_label": app_label,
                "model_name": model_name,
                "model_id": model_id
            }
        )
        adapter = BaseAdapter(
            BasicModel(), "title", None, block_id=block_id,
        )
        encoded = adapter.encode_shared_context()
        encoded = urllib.parse.urlencode({"shared_context": encoded})
        return f"{url}?{encoded}"


