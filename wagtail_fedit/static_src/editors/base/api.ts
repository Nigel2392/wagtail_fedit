import { getCookie } from "../../utils";
import { BaseWagtailFeditEditor, WrapperElement } from "./base";

export {
    WagtailFeditorAPI,
};

type UpdateFunc = (update: (html: string) => HTMLElement) => void;


class WagtailFeditorAPI {
    private editor: BaseWagtailFeditEditor;

    constructor(editor: BaseWagtailFeditEditor) {
        this.editor = editor;
    }

    openEditor() {
        this.editor.openEditor();
    }

    closeEditor() {
        this.editor.closeEditor();
    }

    executeEvent(name: string, detail: any) {
        this.editor.executeEvent(name, detail);
    }

    addEventListener(name: string, callback: EventListener) {
        this.editor.addEventListener(name, callback);
    }

    removeEventListener(name: string, callback: EventListener, options?: boolean | EventListenerOptions) {
        this.editor.removeEventListener(name, callback, options);
    }

    updateHtml(html: string | UpdateFunc) {
        return new Promise((resolve, reject) => {
            const update: (html: string) => HTMLElement = (innerHtml) => {
                const blockWrapper = this.editor.wrapperElement;
                const element = document.createElement("div");
                element.innerHTML = innerHtml;
                const newBlockWrapper = element.firstElementChild as WrapperElement;
                newBlockWrapper.classList.add("wagtail-fedit-initialized");
                blockWrapper.parentNode.insertBefore(newBlockWrapper, blockWrapper);
                blockWrapper.parentNode.removeChild(blockWrapper);
                this.editor.wrapperElement = newBlockWrapper;
                this.editor.initNewEditors();
                this.editor.init();

                resolve(newBlockWrapper);

                return blockWrapper;
            }

            if (typeof html === "string") {
                update(html);
                return;
            }

            if (typeof html === "function") {
                this.editor.wrapperElement.editorAPI = this;
                html(update);
                return;
            }
        });
    }

    async fetch(url: string, method: string, body: any) {
        let headers = new Headers();
        headers.append("X-Requested-With", "XMLHttpRequest");
        headers.append("X-CSRFToken", getCookie("csrftoken"));

        if (!(body instanceof FormData)) {
            body = JSON.stringify(body);
        }

        return fetch(url, {
            method: method,
            headers: headers,
            body: body,
        }).then((response) => {
            return response.json();
        });
    }

    refetch() {
        return this.editor.refetch();
    }

    execRelated(func: (editorAPI: WagtailFeditorAPI) => void) {
        for (const wrapper of this.editor.relatedWrappers) {
            func(wrapper.editorAPI);
        }
    }
}
