from django.db.models.base import Model as Model
from django.http import HttpRequest
from django.template import (
    Context, Template,
    TemplateSyntaxError,
)
from wagtail_fedit.adapters import (
    BaseAdapter,
    adapter_registry,
    BlockAdapter,
    FieldAdapter,
)
from wagtail_fedit.utils import (
    FEDIT_PREVIEW_VAR,
    find_block,
)
from wagtail_fedit.templatetags.fedit import (
    wrap_adapter,
)
from .base import (
    BaseFEditTest,
)

import json

adapters = {}

class TestAdapter(BaseAdapter):
    identifier = "test"
    required_kwargs = ["test"]

    def __init__(self, object: Model, field_name: str, request: HttpRequest, **kwargs):
        super().__init__(object, field_name, request, **kwargs)
        adapters[self.kwargs["id"]] = self

    def get_element_id(self) -> str:
        return f"test-{self.kwargs['id']}"

    def render_content(self, parent_context: dict = None) -> str:
        return f"TestAdapter: {self.field_value}"


class TestBlockAdapter(BlockAdapter, TestAdapter):
    identifier = "test_block"

class TestFieldAdapter(FieldAdapter, TestAdapter):
    identifier = "test_field"

class TestContextAdapter(TestAdapter):
    identifier = "test_context"

    def render_content(self, parent_context: dict = None) -> str:
        return parent_context["testing"]

adapter_registry.register(TestAdapter)
adapter_registry.register(TestBlockAdapter)
adapter_registry.register(TestFieldAdapter)
adapter_registry.register(TestContextAdapter)


class TestBaseAdapter(BaseFEditTest):

    def test_required_kwargs_ok(self):
        self.assertEqual(TestAdapter.required_kwargs, ["test"])

        template_ok = Template(
            "{% load fedit %}"
            "{% fedit test object.title test='test' id=1 %}"
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        template_ok = template_ok.render(
            Context({
                "request": request,
                "object": self.basic_model,
            })
        )

        self.assertHTMLEqual(
            template_ok,
            f'TestAdapter: {self.basic_model.title}'
        )

        self.assertDictEqual(
            adapters[1].kwargs,
            {"test": "test", "id": 1}
        )

    def test_required_kwargs_fail(self):
        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        try:
            template_fail = Template(
                "{% load fedit %}"
                "{% fedit test object.title id=2 %}"
            )

            # self.fail(f"Expected exception: {e}")
            template_fail.render(Context({
                "request": request,
                "object": self.basic_model,
            }))

        except TemplateSyntaxError as e:
            self.assertEqual(
                str(e),
                "Missing required keyword argument test"
            )

        except Exception as e:
            self.fail(f"Unexpected exception: {e} ({type(e)})")

        else:
            self.fail("Expected exception not raised")

    def test_adapter_render_content(self):
        adapter = TestAdapter(
            self.basic_model,
            "title",
            self.request_factory.get(
                self.get_editable_url(
                    self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
                )
            ),
            id=3,
        )

        self.assertEqual(
            adapter.render_content(),
            f"TestAdapter: {self.basic_model.title}"
        )

    def test_adapter_editable(self):
        self.assertEqual(TestAdapter.required_kwargs, ["test"])

        tpl = Template(
            "{% load fedit %}"
            "{% fedit test object.title test='test' id=4 %}"
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        setattr(
            request,
            FEDIT_PREVIEW_VAR,
            True,
        )

        tpl = tpl.render(
            Context({
                "request": request,
                "object": self.basic_model,
            })
        )

        self.assertHTMLEqual(
            tpl,
            wrap_adapter(request, adapters[4], {})
        )

    def test_context_processors_run(self):
        tpl = Template(
            "{% load fedit %}"
            "{% fedit test_context object.title test='test' id=5 %}"
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        setattr(
            request,
            FEDIT_PREVIEW_VAR,
            True,
        )

        # In this test we are testing the adapter - not the template.
        tpl = tpl.render(
            Context({
                "request": request,
                "object": self.basic_model,
                "testing": "testing context processor",
            }),
        )

        self.assertHTMLEqual(
            tpl,
            wrap_adapter(request, adapters[5], {}, run_context_processors=True)
        )


class TestBlockAdapter(BaseFEditTest):

    def test_render(self):
        streamfield = self.basic_model.content
        block = find_block(self.BLOCK_ID, streamfield)
        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user
        setattr(
            request,
            FEDIT_PREVIEW_VAR,
            True,
        )
        block_value, _ = block
        template = Template(
            "{% load fedit %}"
            "{% fedit test_block object.content block=block block_id=block_id id=5 %}"
        )

        context = {
            "object": self.basic_model,
            "request": request,
            "block": block_value,
            "block_id": self.BLOCK_ID,
        }

        tpl = template.render(Context(context))

        self.assertHTMLEqual(
            tpl,
            wrap_adapter(request, adapters[5], {})
        )

    def test_render_from_context(self):
        streamfield = self.basic_model.content
        block = find_block(self.BLOCK_ID, streamfield)
        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user
        setattr(
            request,
            FEDIT_PREVIEW_VAR,
            True,
        )
        block_value, _ = block
        template = Template(
            "{% load fedit %}"
            "{% fedit test_block from_context block=block block_id=block_id id=6 %}"
        )

        context = {
            "object": self.basic_model,
            "request": request,
            "block": block_value,
            "block_id": self.BLOCK_ID,
            "wagtail_fedit_field": "content",
            "wagtail_fedit_instance": self.basic_model,
        }

        tpl = template.render(Context(context))

        self.assertHTMLEqual(
            tpl,
            wrap_adapter(request, adapters[6], context)
        )


    def test_render_from_context_missing(self):
        streamfield = self.basic_model.content
        block = find_block(self.BLOCK_ID, streamfield)
        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user
        block_value, _ = block
        template = Template(
            "{% load fedit %}"
            "{% fedit test_block from_context block=block block_id=block_id id=6 %}"
        )

        context = {
            "object": self.basic_model,
            "request": request,
            "block": block_value,
            "block_id": self.BLOCK_ID,
        }

        tpl = template.render(Context(context))

        self.assertHTMLEqual(
            tpl,
            block_value.render(context),
        )


class TestFieldAdapter(BaseFEditTest):
    
        def test_render(self):
            request = self.request_factory.get(
                self.get_editable_url(
                    self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
                )
            )
            request.user = self.admin_user
            setattr(
                request,
                FEDIT_PREVIEW_VAR,
                True,
            )
            template = Template(
                "{% load fedit %}"
                "{% fedit test_field object.title test=True id=7 %}"
            )
    
            context = {
                "object": self.basic_model,
                "request": request,
            }
    
            tpl = template.render(Context(context))
    
            self.assertHTMLEqual(
                tpl,
                wrap_adapter(request, adapters[7], {})
            )
    