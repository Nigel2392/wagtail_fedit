/**
 * @callback EditorAPIFunc
 * @param {WagtailFeditorAPI} api
 * @returns {void}
 * 
 * @callback StringFunc
 * @param {string} html
 * @returns {HTMLElement}
 * 
 * @callback UpdateFunc
 * @param {StringFunc} html
 * 
 * @typedef {Object} ResponseObject
 * @property {boolean} success
 * @property {string|null} html
 * 
 * @typedef {Object} FuncResponseObject
 * @property {boolean} success
 * @property {string|null} html
 * @property {Object} func
 * @property {string} func.name
 * @property {string} func.target
 * 
 * @typedef {Function} EditorCallback
 * @param {HTMLElement} element
 * @param {ResponseObject} response
 * @returns {Promise<any>|void}
*/


class iFrame {
    /**
     * @param {Object} options
     * @param {string} options.id
     * @param {string} options.className
     * @param {string} [options.srcdoc=null]
     * @param {string} [options.url=null]
     * @param {Function} [options.onLoad=() => {}]
     * @param {Function} [options.onError=() => {}]
     * @param {Function} [options.onCancel=() => {}]
     */
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

    /**
     * @returns {HTMLIFrameElement}
     */
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


class Tooltip {
    /**
     * @param {HTMLElement} element
     **/
    constructor(element) {
        this.element = element;
        this.tooltipConfig = this.makeConfig();
        this.init();
    }

    init() {
        if (!window.tippy) {
            console.debug("Tippy tooltips disabled");
            return;
        }
        tippy(this.element, this.tooltipConfig);
    }

