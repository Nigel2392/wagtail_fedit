{{ Set "Title" "Installation Instructions" }}
{{ Set "Next" (index .Tree.make_editable) }}
Getting Started
---------------
1. Add 'wagtail_fedit' to your INSTALLED_APPS setting like this:

    ```python
    INSTALLED_APPS = [
        ...,
        'wagtail_fedit',
    ]
    ```
2. Run `py ./manage.py collectstatic`.
3. Run `py ./manage.py adapter_help` to see all your options and their requirements.

Click [here]({{ index .Tree.make_editable.URL }}) to get more information on how to make your models editable.