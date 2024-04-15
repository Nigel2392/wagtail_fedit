

class iFrame {
    constructor(options) {
        const {
            id,
            className,
            srcdoc = null,
            url = null,
            onLoad = () => {},
            onError = () => {},
            onCancel = () => {},
        } = options;


        this.url = url;
        this.srcdoc = srcdoc;
        this.iframe = null;
        this.id = id;
        this.className = className;
        this.onLoad = onLoad;
        this.onError = onError;
        this.onCancel = onCancel;
        this.render();
    }

    get element() {
        if (!this.iframe) {
            this.iframe = this._renderFrame(this.url, this.srcdoc, this.onLoad);
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

    update(url = null, srcdoc = null) {
        this.srcdoc = srcdoc;
        this.url = url;
        this._renderFrame(this.url, this.srcdoc, ({ newFrame }) => {
            this.iframe.remove();
            this.iframe = newFrame;
            this.onLoad({ newFrame });
        }, this.onError);
    }

    render() {
        if (this.iframe) {
            return this.iframe;
        }
        this.iframe = this._renderFrame(this.url, this.srcdoc, this.onLoad);
        return this.iframe;
    }

    _renderFrame(url, srcDoc, onLoad, onError) {
        const iframe = document.createElement('iframe');
        if (srcDoc) {
            iframe.srcdoc = srcDoc;
        } else {
            iframe.src = url;
        }
        iframe.id = this.id;
        iframe.className = this.className;
        iframe.onload = () => {
            const cancelButton = this.document.querySelector(".wagtail-fedit-cancel-button");
            if (cancelButton) {
                cancelButton.addEventListener("click", this.onCancel);
            }
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
        } = options;

        this.initialTitle = document.title;
        
        if (!element) {
            this.wrapperQuerySelector = wrapperQuerySelector;
            this.wrapperElement = document.querySelector(this.wrapperQuerySelector);
        } else {
            /**@type {HTMLElement} */
            this.wrapperElement = element;
        }
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

    focus() {
        this.wrapperElement.focus();
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

    async makeModal() {
        this.modalWrapper.innerHTML = this.modalHtml;
        this.modal = this.modalWrapper.querySelector(".wagtail-fedit-modal");

        this.iframe = new iFrame({
            url: this.getEditUrl(),
            id: "wagtail-fedit-iframe",
            className: null,
            onLoad: () => {
                const onSubmit = (e) => {
                    e.preventDefault();
                    const formData = new FormData(this.iframe.formElement);
                    fetch(this.getEditUrl(), {
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

                            const cancelButton = this.iframe.document.querySelector(".wagtail-fedit-cancel-button");
                            cancelButton.addEventListener("click", this.closeModal.bind(this));
                            return;
                        }
                        this.setWrapperHtml(response.html);
                        this.initNewEditors();
                        this.closeModal();

                        const event = new CustomEvent("wagtail-fedit:change", {
                            detail: {
                                element: this.wrapperElement,
                            }
                        });
                        document.dispatchEvent(event);
                    });
                };
                this.iframe.formElement.onsubmit = onSubmit;
                this.iframe.onCancel = this.closeModal.bind(this);
                
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

                const url = window.location.href.split("#")[0];
                window.history.pushState(null, this.iframe.document.title, url + `#${this.wrapperElement.id}`);
                document.title = this.iframe.document.title;
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
    }

    setWrapperHtml(html) {
        
        const anim = this.wrapperElement.animate([
            {opacity: 1},
            {opacity: 0},
        ], {
            duration: 350,
            easing: "ease-in-out",
        });

        anim.onfinish = () => {
            const newBlock = document.createElement("div");
            newBlock.innerHTML = html;
            const blockWrapper = newBlock.firstElementChild;
            blockWrapper.classList.add("wagtail-fedit-initialized");
            this.wrapperElement.parentNode.insertBefore(blockWrapper, this.wrapperElement);
            this.wrapperElement.parentNode.removeChild(this.wrapperElement);
            blockWrapper.style.opacity = 0;
            this.wrapperElement = blockWrapper;
            this.init();

            const anim = blockWrapper.animate([
                {opacity: 0},
                {opacity: 1},
            ], {
                duration: 350,
                easing: "ease-in-out",
            });
            anim.onfinish = () => {
                blockWrapper.style.opacity = 1;
            };
        }
    }

    closeModal() {
        this.modalWrapper.remove();
        window.history.pushState(null, this.initialTitle, window.location.href.split("#")[0]);
        document.title = this.initialTitle;
    }

    get modalWrapper() {
        const modalWrapper = document.querySelector("#wagtail-fedit-modal-wrapper");
        if (modalWrapper) {
            return modalWrapper;
        }
        const wrapper = document.createElement("div");
        wrapper.id = "wagtail-fedit-modal-wrapper";
        wrapper.classList.add("wagtail-fedit-modal-wrapper");
        document.body.appendChild(wrapper);
        return wrapper;
    }

    get editUrl() {
        return this.wrapperElement.dataset.editUrl;
    }

    init() {
        console.log("before", this.sharedContext);
        this.sharedContext = this.wrapperElement.dataset.sharedContext;
        this.modalHtml = modalHtml.replace("__ID__", this.wrapperElement.dataset.id);
        this.editBtn = this.wrapperElement.querySelector(".wagtail-fedit-edit-button");

        console.log("after", this.sharedContext);

        const api = new WagtailFeditorAPI(this);
        const content = this.wrapperElementContent;
        this.wrapperElement.editorAPI = api;
        if (content) {
            content.editorAPI = api;
        }

        this.editBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            e.stopPropagation();
            await this.makeModal();
        });
    }

    initNewEditors() {
        const wagtailFeditBlockEditors = this.wrapperElement.querySelectorAll(".wagtail-fedit-adapter-wrapper");
        for (const editor of wagtailFeditBlockEditors) {
            if (!editor.classList.contains("wagtail-fedit-initialized")) {
                editor.classList.add("wagtail-fedit-initialized");
                new WagtailFeditEditor({element: editor});
            }
        }
    }
}

class WagtailFeditPublishMenu {
    constructor(publishButton) {
        this.publishButton = publishButton;
        this.publishButtonsWrapper = publishButton.parentElement.querySelector(".wagtail-fedit-form-buttons");
        const buttons = this.publishButtonsWrapper.querySelectorAll(".wagtail-fedit-userbar-button");
        let initialIsHidden = false;
        for (const button of buttons) {
            if (button.classList.contains("initially-hidden")) {
                initialIsHidden = true;
                break;
            }
        }

        if (initialIsHidden) {
            document.addEventListener("wagtail-fedit:change", (e) => {
                for (const button of buttons) {
                    if (button.classList.contains("initially-hidden")) {
                        button.classList.remove("initially-hidden");
                    }
                }
            })
        }

        this.init();
    }

    init() {
        this.publishButton.addEventListener("click", (e) => {
            if (this.publishButtonsWrapper.classList.contains("open")) {
                const anim = this.publishButtonsWrapper.animate([
                    {opacity: 1, height: `${this.publishButtonsWrapper.scrollHeight}px`},
                    {opacity: 0, height: "0px"},
                ], {
                    duration: 500,
                    easing: "ease-in-out",
                });
                anim.onfinish = () => {
                    this.publishButtonsWrapper.classList.remove("open");
                };
                return;
            }
            e.preventDefault();
            e.stopPropagation();
            const anim = this.publishButtonsWrapper.animate([
                {opacity: 0, height: "0px"},
                {opacity: 1, height: `${this.publishButtonsWrapper.scrollHeight}px`}
            ], {
                duration: 500,
                easing: "ease-in-out",
            });
            anim.onfinish = () => {
                this.publishButtonsWrapper.classList.add("open");
            };
        });
    }
}

function initFEditors() {
    const editors = document.querySelectorAll(".wagtail-fedit-adapter-wrapper");
    for (const editor of editors) {
        if (!editor.classList.contains("wagtail-fedit-initialized")) {
            editor.classList.add("wagtail-fedit-initialized");
            new WagtailFeditEditor({element: editor, type: "adapter"});
        }
    }
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === 1) {
                    if (node.classList.contains("wagtail-fedit-adapter-wrapper") && !node.classList.contains("wagtail-fedit-initialized")) {
                        node.classList.add("wagtail-fedit-initialized");
                        new WagtailFeditEditor({element: node});
                    }
                }
            }
        }
    });
    observer.observe(document.body, {childList: true, subtree: true});

    const url = new URL(window.location.href);
    const scrollY = url.searchParams.get("scrollY") || 0;
    const scrollX = url.searchParams.get("scrollX") || 0;
    if (scrollY > 0 || scrollX > 0) {
        window.scrollTo(scrollX, scrollY);
    }

    const userbar = document.querySelector("wagtail-userbar");
    if (userbar) {
        const editButton = userbar.shadowRoot.querySelector("#wagtail-fedit-editor-button");
        const liveButton = userbar.shadowRoot.querySelector("#wagtail-fedit-live-button");
        const publishMenu = userbar.shadowRoot.querySelector("#wagtail-fedit-publish-menu");

        function setScrollParams(button) {
            if (!button) {
                return;
            }
            const url = new URL(button.href);
            if (window.scrollY > 100) {
                url.searchParams.set("scrollY", window.scrollY);
            }
            if (window.scrollX > 100) {
                url.searchParams.set("scrollX", window.scrollX);
            }
            button.href = url.toString();
        }

        if (editButton || liveButton) {
            let timer = null;

            window.addEventListener("scroll", () => {
                if (timer) {
                    clearTimeout(timer);
                }
                timer = setTimeout(() => {
                    setScrollParams(editButton);
                    setScrollParams(liveButton);
    
                    const windowURL = new URL(window.location.href);
                    windowURL.searchParams.set("scrollY", window.scrollY);
                    windowURL.searchParams.set("scrollX", window.scrollX);
                    window.history.replaceState(null, "", windowURL.toString());
                }, 50);
            });
        }


        if (publishMenu) {
            const publisher = new WagtailFeditPublishMenu(publishMenu);
        }
    }
}

document.addEventListener("DOMContentLoaded", initFEditors);

