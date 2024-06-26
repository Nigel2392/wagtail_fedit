from django.core.management.base import BaseCommand
from django.core.management.color import color_style, supports_color
from wagtail_fedit.registry import registry as adapter_registry
from wagtail_fedit.utils import TEMPLATE_TAG_NAME
from wagtail_fedit.settings import SHARE_WITH_SESSIONS


class Command(BaseCommand):
    help = "Print an example of how to use all registered adapters."

    def handle(self, *args, **options):
        LB = "\n"

        s = [
            "Registered Adapters",
            "====================",
            " * The first argument is the identifier of the adapter.",
            " * The second argument is the model and/or field to edit. instance.modelfield or instance",
            " * Arguments prefixed with a exclamation mark are absolute. These act like flags.",
            " * Arguments prefixed with a question mark are optional.",
        ]

        if SHARE_WITH_SESSIONS:
            s.extend([
                " * Context is shared with Django sessions. This is useful if you are running into limits with the URL length.",
                "   This will store the session key as a URL parameter and the shared context in the session.",
            ])
        else:
            s.extend([
                " * Extra keyword arguments are optional; must be serializable to JSON and should not be too complex.",
                "   This is due to limits in URL-size when sharing context between views.",
            ])

        s.extend([
            " * You can specify 'as varname' as the last arguments to the templatetag to store the adapter HTML in a context variable.",
        ])

        for identifier, adapter_class in adapter_registry.adapters.items():

            s.append(
                "==========",
            )

            s.append(
                ""
            )

            DISTANCE = "    "

            getter = "instance"
            if adapter_class.field_required:
                getter += ".modelfield"

            s.append(
                f"{DISTANCE}{{% {TEMPLATE_TAG_NAME} {identifier} {getter} {adapter_class.get_usage_string()} %}}",
            )

            HELP_DISTANCE = DISTANCE + "  "
            description = adapter_class.get_usage_description()
            if description:
                s.append(
                    f"{HELP_DISTANCE}{description}",
                )
                
            help_text = adapter_class.get_usage_help_text()
            if help_text:
                mid = f"{HELP_DISTANCE} * "
                help_text = f"{LB}{mid}".join([
                    f"{k}: {v}" for k, v in help_text.items()
                ])
                s.append(
                    f"{mid}{help_text}",
                )

            s.append("")

        if supports_color():
            style = color_style()
            s = style.SUCCESS(LB.join(s))
        else:
            s = LB.join(s)
        self.stdout.write(LB)
        self.stdout.write(s)
        self.stdout.write(LB)


