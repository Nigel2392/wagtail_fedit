

class iFrame {
    constructor(options) {
        const {
            url,
            id,
            className,
            onLoad = () => {},
            onError = () => {},
        } = options;


        this.url = url;
        this.id = id;
        this.className = className;
        this.onLoad = onLoad;
        this.onError = onError;
        this.render();
    }

    get element() {
        if (!this.iframe) {
            this.iframe = this._renderFrame(this.url, this.onLoad);
        }
        return this.iframe;
    }

    get document() {
        return this.element.contentWindow.document;
    }

    get window() {
        return this.element.contentWindow;
    }

    get mainElement() {
        return this.document.querySelector("#main");
    }

    get formElement() {
        return this.document.querySelector("#wagtail-fedit-form");
    }

    get formWrapper() {
        return this.document.querySelector(".wagtail-fedit-form-wrapper");
    }

    update(url) {
        this.url = url;
        this._renderFrame(this.url, ({ newFrame }) => {
            this.iframe.remove();
            this.iframe = newFrame;
            this.onLoad({ newFrame });
        }, this.onError);
    }

    render() {
        if (this.iframe) {
            return this.iframe;
        }
        this.iframe = this._renderFrame(this.url, this.onLoad);
        return this.iframe;
    }

    _renderFrame(url, onLoad, onError) {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.id = this.id;
        iframe.className = this.className;
        iframe.onload = () => {
            onLoad({ newFrame: iframe});
        };
        iframe.onerror = () => {
            onError();
        };
        return iframe;
    }
}

const modalHtml = `
<div class="wagtail-fedit-modal-wrapper">
    <div class="wagtail-fedit-modal" id="wagtail-fedit-modal-__ID__-modal">
    </div>
</div>`


class WagtailFeditorAPI {
    #editor = null;

    constructor(editor) {
        this.#editor = editor;
    }

    openModal() {
        this.#editor.makeModal();
    }

    closeModal() {
        this.#editor.closeModal();
    }
}


class WagtailFeditEditor {
    constructor(options) {
        const {
            element = null,
            wrapperQuerySelector = ".wagtail-fedit-block-wrapper",
            type = "block",
        } = options;

        this.type = type;
        this.initialTitle = document.title;
        
        if (!element) {
            this.wrapperQuerySelector = wrapperQuerySelector;
            this.wrapperElement = document.querySelector(this.wrapperQuerySelector);
        } else {
            /**@type {HTMLElement} */
            this.wrapperElement = element;
        }
        this.editUrl = null;
        this.modalHtml = null;
        this.editBtn = null;
        this.init();
        this.iframe = null;

        if (window.location.hash === `#${this.wrapperElement.id}`) {
            this.makeModal();
            this.focus();
        }
    }

    get wrapperElementContent() {
        return this.wrapperElement.querySelector(`.wagtail-fedit-${this.type}-content`);
    }

    focus() {
        const rect = this.wrapperElementContent.getBoundingClientRect();
        if ((rect.top + rect.height) > window.innerHeight) {
            window.scrollTo(0, rect.top);
        }
    }

