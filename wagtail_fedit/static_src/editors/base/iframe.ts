export {
    iFrame,
    FrameOptions,
};

type FrameOptions = {
    id: string;
    className: string;
    srcdoc?: string;
    url?: string;
    executeOnloadImmediately?: boolean;
    onLoad?: NewFrameFunc;
    onError?: FrameFunc;
    onCancel?: FrameFunc;
    onResize?: (h: number) => void;
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
    private resizeInterval: NodeJS.Timeout;
    executeOnloadImmediately: boolean = false;
    onLoad: NewFrameFunc;
    onError: FrameFunc;
    onCancel: FrameFunc;
    onResize: (oldH: number, newH: number) => void;

    constructor(options: FrameOptions) {
        const {
            id,
            className,
            srcdoc = null,
            url = null,
            onLoad = () => {},
            onError = () => {},
            onCancel = () => {},
            onResize = () => {},
            executeOnloadImmediately = false,
        } = options;


        this.url = url;
        this.srcdoc = srcdoc;
        this.iframe = null;
        this.id = id;
        this.className = className;
        this.onResize = onResize;
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
        if (!this.window) {
            return null;
        }
        return this.window.document;
    }

    get window(): iFrameWindow {
        return this.element.contentWindow as iFrameWindow;
    }

    get mainElement() {
        return this.document?.querySelector("#main");
    }

    get formElement(): HTMLFormElement {
        return this.document?.querySelector("#wagtail-fedit-form");
    }

    get formWrapper() {
        return this.document?.querySelector(".wagtail-fedit-form-wrapper");
    }

    destroy() {
        this.iframe.remove();
        if (this.resizeInterval) {
            clearInterval(this.resizeInterval);
            delete this.resizeInterval;
        }
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
        iframe.onload = () => {
            if (!this.formElement) {
                onError();
                return;
            }
            
            let formElement = this.formElement;
            let lastHeight = formElement.scrollHeight;
            if (this.onResize) {
                this.onResize(0, lastHeight);
            }

            if (this.resizeInterval) {
                clearInterval(this.resizeInterval);
            }

            if (this.onResize) {
                this.resizeInterval = setInterval(() => {
                    if (!formElement) {
                        clearInterval(this.resizeInterval);
                        return;
                    }
                    try {
                        if (lastHeight !== formElement.scrollHeight) {
                            this.onResize(lastHeight, formElement.scrollHeight);
                            lastHeight = formElement.scrollHeight;
                        }
                    } catch (e) {
                        clearInterval(this.resizeInterval);
                        console.error(e);
                        onError();
                    }
                }, 25);
            }

            const cancelButton = this.document.querySelector(".wagtail-fedit-cancel-button");
            if (cancelButton) {
                cancelButton.addEventListener("click", () => {
                    clearInterval(this.resizeInterval);
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