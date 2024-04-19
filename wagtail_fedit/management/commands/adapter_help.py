from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import color_style, supports_color
from wagtail_fedit.adapters import adapter_registry
from wagtail_fedit.utils import TEMPLATE_TAG_NAME


class Command(BaseCommand):
    help = "Print an example of how to use all registered adapters."

    def handle(self, *args, **options):
        s = [
            "Registered Adapters:",
        ]

        for identifier, adapter_class in adapter_registry.adapters.items():
            s.append(
                f"\t{{% {TEMPLATE_TAG_NAME} {identifier} instance.modelfield {adapter_class.usage_string()} %}}",
            )

        if supports_color():
            style = color_style()
            s = style.SUCCESS("\n".join(s))
        else:
            s = "\n".join(s)
        self.stdout.write(s)
        self.stdout.write("\n")


