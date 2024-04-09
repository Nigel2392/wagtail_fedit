from django.contrib.sessions.middleware import SessionMiddleware
from wagtail import blocks

from wagtail_fedit.templatetags import (
    fedit as templatetags,
)
from wagtail_fedit import (
    utils,
)
from .base import (
    BaseFEditTest,
)

class TestBlockTemplateTag(BaseFEditTest):

    def test_render_regular(self):

        block, contentpath = utils.find_block("a98a19c6-2ead-4e69-9ea2-3158c7e82976", self.basic_model.content)
        self.assertEqual(block.value["link"]["text"], "Test Item 3")
        self.assertEqual(contentpath, ["3e9144fd-5fa5-47f8-917e-8fe87c15da01", "items", "a98a19c6-2ead-4e69-9ea2-3158c7e82976"])

        item = self.basic_model.content.stream_block.get_block_by_content_path(self.basic_model.content, contentpath)
        self.assertEqual(item.value["link"]["text"], "Test Item 3")

        # Setup user attribute for request.
        request = self.request_factory.get("/")
        request.user = self.admin_user

        context = {
            "request": request,
            "model": self.basic_model,
            "block": block,
        }

        node = templatetags.BlockEditNode(
            nodelist=None,
            block=block,
            block_id="a98a19c6-2ead-4e69-9ea2-3158c7e82976",
            field_name="content",
            model=self.basic_model,
        )

        self.assertHTMLEqual(
            node.render(context),
            block.render(context)
        )






