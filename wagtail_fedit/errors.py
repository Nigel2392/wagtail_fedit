from django.utils.translation import gettext_lazy as _

class Formatter:
    def __init__(self, *messages):
        self.messages = messages

    def format(self, *args, **kwargs):
        messages = list(self.messages)
        if kwargs:
            raise ValueError("Formatter does not support keyword arguments")
        
        if len(args) > len(messages):
            raise ValueError("Number of arguments does not match number of messages")
        
        made = []
        
        for i, arg in enumerate(args):
            made.append(messages[i].format(arg))

        return " ".join(made)

NO_PERMISSION_VIEW = _("You do not have permission to view this page.")
NO_PERMISSION_ACTION = _("User does not have permission to {}")
NO_WORKFLOW_STATE = _("No workflow state found")
OBJECT_LOCKED = _("This object is locked - it cannot be acted upon.")
OBJECT_NOT_LIVE = _("This object is not live")
ACTION_MISSING = _("No action specified")
INVALID_ACTION = _("Invalid action specified: {}")
MISSING_REQUIRED_SUPERCLASSES = _("Model {} does not inherit from {}")
NO_UNPUBLISHED_CHANGES = _("Object has no unpublished changes")
MODEL_NOT_FOUND = _("Model not found")
INVALID = Formatter(
    _("Invalid {}"),
    _("for object {}"),
)
REQUIRED = Formatter(
    _("{} is required"),
    _("for object {}"),
)