    makeConfig() {
        const cfg = {}
        for (const attr of this.element.attributes) {
            if (attr.name.startsWith("data-tooltip-")) {
                const key = attr.name.replace("data-tooltip-", "");
                cfg[key] = attr.value;
            }
        }
        this.tooltipConfig = cfg;
        return cfg;
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

    dispatchEvent(name, detail = null) {
        this.#editor.dispatchEvent(name, detail);
    }

    addEventListener(name, callback) {
        this.#editor.addEventListener(name, callback);
    }

    removeEventListener(name, callback, options=null) {
        this.#editor.removeEventListener(name, callback, options);
    }

    /**
     * @param {string|UpdateFunc} html
     * @returns {Promise<HTMLElement>}
     **/
    updateHtml(html) {
        return new Promise((resolve, reject) => {
            const update = (innerHtml) => {
                const blockWrapper = this.#editor.wrapperElement;
                const element = document.createElement("div");
                element.innerHTML = innerHtml;
                const newBlockWrapper = element.firstElementChild;
                newBlockWrapper.classList.add("wagtail-fedit-initialized");
                blockWrapper.parentNode.insertBefore(newBlockWrapper, blockWrapper);
                blockWrapper.parentNode.removeChild(blockWrapper);
                this.#editor.wrapperElement = newBlockWrapper;
                this.#editor.initNewEditors();
                this.#editor.init();

                resolve(newBlockWrapper);

                return blockWrapper;
            }

            if (typeof html === "string") {
                update(html);
                return;
            }

            if (typeof html === "function") {
                this.#editor.wrapperElement.editorAPI = this;
                html(update);
                return;
            }
        });
    }

    /**
     * @returns {Promise<any>}
     **/
    refetch() {
        return this.#editor.refetch();
    }

    /**
     * @param {EditorAPIFunc} func
     * @returns {void}
     **/
    execRelated(func) {
        for (const wrapper of this.#editor.relatedWrappers) {
            func(wrapper.editorAPI);
        }
    }
}


class BaseWagtailFeditEditor extends EventTarget {
    /**
     * @param {HTMLElement} element
     */
    constructor(element) {
        super();

        /**@type {string} */
        this.initialTitle = document.title;
        
        /**@type {HTMLElement} */
        this.wrapperElement = element;

        /**@type {WagtailFeditorAPI} */
        this.api = new WagtailFeditorAPI(this);

        /**@type {string} */
        this.sharedContext = null;

        /**@type {string} */
        this.modalHtml = null;

        /**@type {HTMLElement} */
        this.editBtn = null;
        this.init();

        /**@type {iFrame} */
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

    get relatedWrappers() {
        const wrapperId = this.wrapperElement.dataset.wrapperId;
        const filterFn = (el) => el !== this.wrapperElement
        const elements = document.querySelectorAll(`[data-wrapper-id="${wrapperId}"]`)
        return Array.from(elements).filter(filterFn);
    }

    get modalWrapper() {
        const modalWrapper = document.querySelector("#wagtail-fedit-modal-wrapper");
        if (modalWrapper) {
            return modalWrapper;
        }
        const wrapper = document.createElement("div");
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
                response = response.json();
                return response;
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

    /**
     * @param {ResponseObject} response
     * @returns {Promise<any>|void}
     */
    onResponse(response) {
    
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
                const onSubmit = (e) => {
                    e.preventDefault();
                    const formData = new FormData(this.iframe.formElement);

                    this.dispatchEvent(window.wagtailFedit.EVENTS.SUBMIT, {
                        element: this.wrapperElement,
                        formData: formData,
                    });

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
                            this.iframe.onCancel = this.closeModal.bind(this);
                            this.dispatchEvent(window.wagtailFedit.EVENTS.SUBMIT_ERROR, {
                                element: this.wrapperElement,
                                response: response,
                            });
                            return;
                        }
                        const ret = this.onResponse(response);
                        const success = () => {
                            this.closeModal();
                            this.dispatchEvent(window.wagtailFedit.EVENTS.CHANGE, {
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

                this.dispatchEvent(window.wagtailFedit.EVENTS.MODAL_LOAD, {
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
        this.dispatchEvent(window.wagtailFedit.EVENTS.MODAL_OPEN, {
            iframe: this.iframe,
            modal: this.modal,
        });
    }

    closeModal() {
        this.modalWrapper.remove();
        window.history.pushState(null, this.initialTitle, window.location.href.split("#")[0]);
        document.title = this.initialTitle;
        this.dispatchEvent(window.wagtailFedit.EVENTS.MODAL_CLOSE);
    }

    dispatchEvent(name, detail = null) {
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

function initNewEditors(wrapper = document) {
    let wagtailFeditBlockEditors;
    if (
        wrapper != document
        && wrapper.classList.contains("wagtail-fedit-adapter-wrapper")
        && !wrapper.classList.contains("wagtail-fedit-initialized")
    ) {
        wagtailFeditBlockEditors = [wrapper];
    } else {
        wagtailFeditBlockEditors = wrapper.querySelectorAll(".wagtail-fedit-adapter-wrapper");
    }
    for (const editor of wagtailFeditBlockEditors) {
        if (!editor.classList.contains("wagtail-fedit-initialized")) {
            editor.classList.add("wagtail-fedit-initialized");
            const editorClass = getEditorClass(editor);
            if (editorClass) {
                new editorClass(editor);
            } else {
                console.error("No editor class found for element", editor);
            }
        }

        const editButtons = wrapper.querySelectorAll("[data-tooltip='true']");
        for (const button of editButtons) {
            if (button.dataset.tooltip == "true") {
                new Tooltip(button);
                delete button.dataset.tooltip;
            }
        }
    }
}

class BaseFuncEditor extends BaseWagtailFeditEditor {
    static get funcMap() {
        return window
    }

    /**
     * @param {FuncResponseObject} response
     * @returns {Promise<any>|void}
     * @override
     **/
    onResponse(response) {
        const name = response.func.name;
        const targetElementSelector = response.func.target;
        if (!name || !targetElementSelector) {
            console.error("Invalid response", response);
            return;
        }

        const targetElement = document.querySelector(targetElementSelector);
        if (!targetElement) {
            console.error("Target element not found", targetElementSelector);
            return;
        }

        const func = this.constructor.funcMap[name];
        if (!func) {
            console.error("Function not found", name);
            return;
        }

        return func(targetElement, response);
    }
}


class WagtailFeditFuncEditor extends BaseFuncEditor {
    static get funcMap() {
        return window.wagtailFedit.funcs;
    }
}


class BlockFieldEditor extends BaseWagtailFeditEditor {
    /**
     * @param {ResponseObject} response
     * @returns {Promise<any>|void}
     * @override
     **/
    onResponse(response) {
        return this.api.updateHtml((update) => {
            // Fade out the old block
            const anim = this.wrapperElement.animate([
               {opacity: 1},
               {opacity: 0},
            ], {
               duration: 350,
               easing: "ease-in-out",
            });
        
            anim.onfinish = () => {

                const blockWrapper = update(response.html);
                
                if (!response.refetch) {
                    this.api.execRelated((relatedAPI) => {
                        relatedAPI.refetch();
                    });
                }
    
                // Fade in the new block
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
        });
    }
}


class WagtailFeditPublishMenu {
    constructor(publishButton) {
        /**@type {HTMLElement} */
        this.publishButton = publishButton;
        /**@type {HTMLElement} */
        this.publishButtonsWrapper = publishButton.parentElement.querySelector(".wagtail-fedit-form-buttons");
        /**@type {NodeList} */
        const buttons = this.publishButtonsWrapper.querySelectorAll(".wagtail-fedit-userbar-button");
        let initialIsHidden = false;
        for (const button of buttons) {
            if (button.classList.contains("initially-hidden")) {
                initialIsHidden = true;
                break;
            }
        }

        if (initialIsHidden) {
            document.addEventListener(window.wagtailFedit.EVENTS.CHANGE, () => {
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


function getEditorClass(element) {
    const editorClass = element.dataset.feditConstructor;
    if (editorClass) {
        return window.wagtailFedit.editors[editorClass];
    }
    return null;
}


function initFEditors() {
    initNewEditors()
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === 1) {
                    initNewEditors(node);
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
            new WagtailFeditPublishMenu(publishMenu);
        }
    }
}

/**
 * @satisfies {EditorCallback}
 * @param {HTMLElement} element
 * @param {ResponseObject} response
 * @returns {void}
 */
function wagtailFeditBackgroundImageAdapter(element, response) {
    const url = response.url;
    const cssVar = response.css_variable_name;
    if (cssVar) {
        if (cssVar.startsWith("--")) {
            element.style.setProperty(cssVar, `url(${url})`);
        } else {
            element.style.setProperty(cssVar, `url(${url})`);
        }
    } else {
        element.style.backgroundImage = `url(${url})`;
    }
}


document.addEventListener("DOMContentLoaded", initFEditors);

window.wagtailFedit = {
    NAMESPACE: "wagtail-fedit",
    EVENTS: {
        SUBMIT: "wagtail-fedit:submit",
        CHANGE: "wagtail-fedit:change",
        MODAL_OPEN: "wagtail-fedit:modalOpen",
        MODAL_LOAD: "wagtail-fedit:modalLoad",
        MODAL_CLOSE: "wagtail-fedit:modalClose",
        SUBMIT_ERROR: "wagtail-fedit:submitError",
    },
    exports: {
        initFEditors,
        BaseWagtailFeditEditor,
        BaseFuncEditor,
        BlockFieldEditor,
        WagtailFeditPublishMenu,
        WagtailFeditorAPI,
        iFrame,
        Tooltip,
    },
    /**
     * @type {Object<string, BaseWagtailFeditEditor>}
     **/
    editors: {
        "wagtail_fedit.editors.BaseFuncEditor":   BaseFuncEditor,
        "wagtail_fedit.editors.BlockFieldEditor": BlockFieldEditor,
        "wagtail_fedit.editors.WagtailFeditFuncEditor": WagtailFeditFuncEditor,
    },
    /**
     * @type {Object<string, EditorCallback>}
     */
    funcs: {
        "wagtail_fedit.funcs.backgroundImageFunc": wagtailFeditBackgroundImageAdapter,
    },
    /**
     * @param {string} name
     * @param {BaseWagtailFeditEditor} editor
     */
    register: function (name, editor) {
        this.editors[name] = editor;
    },

    /**
     * @param {string} name
     * @param {EditorCallback} func
     */
    registerFunc: function (name, func) {
        this.funcs[name] = func;
    },
};
