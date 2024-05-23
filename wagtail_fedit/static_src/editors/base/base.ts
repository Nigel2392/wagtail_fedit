import { initNewEditors } from "./init";
import { WagtailFeditorAPI } from "./api";
import { EditorModal } from "../../components/modal";
import { FormIFrame } from "./iframe";

export {
    BaseWagtailFeditEditor,
    ResponseObject,
    WrapperElement,
    newCloseButton,
};


interface WrapperElement extends HTMLDivElement {
    editorAPI: WagtailFeditorAPI;
}


type ResponseObject = {
    success: boolean;
    html?: string | null;
    refetch?: boolean;
};


class BaseWagtailFeditEditor extends EventTarget {

    initialTitle: string;
    wrapperElement: WrapperElement;
    api: WagtailFeditorAPI;
    sharedContext: string;
    editBtn: HTMLElement;
    iframe: FormIFrame;
    modal: EditorModal;
    opened: boolean;

    constructor(element: WrapperElement) {
        super();
        this.api = new WagtailFeditorAPI(this);
        this.initialTitle = document.title;
        this.wrapperElement = element;
        this.sharedContext = null;
        this.editBtn = null;
        this.iframe = null;
        this.init();

        if (window.location.hash === `#${this.wrapperElement.id}`) {
            this.openEditor();
            this.focus();
        }
    }

    get editUrl() {
        return this.wrapperElement.dataset.editUrl;
    }

    get refetchUrl() {
        return this.wrapperElement.dataset.refetchUrl;
    }

    get relatedWrappers(): WrapperElement[] {
        const wrapperId = this.wrapperElement.dataset.wrapperId;
        const filterFn = (el: WrapperElement) => el !== this.wrapperElement
        const elements = document.querySelectorAll(`[data-wrapper-id="${wrapperId}"]`)
        return Array.from(elements).filter(filterFn) as WrapperElement[];
    }


