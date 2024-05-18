export {
    iFrame,
    FrameOptions,
};

type FrameOptions = {
    id: string;
    className: string;
    srcdoc?: string;
    url?: string;
    autoResize?: boolean;
    executeOnloadImmediately?: boolean;
    onLoad?: NewFrameFunc;
    onError?: FrameFunc;
    onCancel?: FrameFunc;
};

type NewFrameFunc = (options: { newFrame: HTMLIFrameElement }) => void;
type FrameFunc = () => void;

interface iFrameWindow extends Window {
    initBlockWidget: (id: string) => void;
}

class iFrame {
    private url: string;
    private srcdoc: string;
    private iframe: HTMLIFrameElement;
    private id: string;
    private className: string;
    autoResize: boolean = true;
    executeOnloadImmediately: boolean = false;
    onLoad: NewFrameFunc;
    onError: FrameFunc;
    onCancel: FrameFunc;

    constructor(options: FrameOptions) {
        const {
            id,
            className,
            srcdoc = null,
            url = null,
            onLoad = () => {},
            onError = () => {},
            onCancel = () => {},
            autoResize = false,
            executeOnloadImmediately = false,
        } = options;


        this.url = url;
        this.srcdoc = srcdoc;
        this.iframe = null;
        this.id = id;
        this.className = className;
        this.autoResize = autoResize;
        this.executeOnloadImmediately = executeOnloadImmediately;
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

    get window(): iFrameWindow {
        return this.element.contentWindow as iFrameWindow;
    }

    get mainElement() {
        return this.document.querySelector("#main");
    }

    get formElement(): HTMLFormElement {
        return this.document.querySelector("#wagtail-fedit-form");
    }

    get formWrapper() {
        return this.document.querySelector(".wagtail-fedit-form-wrapper");
    }

    destroy() {
        this.iframe.remove();
    }

    update(url?: string, srcdoc?: string) {
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

    _renderFrame(url: string, srcDoc: string, onLoad: (options: { newFrame: HTMLIFrameElement }) => void, onError = () => {}) {
        const iframe = document.createElement('iframe');
        if (srcDoc) {
            iframe.srcdoc = srcDoc;
        } else {
            iframe.src = url;
        }
        iframe.id = this.id;
        iframe.className = this.className;
        let interval: NodeJS.Timeout;
        iframe.onload = () => {
            if (!this.formElement) {
                onError();
                return;
            }
            if (this.autoResize) {
                interval = setInterval(() => {
                    if (!this.formElement) {
                        clearInterval(interval);
                        return;
                    }
    
                    let height = this.formElement.scrollHeight;
                    iframe.style.height = `${height}px`;
                }, 10);
            }

            const cancelButton = this.document.querySelector(".wagtail-fedit-cancel-button");
            if (cancelButton) {
                cancelButton.addEventListener("click", () => {
                    clearInterval(interval);
                    this.onCancel();
                });
            }
            if (this.document.readyState === "complete" || this.executeOnloadImmediately) {
                onLoad({ newFrame: iframe });
            } else {
                iframe.contentWindow.addEventListener("DOMContentLoaded", () => {
                    onLoad({ newFrame: iframe });
                });
            }
        };
        iframe.onerror = () => {
            onError();
        };
        return iframe;
    }
}