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

        block, contentpath = utils.find_block(self.BLOCK_ID, self.basic_model.content)
        self.assertEqual(block.value["link"]["text"], "Test Item 1")
        self.assertEqual(contentpath, ["3e9144fd-5fa5-47f8-917e-8fe87c15da01", "items", self.BLOCK_ID])

        item = self.basic_model.content.stream_block.get_block_by_content_path(self.basic_model.content, contentpath)
        self.assertEqual(item.value["link"]["text"], "Test Item 1")

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
            block_id=self.BLOCK_ID,
            field_name="content",
            model=self.basic_model,
        )

        self.assertHTMLEqual(
            node.render(context),
            block.render(context)
        )

    def test_render_editable(self):
            
            block, contentpath = utils.find_block(self.BLOCK_ID, self.basic_model.content)
            self.assertEqual(block.value["link"]["text"], "Test Item 1")
            self.assertEqual(contentpath, ["3e9144fd-5fa5-47f8-917e-8fe87c15da01", "items", self.BLOCK_ID])
    
            item = self.basic_model.content.stream_block.get_block_by_content_path(self.basic_model.content, contentpath)
            self.assertEqual(item.value["link"]["text"], "Test Item 1")
    
            # Setup user attribute for request.
            request = self.request_factory.get("/")
            request.user = self.admin_user
    
            context = {
                "request": request,
                "model": self.basic_model,
                "block": block,
            }
    
            # Mark as editable.
            setattr(
                request,
                utils.FEDIT_PREVIEW_VAR,
                True,
            )
    
            node = templatetags.BlockEditNode(
                nodelist=None,
                block=block,
                block_id=self.BLOCK_ID,
                field_name="content",
                model=self.basic_model,
            )

            rendered_block = block.render(context)
            rendered_block = templatetags.render_editable_block(
                 request, rendered_block, self.BLOCK_ID, "content",
                 self.basic_model, context, has_block=True,
            )

            self.assertHTMLEqual(
                node.render(context),
                rendered_block,
            )





