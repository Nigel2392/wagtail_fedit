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


adapter_registry.register(TestAdapter)


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


