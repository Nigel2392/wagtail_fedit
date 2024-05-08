import { WrapperElement } from "./base";
import { Tooltip } from "./tooltips";

export {
    initNewEditors,
    getEditorClass,
    setScrollParams,
};

function getEditorClass(element: HTMLElement) {
    const editorClass = element.dataset.feditConstructor;
    if (editorClass) {
        return window.wagtailFedit.editors[editorClass];
    }
    throw new Error("No editor class found for element");
}


function initNewEditors(wrapper: HTMLElement | Document = document) {
    let wagtailFeditBlockEditors;
    if (
        wrapper instanceof HTMLElement
        && wrapper.classList.contains("wagtail-fedit-adapter-wrapper")
        && !wrapper.classList.contains("wagtail-fedit-initialized")
    ) {
        wagtailFeditBlockEditors = [wrapper];
    } else {
        wagtailFeditBlockEditors = wrapper.querySelectorAll(".wagtail-fedit-adapter-wrapper");
    }
    for (let i = 0; i < wagtailFeditBlockEditors.length; i++) {
        const editor = wagtailFeditBlockEditors[i] as WrapperElement;
        if (!editor.classList.contains("wagtail-fedit-initialized")) {
            editor.classList.add("wagtail-fedit-initialized");
            const editorClass = getEditorClass(editor);
            if (editorClass) {
                new editorClass(editor);
            } else {
                console.error("No editor class found for element", editor);
            }
        }

        const editButtons = wrapper.querySelectorAll("[data-tooltip='true']") as NodeListOf<HTMLElement>;
        for (let i = 0; i < editButtons.length; i++) {
            const button = editButtons[i];
            if (button.dataset.tooltip == "true") {
                new Tooltip(button);
                delete button.dataset.tooltip;
            }
        }
    }
}

function setScrollParams(button: HTMLAnchorElement) {
    if (!button) {
        return;
    }
    const url = new URL(button.href);
    if (window.scrollY > 100) {
        url.searchParams.set("scrollY", `${window.scrollY}`);
    }
    if (window.scrollX > 100) {
        url.searchParams.set("scrollX", `${window.scrollX}`);
    }
    button.href = url.toString();
}
