export {};

import { initNewEditors, setScrollParams } from "./editors/base/init";
import { BaseWagtailFeditEditor } from "./editors/base/base";
import { WagtailFeditPublishMenu } from "./components/menu";
import {
    BaseFuncEditor,
    WagtailFeditFuncEditor,
    FieldEditor,
    DomPositionedFieldEditor,
    BlockEditor,
    DomPositionedBlockEditor,
    backgroundImageAdapter,
} from "./editors/editors";
import { Tooltip } from "./components/tooltips";
import { iFrame } from "./editors/base/iframe";

export {
    BaseWagtailFeditEditor,
    Tooltip,
    iFrame,
};

type EditorCallback = (targetElement: HTMLElement, response: any) => void;

declare global {
    interface Window {
        wagtailFedit: {
            NAMESPACE: string;
            EVENTS: {
                SUBMIT: string;
                CHANGE: string;
                EDITOR_OPEN: string;
                EDITOR_LOAD: string;
                EDITOR_CLOSE: string;
                SUBMIT_ERROR: string;
            };
            editors: Record<string, typeof BaseWagtailFeditEditor>;
            funcs: Record<string, EditorCallback>;
            register: (name: string, editor: BaseWagtailFeditEditor) => void;
            registerFunc: (name: string, func: EditorCallback) => void;
        };
    }
}

window.wagtailFedit = {
    NAMESPACE: "wagtail-fedit",
    EVENTS: {
        SUBMIT: "wagtail-fedit:submit",
        CHANGE: "wagtail-fedit:change",
        EDITOR_OPEN: "wagtail-fedit:editorOpen",
        EDITOR_LOAD: "wagtail-fedit:editorLoad",
        EDITOR_CLOSE: "wagtail-fedit:editorClose",
        SUBMIT_ERROR: "wagtail-fedit:submitError",
    },
    editors: {
        "wagtail_fedit.editors.BaseFuncEditor": BaseFuncEditor,
        "wagtail_fedit.editors.FieldEditor": FieldEditor,
        "wagtail_fedit.editors.BlockEditor": BlockEditor,
        "wagtail_fedit.editors.DomPositionedFieldEditor": DomPositionedFieldEditor,
        "wagtail_fedit.editors.DomPositionedBlockEditor": DomPositionedBlockEditor,
        "wagtail_fedit.editors.WagtailFeditFuncEditor": WagtailFeditFuncEditor,
    },
    funcs: {
        "wagtail_fedit.funcs.backgroundImageFunc": backgroundImageAdapter,
    },
    register: function (name, editor) {
        this.editors[name] = editor;
    },

    registerFunc: function (name, func) {
        this.funcs[name] = func;
    },
};



function initFEditors() {
    initNewEditors()
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (let i = 0; i < mutation.addedNodes.length; i++) {
                const node = mutation.addedNodes[i];
                if (node.nodeType === 1) {
                    initNewEditors(node as HTMLElement);
                }
            }
        }
    });
    observer.observe(document.body, {childList: true, subtree: true});

    const url = new URL(window.location.href);
    const scrollY = (url.searchParams.get("scrollY") || 0) as number;
    const scrollX = (url.searchParams.get("scrollX") || 0) as number;
    if (scrollY > 0 || scrollX > 0) {
        window.scrollTo(scrollX, scrollY);
    }

    const userbar = document.querySelector("wagtail-userbar");
    if (userbar) {
        const editButton = userbar.shadowRoot.querySelector("#wagtail-fedit-editor-button");
        const liveButton = userbar.shadowRoot.querySelector("#wagtail-fedit-live-button");
        const publishMenu = userbar.shadowRoot.querySelector("#wagtail-fedit-publish-menu");


        if (editButton || liveButton) {
            let timer: NodeJS.Timeout;

            window.addEventListener("scroll", () => {
                if (timer) {
                    clearTimeout(timer);
                }
                timer = setTimeout(() => {
                    setScrollParams(editButton as HTMLAnchorElement);
                    setScrollParams(liveButton as HTMLAnchorElement);
    
                    const windowURL = new URL(window.location.href);
                    windowURL.searchParams.set("scrollY", `${window.scrollY}`);
                    windowURL.searchParams.set("scrollX", `${window.scrollX}`);
                    window.history.replaceState(null, "", windowURL.toString());
                }, 50);
            });
        }


        if (publishMenu) {
            new WagtailFeditPublishMenu(publishMenu as HTMLElement);
        }
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initFEditors);
} else {
    initFEditors();
}