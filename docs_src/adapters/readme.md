// Title: Creating an Adapter
// Previous: make_editable.md
// Next: adapters/adapters_python.md
## Adapters

Creating a custom adapter is relatively simple.
We highly recommend you to inherit from `BaseFieldFuncAdapter` or `BaseBlockFuncAdapter`.
These adapters are basically pre-setup to callback to a javascript function on successful form submission.
This will save you the most amount of work.

We will create an adapter to change the color of a text field.

Our adapter will be called `colorizer`.

1. Our model is defined as follows:

```python
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from django.db import models

class MyPage(Page):
    COLOR_CHOICES = [
        ("#000000", "Black"),
        ("#FFFFFF", "White"),
        ("#FF0000", "Red"),
        ("#00FF00", "Green"),
        ("#0000FF", "Blue"),
    ]

    color = models.CharField(max_length=7, default="#000000", choices=COLOR_CHOICES)

    content_panels = Page.content_panels + [
        FieldPanel("color"),
    ]
```

2. We have the following HTML template:

```django-html
...

{% load fedit %}
{% fedit colorizer page.color target=".my-colorized-div" %}
<div class="my-colorized-div" style="color: {{ "{{ page.color }}" }}">
    <h1>Colorized Text!</h1>
</div>
...
```

View the custom Python adapter in the [Adapters Python]({{ index .Tree.adapters.adapters_python.URL }}) page.

View the custom Javascript adapter in the [Adapters Javascript]({{ index .Tree.adapters.adapters_js.URL }}) page.

