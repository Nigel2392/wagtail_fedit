from django.utils.translation import (
    gettext_lazy as _,
    gettext,
)
from wagtail.log_actions import LogFormatter
from wagtail import hooks

@hooks.register("register_log_actions")
def register_core_log_actions(actions):
    actions.register_action("wagtail_fedit.related_changed", _("Edit Related"), _("Related Object Edited"))

    @actions.register_action("wagtail_fedit.edit_field")
    class FieldChangedFormatter(LogFormatter):
        label = _("Field Changed (Frontend)")
        message = _("A field was changed from the frontend")

        def format_message(self, log_entry):
            data = log_entry.data

            if not "verbose_field_name" in data:
                return self.label

            if "edited_model_string" in data\
                and "edited_model_verbose" in data:
                return _("Changed related '%(related)s' instance '%(instance)s' on field '%(field)s' (Frontend)") % {
                    "field": gettext(data["verbose_field_name"]),
                    "related": gettext(data["edited_model_verbose"]),
                    "instance": data["edited_model_string"],
                }

            try:

                old = data["old"]
                new = data["new"]

                if len(old) > 50:
                    old = old[:50] + "..."

                if len(new) > 50:
                    new = new[:50] + "..."

                return _("Changed '%(field)s' from '%(old)s' to '%(new)s' (Frontend)") % {
                    "field": gettext(data["verbose_field_name"]),
                    "old": old,
                    "new": new,
                }
            
            except KeyError:
                return _("Edit Field")

    @actions.register_action("wagtail_fedit.edit_model")
    class ModelChangedFormatter(LogFormatter):
        label = _("Model Changed (Frontend)")
        message = _("A model was changed from the frontend")

        def format_message(self, log_entry):
            data = log_entry.data

            if not "model_verbose" in data:
                return self.label
            
            return _("Changed '%(model)s' (Frontend)") % {
                "model": gettext(data["model_verbose"]),
            }
            
    @actions.register_action("wagtail_fedit.edit_block")
    class BlockChangedFormatter(LogFormatter):
        label = _("Block Changed (Frontend)")
        message = _("A block was changed from the frontend")
        must = [
            "block_id",
            "verbose_field_name",
            "block_label",
        ]

        def format_message(self, log_entry):
            data = log_entry.data

            if not all([key in data for key in self.must]):
                return self.label

            return _("Changed block \"%(block)s\" on field \"%(field)s\" (%(block_id)s, Frontend)") % {
                "block": gettext(data["block_label"]),
                "field": gettext(data["verbose_field_name"]),
                "block_id": data["block_id"],
            }
        
    @actions.register_action("wagtail_fedit.move_block")
    class BlockMovedFormatter(LogFormatter):
        label = _("Block Moved (Frontend)")
        message = _("A block was moved from the frontend")
        must = [
            "field_name",
            "block_label",
            "block_id",
            "direction",
        ]

        def format_message(self, log_entry):
            data = log_entry.data

            if not all([key in data for key in self.must]):
                return _("Moved block on field (Frontend)")

            return _("Moved block \"%(block)s\" on field \"%(field)s\" %(direction)s (%(block_id)s, Frontend)") % {
                "block": gettext(data["block_label"]),
                "field": gettext(data["field_name"]),
                "direction": gettext(data["direction"]),
                "block_id": data["block_id"],
            }
    