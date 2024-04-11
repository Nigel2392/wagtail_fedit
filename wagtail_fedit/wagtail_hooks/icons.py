from wagtail import hooks


@hooks.register("register_icons")
def register_icons(icons):
    icons.extend([
        "wagtail_fedit/icons/fedit-save.svg",
        "wagtail_fedit/icons/fedit-check-list.svg",
        "wagtail_fedit/icons/fedit-eye-open.svg",
        "wagtail_fedit/icons/fedit-eye-closed.svg",
        "wagtail_fedit/icons/fedit-stop-sign.svg",
    ])

    return icons
