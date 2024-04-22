from django.db.models.base import Model as Model
from django.http import HttpRequest
from django.template import (
    Context, Template,
    TemplateSyntaxError,
)
from wagtail_fedit.adapters import (
    Keyword,
    BaseAdapter,
    adapter_registry,
    BlockAdapter,
    FieldAdapter,
    ModelAdapter,
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

adapters = {}

class TestAdapter(BaseAdapter):
    identifier = "test"
    keywords = (
        Keyword("test", help_text="A test keyword argument", type_hint="str"),
    )
    js_constructor = "wagtail_fedit.ThisDoesntGetUsedAnyways"

    def __init__(self, object: Model, field_name: str, request: HttpRequest, **kwargs):
        super().__init__(object, field_name, request, **kwargs)
        adapters[self.kwargs["id"]] = self

    def get_element_id(self) -> str:
        return f"test-{self.kwargs['id']}"

    def render_content(self, parent_context: dict = None) -> str:
        return f"TestAdapter: {self.field_value}"

class TestContextAdapter(TestAdapter):
    identifier = "test_context"

    def render_content(self, parent_context: dict = None) -> str:
        return parent_context["testing"]

class TestAbsoluteTokensAdapter(TestAdapter):
    identifier = "test_absolute_tokens"

    keywords = TestAdapter.keywords + (
        Keyword("optional", optional=True, help_text="A test keyword argument", type_hint="str", default="default"),
        Keyword("absolute", absolute=True, help_text="A test keyword argument", type_hint="bool"),
    )

    def render_content(self, parent_context: dict = None) -> str:
        return str(self.kwargs.get("absolute", False))

class TestBlockAdapter(BlockAdapter, TestAdapter):
    identifier = "test_block"

class TestFieldAdapter(FieldAdapter, TestAdapter):
    identifier = "test_field"

class TestModelAdapter(ModelAdapter, TestAdapter):
    identifier = "test_model"

adapter_registry.register(TestAdapter)
adapter_registry.register(TestBlockAdapter)
adapter_registry.register(TestFieldAdapter)
adapter_registry.register(TestModelAdapter)
adapter_registry.register(TestContextAdapter)
adapter_registry.register(TestAbsoluteTokensAdapter)

import uuid

def get_adapter_id() -> str:
    return str(uuid.uuid4())

class TestBaseAdapter(BaseFEditTest):

    def test_required_kwargs(self):
        self.assertEqual(TestAdapter.required_kwargs, set(["test"]))

    def test_absolute_tokens(self):
        self.assertEqual(TestAbsoluteTokensAdapter.absolute_tokens, set(["absolute"]))

    def test_required_kwargs_ok(self):
        self.assertEqual(TestAdapter.required_kwargs, set(["test"]))
        id = get_adapter_id()

        template_ok = Template(
            "{% load fedit %}"
            f"{{% fedit test object.title test='test' id='{id}' %}}"
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
            adapters[id].kwargs,
            {"test": "test", "id": id}
        )

    def test_required_kwargs_fail(self):
        id = get_adapter_id()
        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        try:
            template_fail = Template(
                "{% load fedit %}"
                f"{{% fedit test object.title id='{id}' %}}"
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

    def test_optional_kwargs_default(self):
        id = get_adapter_id()
        template = Template(
            "{% load fedit %}"
            f"{{% fedit test_absolute_tokens object.title test='test' id='{id}' %}}"
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        template = template.render(
            Context({
                "request": request,
                "object": self.basic_model,
            })
        )

        adapter = adapters[id]

        self.assertEqual(
            adapter.kwargs["optional"],
            "default",
        )

    def test_optional_kwargs_override(self):
        id = get_adapter_id()
        template = Template(
            "{% load fedit %}"
            f"{{% fedit test_absolute_tokens object.title optional='not default' test='test' id='{id}' %}}"
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        template = template.render(
            Context({
                "request": request,
                "object": self.basic_model,
            })
        )

        adapter = adapters[id]

        self.assertEqual(
            adapter.kwargs["optional"],
            "not default",
        )

    def test_adapter_absolute_tokens(self):
        id = get_adapter_id()
        tpl = Template(
            "{% load fedit %}"
            f"{{% fedit test_absolute_tokens object.title test='test' absolute id='{id}' %}}"
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        tpl = tpl.render(
            Context({
                "request": request,
                "object": self.basic_model,
            })
        )

        self.assertHTMLEqual(
            tpl,
            str(True),
        )

    def test_adapter_absolute_tokens_fail(self):
        id = get_adapter_id()
        tpl = Template(
            "{% load fedit %}"
            f"{{% fedit test_absolute_tokens object.title test='test' id='{id}' %}}"
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        request.user = self.admin_user

        tpl = tpl.render(
            Context({
                "request": request,
                "object": self.basic_model,
            })
        )

        self.assertHTMLEqual(
            tpl,
            str(False),
        )

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
        id = get_adapter_id()
        self.assertEqual(TestAdapter.required_kwargs, set(["test"]))

        tpl = Template(
            "{% load fedit %}"
            f"{{% fedit test object.title test='test' id='{id}' %}}"
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
            wrap_adapter(request, adapters[id], {})
        )

    def test_adapter_editable_as_var(self):
        id = get_adapter_id()
        self.assertEqual(TestAdapter.required_kwargs, set(["test"]))

        tpl = Template(
            "{% load fedit %}"
            f"{{% fedit test object.title test='test' id='{id}' as test_adapter_as_variable_name %}}"
            "{{ test_adapter_as_variable_name }}"
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
            wrap_adapter(request, adapters[id], {})
        )

    def test_context_processors_run(self):
        id = get_adapter_id()
        tpl = Template(
            "{% load fedit %}"
            f"{{% fedit test_context object.title test='test' id='{id}' %}}"
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
            wrap_adapter(request, adapters[id], {}, run_context_processors=True)
        )


class TestBlockAdapter(BaseFEditTest):

    def test_render(self):
        id = get_adapter_id()
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
            f"{{% fedit test_block object.content block=block block_id=block_id id='{id}' %}}"
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
            wrap_adapter(request, adapters[id], {})
        )

    def test_render_as_var(self):
        id = get_adapter_id()
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
            f"{{% fedit test_block object.content block=block block_id=block_id id='{id}' as test %}}"
            "{{ test }}"
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
            wrap_adapter(request, adapters[id], {})
        )

    def test_render_from_context(self):
        id = get_adapter_id()
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
            f"{{% fedit test_block from_context block=block block_id=block_id id='{id}' %}}"
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
            wrap_adapter(request, adapters[id], context)
        )


    def test_render_from_context_missing(self):
        id = get_adapter_id()
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
            f"{{% fedit test_block from_context block=block block_id=block_id id='{id}' %}}"
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
            id = get_adapter_id()
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
                f"{{% fedit test_field object.title test=True id='{id}' %}}"
            )
    
            context = {
                "object": self.basic_model,
                "request": request,
            }
    
            tpl = template.render(Context(context))
    
            self.assertHTMLEqual(
                tpl,
                wrap_adapter(request, adapters[id], {})
            )

        def test_render_as_var(self):
            id = get_adapter_id()
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
                f"{{% fedit test_field object.title test=True id='{id}' as test %}}"
                "{{ test }}"
            )
    
            context = {
                "object": self.basic_model,
                "request": request,
            }
    
            tpl = template.render(Context(context))
    
            self.assertHTMLEqual(
                tpl,
                wrap_adapter(request, adapters[id], {})
            )

        def test_render_related_field(self):
            id = get_adapter_id()
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
                f"{{% fedit test_field object.related_field test=True id='{id}' as test %}}"
                "{{ test }}"
            )

            context = {
                "object": self.basic_model,
                "request": request,
            }
    
            tpl = template.render(Context(context))
    
            self.assertHTMLEqual(
                tpl,
                wrap_adapter(request, adapters[id], {})
            )

class TestModelAdapter(BaseFEditTest):
    
        def test_render(self):
            id = get_adapter_id()
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
                f"{{% fedit test_model object test=True id='{id}' %}}"
            )
    
            context = {
                "object": self.basic_model,
                "request": request,
            }
    
            tpl = template.render(Context(context))
    
            self.assertHTMLEqual(
                tpl,
                wrap_adapter(request, adapters[id], {})
            )
    
        def test_render_as_var(self):
            id = get_adapter_id()
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
                f"{{% fedit test_model object test=True id='{id}' as test %}}"
                "{{ test }}"
            )
    
            context = {
                "object": self.basic_model,
                "request": request,
            }
    
            tpl = template.render(Context(context))
    
            self.assertHTMLEqual(
                tpl,
                wrap_adapter(request, adapters[id], {})
            )
    
        def test_render_from_context(self):
            id = get_adapter_id()
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
                f"{{% fedit test_model from_context test=True id='{id}' %}}"
            )
    
            context = {
                "object": self.basic_model,
                "request": request,
                "wagtail_fedit_instance": self.basic_model,
            }
    
            tpl = template.render(Context(context))
    
            self.assertHTMLEqual(
                tpl,
                wrap_adapter(request, adapters[id], context)
            )
