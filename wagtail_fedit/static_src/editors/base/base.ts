import { initNewEditors } from "./init";
import { WagtailFeditorAPI } from "./api";
import { iFrame } from "./iframe";

export {
    BaseWagtailFeditEditor,
    WrapperElement,
};

interface WrapperElement extends HTMLDivElement {
    editorAPI: WagtailFeditorAPI;
}


const modalHtml = `
<div class="wagtail-fedit-modal-wrapper">
    <div class="wagtail-fedit-modal" id="wagtail-fedit-modal-__ID__-modal">
    </div>
</div>`


class BaseWagtailFeditEditor extends EventTarget {

    initialTitle: string;
    wrapperElement: WrapperElement;
    api: WagtailFeditorAPI;
    sharedContext: string;
    modalHtml: string;
    editBtn: HTMLElement;
    iframe: iFrame;
    modal: HTMLElement;

    constructor(element: WrapperElement) {
        super();
        this.initialTitle = document.title;
        this.wrapperElement = element;
        this.api = new WagtailFeditorAPI(this);
        this.sharedContext = null;
        this.modalHtml = null;
        this.editBtn = null;
        this.init();
        this.iframe = null;

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

    get modalWrapper() {
        const modalWrapper = document.querySelector("#wagtail-fedit-modal-wrapper");
        if (modalWrapper) {
            return modalWrapper;
        }
        const wrapper = document.createElement("div") as WrapperElement;
        wrapper.id = "wagtail-fedit-modal-wrapper";
        wrapper.classList.add("wagtail-fedit-modal-wrapper");
        wrapper.editorAPI = this.api;
        document.body.appendChild(wrapper);
        return wrapper;
    }

    init() {
        this.sharedContext = this.wrapperElement.dataset.sharedContext;
        this.modalHtml = modalHtml.replace("__ID__", this.wrapperElement.dataset.id);
        this.editBtn = this.wrapperElement.querySelector(".wagtail-fedit-edit-button");

        this.wrapperElement.editorAPI = this.api;

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

    /**
     * @returns {Promise<ResponseObject>}
     */
    refetch() {
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

    onResponse(response: any): any | Promise<any> {
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
        this.modalWrapper.innerHTML = this.modalHtml;
        this.modal = this.modalWrapper.querySelector(".wagtail-fedit-modal");

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
                            cancelButton.addEventListener("click", this.closeModal.bind(this));
                            this.iframe.onCancel = this.closeModal.bind(this);
                            this.executeEvent(window.wagtailFedit.EVENTS.SUBMIT_ERROR, {
                                element: this.wrapperElement,
                                response: response,
                            });
                            return;
                        }
                        const ret = this.onResponse(response);
                        const success = () => {
                            this.closeModal();
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
                this.iframe.onCancel = this.closeModal.bind(this);
                
                // Check if we need to apply the fedit-full class to the modal
                const formWrapper = this.iframe.formWrapper;
                const options = ["large", "full"]

                for (const option of options) {
                    if (formWrapper && (
                        formWrapper.classList.contains(`fedit-${option}`) ||
                        (this.iframe.formElement.dataset.editorSize || "").toLowerCase() === option
                    )) {
                        this.modal.classList.add(`fedit-${option}`);
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
                this.closeModal();
            },
            onCancel: () => {
                this.closeModal();
            },
        });

        this.modal.appendChild(this.iframe.element);

        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "&times;";
        closeBtn.classList.add("wagtail-fedit-close-button");
        closeBtn.addEventListener("click", this.closeModal.bind(this));
        this.modal.appendChild(closeBtn);
        this.executeEvent(window.wagtailFedit.EVENTS.MODAL_OPEN, {
            iframe: this.iframe,
            modal: this.modal,
        });
    }

    closeModal() {
        this.modalWrapper.remove();
        window.history.pushState(null, this.initialTitle, window.location.href.split("#")[0]);
        document.title = this.initialTitle;
        this.executeEvent(window.wagtailFedit.EVENTS.MODAL_CLOSE);
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
