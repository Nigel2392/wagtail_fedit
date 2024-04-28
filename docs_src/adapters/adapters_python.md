### Adapters Python

We will get started creating the adapter definition.
Adapters can be defined anywhere; we recommend a separate `adapters.py` file.

Adapter instances also have access to the following variables:

* `self.object` - The model instance.
* `self.field_name` - The field name.
* `self.meta_field` - The models.Field instance.
* `self.field_value` - The field value (Retrieved with `getattr(self.object, self.field_name)`).
* `self.request` - The django HTTP request object.
* `self.kwargs` - Any shared context / keyword arguments for this adapter.

```python
# myapp/adapters.py

from wagtail_fedit.adapters import (
    BaseFieldFuncAdapter,
    VARIABLES,
)

class ColorizerAdapter(BaseFieldFuncAdapter):
    # Keywords for the adapter can easily be defined.
    # These will be used to inform the templatetag on what is nescessary, required and counts as a flag.
    keywords = (
        Keyword(
            "target",
            help_text="The target element to apply the background-image to - this should be a css selector.",
            type_hint="str",  # Type hint for the `adapter_help` command.
            # optional=False, # Required is the default.
            # absolute=False, # Counts as a keyword argument key=value instead of a boolean flag.
            # default=None,   # Default value if not provided, only for optional keyword arguments.
        ),
    )

    # How the adapter will be adressed inside of the template tag.
    identifier = "colorizer"

    # The function to call in javascript.
    js_function = "myColorizerJavascriptFunction"

    # A simple description of what this adapter does.
    usage_description = "Change the color of the text for the given target element."

    def render_content(self, parent_context=None):
        # This is not required; we will replace a CSS variable; thus we are not returning any actual content.
        return ""
  
    def get_response_data(self, parent_context=None):
        """
        Return the data to be sent to the frontend adapter.
        """
        data = super().get_response_data(parent_context)
        return data | {
            "color": self.field_value,
        }

    def get_form_attrs(self) -> dict:
        """
        Return form attributes for the form inside of the edit modal.
        This can be used to control editor size.
        """
        attrs = super().get_form_attrs()
        attrs[VARIABLES.FORM_SIZE_VAR] = "full" # Fullscreen, there is also `large`.
        return attrs
```

We must then register the adapter to make sure it is available for templates.

This should be done in a `wagtail_hooks.py` file.

```python
# myapp/wagtail_hooks.py

from wagtail_fedit.adapters import adapter_registry
from myapp.adapters import ColorizerAdapter

adapter_registry.register(ColorizerAdapter)
```
