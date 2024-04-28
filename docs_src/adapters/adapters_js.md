### Adapters Javascript

We now need to create the javascript function to actually apply the color to the styles of the element.
This function will be called `myColorizerJavascriptFunction`, as defined in the adapter's `__init__` method.

```javascript
// myapp/static/myapp/js/custom.js
function myColorizerJavascriptFunction(element, response) {
    element.style.color = response.color;
}
```

We must then register this javascript file to be included in the frontend editing interface.

This should be done in a `wagtail_hooks.py` file.

```python
# myapp/wagtail_hooks.py

from django.utils.html import format_html
from django.templatetags.static import static
from wagtail_fedit.hooks import REGISTER_JS
from wagtail import hooks

@hooks.register(REGISTER_JS)
def register_js(request):
    return [
        format_html(
            '<script src="{0}"></script>',
            static('myapp/js/custom.js')
        ),
    ]
```
View the custom Python adapter in the [Adapters Python]({{ index .Tree.adapters.adapters_python.URL }}) page.