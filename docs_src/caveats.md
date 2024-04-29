// Title: Caveats
// Next: hooks.md
// Previous: adapters/adapters_js.md
## Caveats

### ID Attribute

Wagtail does not always make it's `id` attribute available.

This is only available to instances of `StreamChild` and `ListChild`.

Consider the following regular wagtail list loop where `items` is a `ListBlock`.

```django-html
{% for item in self.items %}
    {% include_block item %} {# No access to ID! Cannot edit! #}
{% endfor %}
```

To make this an editable block instead; we would slightly change the loop to make the block's `id` available.

This is done by accessing the `bound_blocks` of that ListBlock *(`StreamBlock` does this automatically for the toplevel block!)*

Our new loop would then be:

```django-html
{% for item in self.items.bound_blocks %}
    {# Field name and model are the same arguments as in the first example! #}
    {% fedit block my_model_instance_var.content_field block=item block_id=item.id %}
{% endfor %}
```

### Wrong Model- links in Wagtail Userbar

Sometimes without thinking about it you might override the default template variable for pages.

This might create issues where the userbar links are not linking to the correct edit- view.

For this we have created a simple solution by including a template-tag at the end of your html template.

Example:

```html
<DOCTYPE ...>
<html>
    ...
    <body>
    ...

    {% fedit_userbar my_model_instance %}
    </body>
</html>
```
