from django.test import TestCase
from wagtail import blocks
from wagtail_fedit import forms as block_forms
from wagtail_fedit import utils
import copy
from .base import TEST_BLOCK_DATA
from ..models import (
    HeadingComponent,
    FlatMenuComponent
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
        self.stream_value = self.stream_block.to_python(copy.deepcopy(TEST_BLOCK_DATA))

    def test_find_block(self):
        block, contentpath, parent, idx = utils.find_block("d543a6bf-34dc-4365-a3fa-d302561930ae", self.stream_value)
        self.assertEqual(block.value["heading"], "AWESOME!!")
        self.assertEqual(block.value["subheading"], "RIGHT?!")

        block, contentpath, parent, idx = utils.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)
        self.assertEqual(block.value["link"]["text"], "Test Item 3")
        self.assertEqual(contentpath, ["3e9144fd-5fa5-47f8-917e-8fe87c15da01", "items", "a98a19c6-2ead-4e69-9ea2-3158c7e82976"])

        item = self.stream_block.get_block_by_content_path(self.stream_value, contentpath)
        self.assertEqual(item.value["link"]["text"], "Test Item 3")

        block, contentpath, parent, idx = utils.find_block("invalid-id", self.stream_value)
        self.assertIsNone(block)
        self.assertEqual(contentpath, [])

    def test_find_block_parent(self):
        block, contentpath, parent, idx = utils.find_block("d543a6bf-34dc-4365-a3fa-d302561930ae", self.stream_value)
        self.assertEqual(parent, self.stream_value)

        block, contentpath, parent, idx = utils.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)
        self.assertEqual(idx, 2)
        self.assertEqual(parent.bound_blocks[idx].value["link"]["text"], "Test Item 3")
    
    def test_move_block_down(self):
        block, contentpath, parent, idx = utils.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)
        self.assertEqual(idx, 2)
        self.assertEqual(parent.bound_blocks[idx].value["link"]["text"], "Test Item 3")

        if idx < len(parent) - 1:
            parent[idx], parent[idx + 1] = parent[idx + 1], parent[idx]
        else:
            self.fail("Block is already at the bottom")

        self.assertEqual(parent.bound_blocks[idx].value["link"]["text"], "Test Item 4")
        self.assertEqual(parent.bound_blocks[idx + 1].value["link"]["text"], "Test Item 3")

    def test_move_block_up(self):
        block, contentpath, parent, idx = utils.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)
        self.assertEqual(idx, 2)
        self.assertEqual(parent.bound_blocks[idx].value["link"]["text"], "Test Item 3")

        if idx > 0:
            parent[idx], parent[idx - 1] = parent[idx - 1], parent[idx]
        else:
            self.fail("Block is already at the top")

        self.assertEqual(parent.bound_blocks[idx].value["link"]["text"], "Test Item 2")
        self.assertEqual(parent.bound_blocks[idx - 1].value["link"]["text"], "Test Item 3")

    def test_get_form_class(self):
        block = utils.find_block("d543a6bf-34dc-4365-a3fa-d302561930ae", self.stream_value)[0]
        form_class = block_forms.get_block_form_class(block.block)
        self.assertIsNotNone(form_class)

        VALID_DATA = {
            "value-heading": "New Heading",
            "value-subheading": "New Subheading"
        }

        INVALID_DATA = {
            "value-heading": "New Heading",
            "value-subheading": "New Subheading" * 10
        }

        valid_form = form_class(data=VALID_DATA, block=block, parent_instance=FakeModel())
        self.assertTrue(valid_form.is_valid())

        invalid_form = form_class(data=INVALID_DATA, block=block, parent_instance=FakeModel())
        self.assertFalse(invalid_form.is_valid())

    def test_get_subblock_form_class(self):
        block = utils.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)[0]
        form_class = block_forms.get_block_form_class(block.block)
        self.assertIsNotNone(form_class)

        VALID_DATA = {
            "value-link-text": "New Link Text"
        }

        INVALID_DATA = {
            "value-link-text": ["New Link Text" * 10]
        }


        valid_form = form_class(data=VALID_DATA, block=block, parent_instance=FakeModel())
        if not valid_form.is_valid():
            self.fail((
                valid_form.errors.items(),
                valid_form.non_field_errors()
            ))

        valid_form.save()
        self.assertEqual(block.value["link"]["text"], "New Link Text")

        invalid_form = form_class(data=INVALID_DATA, block=block, parent_instance=FakeModel())
        self.assertFalse(invalid_form.is_valid())


    def test_block_form_save(self):
        block = utils.find_block("d543a6bf-34dc-4365-a3fa-d302561930ae", self.stream_value)[0]
        form_class = block_forms.get_block_form_class(block.block)

        VALID_DATA = {
            "value-heading": "New Heading",
            "value-subheading": "New Subheading"
        }

        valid_form = form_class(data=VALID_DATA, block=block, parent_instance=FakeModel())
        if not valid_form.is_valid():
            self.fail((valid_form.errors.items(), valid_form.non_field_errors()))

        valid_form.save()
        self.assertEqual(block.value["heading"], "New Heading")
        self.assertEqual(block.value["subheading"], "New Subheading")


    def test_subblock_form_save(self):
        block = utils.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.stream_value)[0]
        form_class = block_forms.get_block_form_class(block.block)

        VALID_DATA = {
            "value-link-text": "New Link Text"
        }

        valid_form = form_class(data=VALID_DATA, block=block, parent_instance=FakeModel())
        if not valid_form.is_valid():
            errors = valid_form.errors.as_data()["value"][0].as_json_data()
            self.fail((errors, valid_form.non_field_errors()))

        valid_form.save()
        self.assertEqual(block.value["link"]["text"], "New Link Text")