    makeModal() {
        this.modalWrapper.innerHTML = this.modalHtml;
        this.modal = this.modalWrapper.querySelector(".wagtail-fedit-modal");
        this.iframe = new iFrame({
            url: this.editUrl,
            id: null,
            className: null,
            onLoad: () => {
                const onSubmit = (e) => {
                    e.preventDefault();
                    const formData = new FormData(this.iframe.formElement);
                    fetch(this.editUrl, {
                        method: "POST",
                        body: formData,
                    }).then((response) => {
                        response = response.json();
                        return response;
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

                            const cancelButton = this.iframe.document.querySelector("button.wagtail-fedit-cancel-button");
                            cancelButton.addEventListener("click", this.closeModal.bind(this));
                            return;
                        }
                        this.wrapperElement.style.display = "none";
                        this.setWrapperHtml(response.html);
                        this.initNewEditors();
                        this.closeModal();
                    });
                };
                const cancelButton = this.iframe.document.querySelector("button.wagtail-fedit-cancel-button");
                cancelButton.addEventListener("click", this.closeModal.bind(this));
                this.iframe.formElement.onsubmit = onSubmit;
                
                // Check if we need to apply the fedit-full class to the modal
                const formHeight = this.iframe.formElement.getBoundingClientRect().height;
                const formWrapper = this.iframe.formWrapper;
                if (
                    (formWrapper && (
                        formWrapper.classList.contains("fedit-full") ||
                        (this.iframe.formElement.dataset.isRelation || "").toLowerCase() === "true"
                    )) ||
                    (formHeight > window.innerHeight)
                ) {
                    this.modal.classList.add("fedit-full");
                }

                // Check if we should adjust the modal height to the height of the iframe form.
                if (formHeight > this.modal.getBoundingClientRect().height) {
                    this.modal.style.height = `${formHeight}px`;
                }

                const url = window.location.href.split("#")[0];
                window.history.pushState(null, this.iframe.document.title, url + `#${this.wrapperElement.id}`);
                document.title = this.iframe.document.title;
            },
        });
        this.modal.appendChild(this.iframe.element);

        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "&times;";
        closeBtn.classList.add("wagtail-fedit-close-button");
        closeBtn.addEventListener("click", this.closeModal.bind(this));
        this.modal.appendChild(closeBtn);
    }

    setWrapperHtml(html) {
        const newBlock = document.createElement("div");
        newBlock.innerHTML = html;
        const blockWrapper = newBlock.firstElementChild;
        this.wrapperElement.parentNode.insertBefore(blockWrapper, this.wrapperElement);
        this.wrapperElement.parentNode.removeChild(this.wrapperElement);
        this.wrapperElement = blockWrapper;
        this.init();
    }

    closeModal() {
        this.modalWrapper.innerHTML = "";
        window.history.pushState(null, this.initialTitle, window.location.href.split("#")[0]);
        document.title = this.initialTitle;
    }

    get modalWrapper() {
        return this.wrapperElement.querySelector(".wagtail-fedit-frontend-edit");
    }

    init() {
        this.editUrl = this.wrapperElement.dataset.editUrl;
        this.modalHtml = modalHtml.replace("__ID__", this.wrapperElement.dataset.id);
        this.editBtn = this.wrapperElement.querySelector(".wagtail-fedit-edit-button");

        const api = new WagtailFeditorAPI(this);
        const content = this.wrapperElementContent;
        this.wrapperElement.editorAPI = api;
        if (content) {
            content.editorAPI = api;
        }

        this.editBtn.addEventListener("click", (e) => {
            this.makeModal();
        });
    }

    initNewEditors() {
        const wagtailFeditBlockEditors = this.wrapperElement.querySelectorAll(".wagtail-fedit-block-wrapper");
        for (const editor of wagtailFeditBlockEditors) {
            if (!editor.classList.contains("wagtail-fedit-initialized")) {
                editor.classList.add("wagtail-fedit-initialized");
                new WagtailFeditEditor({element: editor, type: this.type});
            }
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const wagtailFeditBlockEditors = document.querySelectorAll(".wagtail-fedit-block-wrapper");
    const wagtailFeditFieldEditors = document.querySelectorAll(".wagtail-fedit-field-wrapper");
    for (const editor of wagtailFeditBlockEditors) {
        if (!editor.classList.contains("wagtail-fedit-initialized")) {
            editor.classList.add("wagtail-fedit-initialized");
            new WagtailFeditEditor({element: editor, type: "block"});
        }
    }
    for (const editor of wagtailFeditFieldEditors) {
        if (!editor.classList.contains("wagtail-fedit-initialized")) {
            editor.classList.add("wagtail-fedit-initialized");
            new WagtailFeditEditor({element: editor, type: "field"});
        }
    }
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === 1) {
                    if (node.classList.contains("wagtail-fedit-block-wrapper") && !node.classList.contains("wagtail-fedit-initialized")) {
                        new WagtailFeditEditor({element: node});
                    }
                }
            }
        }
    });
    observer.observe(document.body, {childList: true, subtree: true});
});

