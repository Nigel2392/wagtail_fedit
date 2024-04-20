from django.core.management.base import BaseCommand
from django.core.management.color import color_style, supports_color
from wagtail_fedit.adapters import adapter_registry
from wagtail_fedit.utils import TEMPLATE_TAG_NAME


class Command(BaseCommand):
    help = "Print an example of how to use all registered adapters."

    def handle(self, *args, **options):
        s = [
            " Registered Adapters",
            "====================",
            " * The first argument is the identifier of the adapter.",
            " * The second argument is the model and field to edit. instance.modelfield",
            " * Absolute arguments (missing an equal sign) are optional and treated as booleans.",
            " * Keyword arguments wrapped in square brackets are optional. [key=value]",
            " * The value of the adapter is the value of the field.",
            "====================",
            "",
        ]

        for identifier, adapter_class in adapter_registry.adapters.items():
            s.append(
                f"    {{% {TEMPLATE_TAG_NAME} {identifier} instance.modelfield {adapter_class.usage_string()} %}}",
            )
            help_text = adapter_class.usage_help_text()
            if help_text:
                help_text = "\n      * ".join(help_text)
                s.append(f"      * {help_text}")
                s.append("")
            else:
                s.append("")

        if supports_color():
            style = color_style()
            s = style.SUCCESS("\n".join(s))
        else:
            s = "\n".join(s)
        self.stdout.write("\n")
        self.stdout.write(s)
        self.stdout.write("\n")


