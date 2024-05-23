from typing import (
    TYPE_CHECKING,
)
from django.urls import (
    reverse,
)
from django.utils.translation import (
    gettext_lazy as _,
)
from ... import utils
from ...toolbar import (
    FeditAdapterComponent,
)

if TYPE_CHECKING:
    from .adapter import BlockAdapter

class BaseBlockButton(FeditAdapterComponent):
    permissions = [
        "wagtailadmin.access_admin",
    ]
    adapter: "BlockAdapter"
    required_kwarg: str = None
    reverse_url: str = None

    def is_shown(self):
        return super().is_shown() and self.adapter.kwargs[self.required_kwarg]

    def get_context_data(self):
        return super().get_context_data() | {
            "change_url": utils.shared_context_url(self.adapter.shared_context_string, reverse(
                self.reverse_url,
                kwargs=utils.get_reverse_kwargs(self.adapter)
            ), **self.get_url_kwargs()),
        }
    
    def get_url_kwargs(self):
        return {}

class BaseMoveButton(BaseBlockButton):
    reverse_url = "wagtail_fedit:block-move"
    required_kwarg = "movable"

    def get_context_data(self):
        return super().get_context_data() | {
            "direction": self.direction,
        }
    
    def get_url_kwargs(self):
        return {
            "action": self.direction,
        }

class MoveUpButton(BaseMoveButton):
    template_name = "wagtail_fedit/content/buttons/move_up.html"
    direction = "up"

class MoveDownButton(BaseMoveButton):
    template_name = "wagtail_fedit/content/buttons/move_down.html"
    direction = "down"

class AddableButton(BaseBlockButton):
    reverse_url = "wagtail_fedit:block-add"
    template_name = "wagtail_fedit/content/buttons/add_block.html"
    required_kwarg = "addable"