    init() {
        this.sharedContext = this.wrapperElement.dataset.sharedContext;
        this.wrapperElement.editorAPI = this.api;
        this.editBtn = this.wrapperElement.querySelector(".wagtail-fedit-edit-button");
        this.editBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (this.opened) {
                return;
            }
            this.openEditor();
        });
    }

    initNewEditors() {
        initNewEditors(this.wrapperElement);
    }

    focus() {
        this.wrapperElement.focus();
    }

    refetch(): Promise<any> {
        return new Promise((resolve, reject) => {
            fetch(this.refetchUrl).then((response) => {
                return response.json();
            }).then((response) => {
                if (!response.success) {
                    console.error("Errors rendering response, failed to refetch", response);
                    return;
                }
                this.onResponse(response);
                resolve(response);
            }).catch((e) => {
                console.error("Failed to refetch", e);
                reject(e);
            });
        })
    }

    refetchParent(fallback: () => void | null) {
        let body = document.body;
        let parent = this.wrapperElement.parentElement;
        while (parent && parent !== body) {
            if (parent.classList.contains("wagtail-fedit-initialized")) {
                (parent as WrapperElement).editorAPI.refetch().then(() => {
                    initNewEditors(parent as HTMLElement);
                });
                return;
            }
            parent = parent.parentElement;
        }

        if (fallback) {
            fallback();
        }
    }

    onResponse(response: ResponseObject): any | Promise<any> {
        throw new Error("onResponse not implemented, cannot call super");
    }

    get frameOptions() {
        return {}
    }

    openIframe(wrapper: HTMLElement, fn: (iframe: FormIFrame) => void) {

        if (this.iframe) {
            wrapper.appendChild(this.iframe.element);
            fn(this.iframe);
            return;
        }

        this.iframe = new FormIFrame({
            url: this.editUrl,
            id: "wagtail-fedit-iframe",
            className: null,
            executeOnloadImmediately: true,
            ...this.frameOptions,
            onLoad: () => {
                const onSubmit = (e: Event) => {
                    e.preventDefault();
                    const formData = new FormData(this.iframe.formElement);

                    this.executeEvent(window.wagtailFedit.EVENTS.SUBMIT, {
                        element: this.wrapperElement,
                        formData: formData,
                    });

                    fetch(this.editUrl, {
                        method: "POST",
                        body: formData,
                    }).then((response) => {
                        return response.json();
                    }).then((response) => {
                        if (!response.success) {
                            console.error("Errors rendering response", response);
                            let newElement = document.createElement("div");
                            newElement.innerHTML = response.html;
                            this.iframe.mainElement.innerHTML = newElement.querySelector("#main").innerHTML;
                            this.iframe.formElement.onsubmit = onSubmit;

                            const uninitializedBlock = this.iframe.mainElement.querySelector("#value[data-block]");
                            if (uninitializedBlock) {
                                this.iframe.window.initBlockWidget(uninitializedBlock.id);
                            }

                            const cancelButton = this.iframe.document.querySelector(".wagtail-fedit-cancel-button");
                            const closeFn = this.closeEditor.bind(this);
                            cancelButton.addEventListener("click", closeFn);
                            this.iframe.onCancel = closeFn;
                            this.executeEvent(window.wagtailFedit.EVENTS.SUBMIT_ERROR, {
                                element: this.wrapperElement,
                                response: response,
                            });
                            return;
                        }
                        const ret = this.onResponse(response);
                        const success = () => {
                            this.closeEditor();
                            this.executeEvent(window.wagtailFedit.EVENTS.CHANGE, {
                                element: this.wrapperElement,
                            });
                        }
                        if (ret instanceof Promise) {
                            ret.then(success);
                        } else {
                            success();
                        }
                    });
                };
                this.iframe.formElement.onsubmit = onSubmit;
                this.iframe.onCancel = this.closeEditor.bind(this);
                
                // Check if we need to apply the fedit-full class to the iframe wrapper
                const formWrapper = this.iframe.formWrapper;
                const options = ["large", "full"]

                for (const option of options) {
                    if (formWrapper && (
                        formWrapper.classList.contains(`fedit-${option}`) ||
                        (this.iframe.formElement.dataset.editorSize || "").toLowerCase() === option
                    )) {
                        wrapper.classList.add(`fedit-${option}`);
                        break;
                    }
                }

                const url = window.location.href.split("#")[0];
                window.history.pushState(null, this.iframe.document.title, url + `#${this.wrapperElement.id}`);
                document.title = this.iframe.document.title;

                this.executeEvent(window.wagtailFedit.EVENTS.EDITOR_LOAD, {
                    iframe: this.iframe,
                });
            },
            onError: () => {
                this.closeEditor();
            },
            onCancel: () => {
                this.closeEditor();
            },
        });


        wrapper.appendChild(this.iframe.element);

        fn(this.iframe);
    }

    openEditor() {
        if (!this.modal) {
            this.modal = new EditorModal({
                modalId: `${this.wrapperElement.id}-modal`,
            });
        }

        this.opened = true;

        this.openIframe((this.modal as any), (iframe) => {
            this.modal.appendChild(
                newCloseButton(this.closeEditor.bind(this))
            );

            this.executeEvent(window.wagtailFedit.EVENTS.EDITOR_OPEN, {
                iframe: this.iframe,
                modal: this.modal,
            });
    
            this.modal.openModal()
        });
    }

    closeEditor() {
        this.opened = false;
        window.history.pushState(null, this.initialTitle, window.location.href.split("#")[0]);
        document.title = this.initialTitle;
        this.executeEvent(window.wagtailFedit.EVENTS.EDITOR_CLOSE);
        this.modal.closeModal();
    }

    executeEvent(name: string, detail?: any): void { 
        if (!detail) {
            detail = {
                element: this.wrapperElement,
            };
        }
       
        detail.editor = this;
        detail.api = this.api;
        if (!name.startsWith(`${window.wagtailFedit.NAMESPACE}:`)) {
            name = `${window.wagtailFedit.NAMESPACE}:${name}`;
        }
        const event = new CustomEvent(name, {
            detail: detail,
        });
        super.dispatchEvent(event);
        this.wrapperElement.dispatchEvent(event);
        document.dispatchEvent(event);
    }
}

function newCloseButton(closeFn: () => void) {
    const button = document.createElement("button");
    button.innerHTML = "&times;";
    button.classList.add("wagtail-fedit-close-button");
    button.addEventListener("click", closeFn);
    return button;
}