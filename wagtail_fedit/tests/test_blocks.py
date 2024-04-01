from django.test import TestCase
from django import forms
from wagtail import blocks
from .. import block_forms

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

import uuid

_model_map = {}

class FakeModel(object):
    def __init__(self, title="Fake Model"):
        self.pk = uuid.uuid4()
        self.title = title
        self.attrs = {}

    def __setattr__(self, key, value):
        if key in ["pk", "title", "attrs"]:
            object.__setattr__(self, key, value)
        else:
            self.attrs[key] = value

    def __getattribute__(self, key):
        if key in ["pk", "title", "attrs", "full_clean", "save"]:
            return object.__getattribute__(self, key)
        return self.attrs.get(key)
    
    def full_clean(self):
        pass

    def save(self):
        _model_map[self.pk] = self

class FakeUser:
    def __init__(self, is_authenticated=True, is_staff=True):
        self.is_authenticated = is_authenticated
        self.is_staff = is_staff

class FakeRequest:
    def __init__(self, method="GET", user=None, GET=None, POST=None):
        self.user = user or FakeUser()
        self.method = method
        self.GET = GET
        self.POST = POST

class TestBlocks(TestCase):
    def setUp(self) -> None:
        self.stream_block = blocks.StreamBlock([
            ("heading_component", HeadingComponent()),
            ("flat_menu_component", FlatMenuComponent())
        ])
        self.stream_value = self.stream_block.to_python(TEST_BLOCK_DATA)

    def test_find_block(self):
        block, contentpath = block_forms.find_block("d543a6bf-34dc-4365-a3fa-d302561930ae", self.stream_value)
        self.assertEqual(block.value["heading"], "AWESOME!!")
        self.assertEqual(block.value["subheading"], "RIGHT?!")

        block, contentpath = block_forms.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)
        self.assertEqual(block.value["link"]["text"], "Test Item 3")
        self.assertEqual(contentpath, ["3e9144fd-5fa5-47f8-917e-8fe87c15da01", "items", "a98a19c6-2ead-4e69-9ea2-3158c7e82976"])

        item = self.stream_block.get_block_by_content_path(self.stream_value, contentpath)
        self.assertEqual(item.value["link"]["text"], "Test Item 3")

        block, contentpath = block_forms.find_block("invalid-id", self.stream_value)
        self.assertIsNone(block)
        self.assertEqual(contentpath, [])

    def test_get_form_class(self):
        block = block_forms.find_block("d543a6bf-34dc-4365-a3fa-d302561930ae", self.stream_value)[0]
        form_class = block_forms.get_form_class(block, block.block, request=FakeRequest())
        self.assertIsNotNone(form_class)

        fields = {
            "heading": forms.CharField(max_length=25),
            "subheading": forms.CharField(max_length=40)
        }

        for name, field in form_class.base_fields.items():
            self.assertIsInstance(field, fields[name].__class__)

        VALID_DATA = {
            "heading": "New Heading",
            "subheading": "New Subheading"
        }

        INVALID_DATA = {
            "heading": "New Heading",
            "subheading": "New Subheading" * 10
        }

        valid_form = form_class(data=VALID_DATA, block=block, parent_instance=FakeModel(), request=FakeRequest(method="POST", POST=VALID_DATA))
        self.assertTrue(valid_form.is_valid())

        invalid_form = form_class(data=INVALID_DATA, block=block, parent_instance=FakeModel(), request=FakeRequest(method="POST", POST=INVALID_DATA))
        self.assertFalse(invalid_form.is_valid())

    def test_get_subblock_form_class(self):
        block = block_forms.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)[0]
        form_class = block_forms.get_form_class(block, block.block, request=FakeRequest())
        self.assertIsNotNone(form_class)

        fields = {
            "link": block_forms.BlockEditSubFormField
        }

        subfields = {
            "text": forms.CharField(max_length=25)
        }

        for name, field in form_class.base_fields.items():
            self.assertIsInstance(field, fields[name])

        field = form_class.declared_fields["link"]
        self.assertIsInstance(field, block_forms.BlockEditSubFormField)
        self.assertIsInstance(field.form, block_forms.BaseBlockEditForm)

        for name, field in field.form.base_fields.items():
            self.assertIsInstance(field, subfields[name].__class__)

        VALID_DATA = {
            "link-text": "New Link Text"
        }

        INVALID_DATA = {
            "link-text": ["New Link Text" * 10]
        }


        valid_form = form_class(data=VALID_DATA, block=block, parent_instance=FakeModel(), request=FakeRequest(method="POST"))
        if not valid_form.is_valid():
            self.fail((
                valid_form.errors.items(),
                valid_form.non_field_errors()
            ))

        valid_form.save()
        self.assertEqual(block.value["link"]["text"], "New Link Text")

        invalid_form = form_class(data=INVALID_DATA, block=block, parent_instance=FakeModel(), request=FakeRequest(method="POST"))
        self.assertFalse(invalid_form.is_valid())


    def test_block_form_save(self):
        block = block_forms.find_block("d543a6bf-34dc-4365-a3fa-d302561930ae", self.stream_value)[0]
        form_class = block_forms.get_form_class(block, block.block, request=FakeRequest())

        VALID_DATA = {
            "heading": "New Heading",
            "subheading": "New Subheading"
        }

        valid_form = form_class(data=VALID_DATA, block=block, parent_instance=FakeModel(), request=FakeRequest(method="POST"))
        if not valid_form.is_valid():
            self.fail((valid_form.errors.items(), valid_form.non_field_errors()))

        valid_form.save()
        self.assertEqual(block.value["heading"], "New Heading")
        self.assertEqual(block.value["subheading"], "New Subheading")


    def test_subblock_form_save(self):
        block = block_forms.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)[0]
        form_class = block_forms.get_form_class(block, block.block, request=FakeRequest())

        VALID_DATA = {
            "link-text": "New Link Text"
        }

        valid_form = form_class(data=VALID_DATA, block=block, parent_instance=FakeModel(), request=FakeRequest(method="POST"))
        if not valid_form.is_valid():
            self.fail((
                valid_form.errors.items(),
                valid_form.non_field_errors()
            ))

        valid_form.save()
        self.assertEqual(block.value["link"]["text"], "New Link Text")
