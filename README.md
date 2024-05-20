wagtail_fedit
=============

![Wagtail FEdit Example](https://github.com/Nigel2392/wagtail_fedit/blob/main/.github/static/wagtail_fedit_example.png?raw=true)

Wagtail FEdit is a library to allow your Wagtail pages and content-blocks to be edited on the frontend.

[View the documentation](https://nigel2392.github.io/wagtail_fedit/)

Getting Started
---------------

1. Add 'wagtail_fedit' to your INSTALLED_APPS setting like this:

   ```
   INSTALLED_APPS = [
   ...,
   'wagtail_fedit',
   ]
   ```
2. Run `py ./manage.py collectstatic`.
3. Run `py ./manage.py adapter_help` to see all your options and their requirements.

## How your content is rendered

(**Maintainer's note:** In my experience this doesn't mess the CSS up too much, or even at all for most content - **if** you don't get hyperspecific with your CSS selectors and structure your templates well.)

Your block and field are wrapped in a `div`, any CSS for your templates should keep this in mind.

### Rendered editable output HTML

```html
{% load fedit %}<div id="{{ unique_id }}" data-wrapper-id="{{ unique_id }}" class="wagtail-fedit-adapter-wrapper{% if shared_context.inline or adapter.inline %} wagtail-fedit-inline{%endif%} wagtail-fedit-{{ identifier }}" data-fedit-constructor="{{ js_constructor }}" {% if shared %} data-shared-context="{{ shared }}"{%endif%} data-edit-url="{{ edit_url }}" data-refetch-url="{{ refetch_url }}">
    <div class="wagtail-fedit-buttons">
        {% for button in buttons %}
            {{ button }}
        {% endfor %}
    </div>{% render_adapter adapter %}
</div>
```

## Implemented

* Editing fields/blocks on the frontend
* Moving blocks on the frontend
* High compatibility with custom widgets and blocks
* Revision Support
* Locked Support
* Draft Support
* Preview Support
* Workflow Support
* Permissions
* Audit Logs
