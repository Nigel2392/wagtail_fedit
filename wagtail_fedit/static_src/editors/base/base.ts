import { initNewEditors } from "./init";
import { WagtailFeditorAPI } from "./api";
import { EditorModal } from "./modal";
import { iFrame } from "./iframe";

export {
    BaseWagtailFeditEditor,
    ResponseObject,
    WrapperElement,
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
    iframe: iFrame;
    modal: EditorModal;

    constructor(element: WrapperElement) {
        super();
        this.api = new WagtailFeditorAPI(this);
        this.initialTitle = document.title;
        this.wrapperElement = element;
        this.sharedContext = null;
        this.editBtn = null;
        this.iframe = null;
        this.init();

        this.modal = new EditorModal({
            modalId: this.wrapperElement.id,
            onClose: () => {
                window.history.pushState(null, this.initialTitle, window.location.href.split("#")[0]);
                document.title = this.initialTitle;
                this.executeEvent(window.wagtailFedit.EVENTS.MODAL_CLOSE);
            },
        });

        if (window.location.hash === `#${this.wrapperElement.id}`) {
            this.makeModal();
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
            await this.makeModal();
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
            fetch(this.getRefetchUrl()).then((response) => {
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

    onResponse(response: ResponseObject): any | Promise<any> {
        throw new Error("onResponse not implemented, cannot call super");
    }

    getEditUrl() {
        // build the edit url from relative edit url
        const url = new URL(window.location.href);
        url.pathname = this.editUrl;
        if (this.sharedContext) {
            url.searchParams.set("shared_context", this.sharedContext);
        }
        return url.toString();
    }

    getRefetchUrl() {
        // build the edit url from relative edit url
        const url = new URL(window.location.href);
        url.pathname = this.refetchUrl;
        if (this.sharedContext) {
            url.searchParams.set("shared_context", this.sharedContext);
        }
        return url.toString();
    }

    async makeModal() {
        this.iframe = new iFrame({
            url: this.getEditUrl(),
            id: "wagtail-fedit-iframe",
            className: null,
            onLoad: () => {
                const onSubmit = (e: Event) => {
                    e.preventDefault();
                    const formData = new FormData(this.iframe.formElement);

                    this.executeEvent(window.wagtailFedit.EVENTS.SUBMIT, {
                        element: this.wrapperElement,
                        formData: formData,
                    });

                    fetch(this.getEditUrl(), {
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
                            const modalCloseFn = this.modal.closeModal.bind(this.modal);
                            cancelButton.addEventListener("click", modalCloseFn);
                            this.iframe.onCancel = modalCloseFn;
                            this.executeEvent(window.wagtailFedit.EVENTS.SUBMIT_ERROR, {
                                element: this.wrapperElement,
                                response: response,
                            });
                            return;
                        }
                        const ret = this.onResponse(response);
                        const success = () => {
                            this.modal.closeModal();
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
                this.iframe.onCancel = this.modal.closeModal.bind(this.modal);
                
                // Check if we need to apply the fedit-full class to the modal
                const formWrapper = this.iframe.formWrapper;
                const options = ["large", "full"]

                for (const option of options) {
                    if (formWrapper && (
                        formWrapper.classList.contains(`fedit-${option}`) ||
                        (this.iframe.formElement.dataset.editorSize || "").toLowerCase() === option
                    )) {
                        this.modal.addClass(`fedit-${option}`);
                        break;
                    }
                }

                const url = window.location.href.split("#")[0];
                window.history.pushState(null, this.iframe.document.title, url + `#${this.wrapperElement.id}`);
                document.title = this.iframe.document.title;

                this.executeEvent(window.wagtailFedit.EVENTS.MODAL_LOAD, {
                    iframe: this.iframe,
                    modal: this.modal,
                });
            },
            onError: () => {
                this.modal.closeModal();
            },
            onCancel: () => {
                this.modal.closeModal();
            },
        });

        this.modal.appendChild(this.iframe.element);

        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "&times;";
        closeBtn.classList.add("wagtail-fedit-close-button");
        closeBtn.addEventListener("click", this.modal.closeModal.bind(this.modal));
        this.modal.appendChild(closeBtn);
        this.executeEvent(window.wagtailFedit.EVENTS.MODAL_OPEN, {
            iframe: this.iframe,
            modal: this.modal,
        });

        this.modal.openModal()
    }

    executeEvent(name: string, detail?: any): void { 
        if (!detail) {
            detail = {
                element: this.wrapperElement,
            };
        }
       
        detail.editor = this;
        detail.api = this.api;
        let eventStr = name.toLowerCase();
        if (!name.startsWith(`${window.wagtailFedit.NAMESPACE}:`)) {
            eventStr = `${window.wagtailFedit.NAMESPACE}:${name}`;
        }
        const event = new CustomEvent(eventStr, {
            detail: detail,
        });
        super.dispatchEvent(event);
        this.wrapperElement.dispatchEvent(event);
        document.dispatchEvent(event);
    }
}
