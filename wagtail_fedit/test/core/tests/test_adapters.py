from django.db.models.base import Model as Model
from django.http import HttpRequest
from django.urls import reverse
from django.template import (
    Context, Template,
    TemplateSyntaxError,
)
from wagtail_fedit.adapters import (
    Keyword,
    BaseAdapter,
    BlockAdapter,
    FieldAdapter,
    ModelAdapter,
)
from wagtail_fedit.registry import (
    registry as adapter_registry,
)
from wagtail_fedit.adapters.base import (
    BlockFieldReplacementAdapter,
)
from wagtail_fedit.utils import (
    FEDIT_PREVIEW_VAR,
    FIELD_TEMPLATE_VAR,
    INSTANCE_TEMPLATE_VAR,
    base_adapter_context,
    shared_context_url,
    get_reverse_kwargs,
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

class TestAdapter(BlockFieldReplacementAdapter):
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
        if "test" not in parent_context:
            return f"TestAdapter: {self.field_value} ({parent_context['id']})"
        return f"TestAdapter: {self.field_value} ({parent_context['test']}) ({parent_context['id']})"

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
        self.assertEqual(TestAdapter.required_kwargs, tuple(["test"]))

    def test_absolute_tokens(self):
        self.assertEqual(TestAbsoluteTokensAdapter.absolute_tokens, tuple(["absolute"]))

    def test_required_kwargs_ok(self):
        self.assertEqual(TestAdapter.required_kwargs, tuple(["test"]))
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
            f"TestAdapter: {self.basic_model.title} (test) ({id})"
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

    def test_positional_kwargs(self):
        id = get_adapter_id()
        tpl = Template(
            "{% load fedit %}"
            f"{{% fedit test_absolute_tokens object.title 'test' absolute id='{id}' %}}"
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

        adapter = adapters[id]

        self.assertEqual(
            adapter.kwargs["test"],
            "test",
        )

        self.assertEqual(
            adapter.kwargs["absolute"],
            True,
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
            adapter.render_content(base_adapter_context(
                adapter=adapter,
                context={},
            )),
            f"TestAdapter: {self.basic_model.title} (3)"
        )

    def test_adapter_editable(self):
        id = get_adapter_id()
        self.assertEqual(TestAdapter.required_kwargs, tuple(["test"]))

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
            wrap_adapter(request, adapters[id], base_adapter_context(
                adapter=adapters[id],
                context={},
            ))
        )

    def test_adapter_editable_equals_refetch(self):
        id = get_adapter_id()
        self.assertEqual(TestAdapter.required_kwargs, tuple(["test"]))

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

        adapter = adapters[id]

        self.assertEqual(
            adapter.kwargs["test"],
            "test",
        )

        self.assertEqual(
            adapter.kwargs["id"],
            id,
        )

        self.assertHTMLEqual(
            tpl,
            wrap_adapter(request, adapters[id], base_adapter_context(
                adapter=adapter,
                context={},
            ))
        )

        url = self.get_refetch_url(
            "test",
            self.basic_model._meta.app_label,
            self.basic_model._meta.model_name,
            self.basic_model.pk,
            "title",
        )

        self.client.force_login(self.admin_user)

        response = self.client.get(url, {
            "shared_context":\
                adapters[id].encode_shared_context(),
        })

        json_data = json.loads(
            response.content.decode("utf-8"),
        )

        if "html" not in json_data:
            self.fail(f"Expected 'html' in response, got {json_data}")

        if "success" not in json_data\
            or "success" in json_data and not json_data["success"]:
            self.fail(f"Expected 'success' in response, got {json_data}")

        if "refetch" not in json_data\
            or "refetch" in json_data and not json_data["refetch"]:
            self.fail(f"Expected 'refetch' in response, got {json_data}")

        self.assertHTMLEqual(
            tpl,
            json_data["html"],
        )


    def test_adapter_shared_context(self):
        uid = get_adapter_id()
        self.assertEqual(TestAdapter.required_kwargs, tuple(["test"]))

        tpl = Template(
            "{% load fedit %}"
            f"{{% fedit test object.title test='test' id='{uid}' %}}"
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

        adapter = adapters[uid]

        self.assertEqual(
            adapter.kwargs["test"],
            "test",
        )

        self.assertEqual(
            adapter.kwargs["id"],
            uid,
        )

        new_id = get_adapter_id()
        adapter.kwargs["id"] = new_id
        context = adapter.encode_shared_context()
        adapter.kwargs["id"] = uid

        url = self.get_refetch_url(
            "test",
            self.basic_model._meta.app_label,
            self.basic_model._meta.model_name,
            self.basic_model.pk,
            "title",
        )

        self.client.force_login(self.admin_user)

        self.assertFalse(
            new_id in adapters,
        )

        response = self.client.get(url, {
            "shared_context": context,
        })

        # Load if lazy
        response.content.decode("utf-8")

        self.assertTrue(
            new_id in adapters,
        )

        self.assertFalse(
            id(adapter) == id(adapters[new_id]),
        )

        new_adapter = adapters[new_id]

        self.assertEqual(
            new_adapter.kwargs["test"],
            "test",
        )

        self.assertEqual(
            adapter.kwargs["test"],
            new_adapter.kwargs["test"],
        )

        self.assertEqual(
            new_adapter.kwargs["id"],
            new_id,
        )

        self.assertNotEqual(
            adapter.kwargs["id"],
            new_adapter.kwargs["id"],
        )

    def test_adapter_editable_as_var(self):
        id = get_adapter_id()
        self.assertEqual(TestAdapter.required_kwargs, tuple(["test"]))

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
            wrap_adapter(request, adapters[id], base_adapter_context(
                adapter=adapters[id],
                context={},
            ))
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
            wrap_adapter(request, adapters[id], base_adapter_context(
                adapter=adapters[id],
                context={},
            ), run_context_processors=True)
        )


class BlockAdapterTest(BaseFEditTest):

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
        block_value, _, parent, idx = block
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
        block_value, _, parent, idx = block
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

    def test_move_block_up(self):
        id = get_adapter_id()
        streamfield = self.basic_model.content

        second_streamfield_listvalue_item = "ec3d73d1-fd01-49ba-840a-d44586ac0025"

        block = find_block(second_streamfield_listvalue_item, streamfield)
        block_value, _, parent, idx = block
        if idx != 1:
            self.fail(f"Expected 1, got {idx}")

        self.assertEqual(
            parent[idx].value["link"]["text"],
            "Test Item 2",
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        adapter = TestBlockAdapter(
            self.basic_model,
            "content",
            request,
            id=id,
            block=block_value,
            block_id=second_streamfield_listvalue_item,
            movable=True,
        )

        url = shared_context_url(
            adapter.encode_shared_context(),
            reverse(
                "wagtail_fedit:block-move",
                kwargs=get_reverse_kwargs(adapter)
            ),
            action="up",
        )

        self.client.force_login(self.admin_user)

        response = self.client.post(url)
        if response.status_code != 200:
            self.fail(f"Expected 200, got {response.status_code}")

        self.assertDictEqual(
            json.loads(response.content.decode("utf-8")),
            {
                "success": True,
            }
        )

        self.basic_model.refresh_from_db()

        streamfield = self.basic_model.content
        block = find_block(second_streamfield_listvalue_item, streamfield)
        block_value, _, parent, idx = block

        if idx != 0:
            self.fail(f"Expected 0, got {idx}")
            
        self.assertDictEqual(
            parent[idx].value,
            block_value.value,
        )

        self.assertEqual(
            parent[idx].value["link"]["text"],
            "Test Item 2",
        )


    def test_move_block_down(self):
        id = get_adapter_id()
        streamfield = self.basic_model.content

        first_streamfield_listvalue_item = "c757f54d-0df5-4b35-8a06-4174f180ec41"

        block = find_block(first_streamfield_listvalue_item, streamfield)
        block_value, _, parent, idx = block
        if idx != 0:
            self.fail(f"Expected 0, got {idx}")

        self.assertEqual(
            parent[idx].value["link"]["text"],
            "Test Item 1",
        )

        request = self.request_factory.get(
            self.get_editable_url(
                self.basic_model.pk, self.basic_model._meta.app_label, self.basic_model._meta.model_name,
            )
        )
        adapter = TestBlockAdapter(
            self.basic_model,
            "content",
            request,
            id=id,
            block=block_value,
            block_id=first_streamfield_listvalue_item,
            movable=True,
            addable=True,
        )

        url = shared_context_url(
            adapter.encode_shared_context(),
            reverse(
                "wagtail_fedit:block-move",
                kwargs=get_reverse_kwargs(adapter)
            ),
            action="down",
        )

        self.client.force_login(self.admin_user)

        response = self.client.post(url)
        if response.status_code != 200:
            self.fail(f"Expected 200, got {response.status_code}")

        self.assertDictEqual(
            json.loads(response.content.decode("utf-8")),
            {
                "success": True,
            }
        )

        self.basic_model.refresh_from_db()

        streamfield = self.basic_model.content
        block = find_block(first_streamfield_listvalue_item, streamfield)
        block_value, _, parent, idx = block

        if idx != 1:
            self.fail(f"Expected 1, got {idx}")
            
        self.assertDictEqual(
            parent[idx].value,
            block_value.value,
        )

        self.assertEqual(
            parent[idx].value["link"]["text"],
            "Test Item 1",
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
        block_value, _, parent, idx = block
        template = Template(
            "{% load fedit %}"
            f"{{% fedit test_block from_context block=block block_id=block_id id='{id}' %}}"
        )

        context = {
            "object": self.basic_model,
            "request": request,
            "block": block_value,
            "block_id": self.BLOCK_ID,
            FIELD_TEMPLATE_VAR: "content",
            INSTANCE_TEMPLATE_VAR: self.basic_model,
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
        block_value, _, parent, idx = block
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
                INSTANCE_TEMPLATE_VAR: self.basic_model,
            }
    
            tpl = template.render(Context(context))
    
            self.assertHTMLEqual(
                tpl,
                wrap_adapter(request, adapters[id], context)
            )
