export {
    BaseIFrame,
    FormIFrame,
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
    onResize?: (oldH: number, newH: number) => void;
};

type NewFrameFunc = (options: { newFrame: HTMLIFrameElement }) => void;
type FrameFunc = () => void;

interface iFrameWindow extends Window {
    initBlockWidget: (id: string) => void;
}

class BaseIFrame {
    url: string;
    srcdoc: string;
    iframe: HTMLIFrameElement;
    id: string;
    className: string;
    resizeInterval: NodeJS.Timeout;
    executeOnloadImmediately: boolean = false;
    onLoad: NewFrameFunc;
    onError: FrameFunc;
    onCancel: FrameFunc;
    onResize: (oldH: number, newH: number) => void;

    constructor(options: FrameOptions) {

        this.url = options.url;
        this.srcdoc = options.srcdoc;
        this.iframe = null;
        this.id = options.id;
        this.className = options.className;
        this.onResize = options.onResize;
        this.executeOnloadImmediately = options.executeOnloadImmediately;
        this.onLoad = options.onLoad;
        this.onError = options.onError;
        this.onCancel = options.onCancel;
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
        return this.element?.contentWindow as iFrameWindow;
    }

    get mainElement() {
        return this.document?.querySelector("#main");
    }

    get scrollableElement() {
        return this.document.body;
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
            if (!this.scrollableElement) {
                onError();
                return;
            }
            
            let scrollableElement = this.scrollableElement;
            let lastHeight = scrollableElement.scrollHeight;
            if (this.onResize) {
                this.onResize(0, lastHeight);
            }

            if (this.resizeInterval) {
                clearInterval(this.resizeInterval);
            }

            if (this.onResize) {
                this.resizeInterval = setInterval(() => {
                    if (!scrollableElement) {
                        clearInterval(this.resizeInterval);
                        return;
                    }
                    try {
                        if (lastHeight !== scrollableElement.scrollHeight) {
                            this.onResize(lastHeight, scrollableElement.scrollHeight);
                            lastHeight = scrollableElement.scrollHeight;
                        }
                    } catch (e) {
                        clearInterval(this.resizeInterval);
                        console.error(e);
                        onError();
                    }
                }, 25);
            }

            this._onLoad(iframe);
            
            if (!onLoad) {
                return;
            }

            if (this.executeOnloadImmediately || this.document.readyState === "complete") {
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

    _onLoad(iframe: HTMLIFrameElement) {

    }
}

class FormIFrame extends BaseIFrame {
    get scrollableElement() {
        return this.document.querySelector(".wagtail-fedit-form-wrapper") as HTMLElement;
    }

    get formElement(): HTMLFormElement {
        return this.document?.querySelector("#wagtail-fedit-form");
    }

    get formWrapper() {
        return this.document?.querySelector(".wagtail-fedit-form-wrapper");
    }

    _onLoad(iframe: HTMLIFrameElement) {
        super._onLoad(iframe);
        
        const cancelButton = this.document.querySelector(".wagtail-fedit-cancel-button");
        if (cancelButton) {
            cancelButton.addEventListener("click", () => {
                clearInterval(this.resizeInterval);
                if (this.onCancel) {
                    this.onCancel();
                }
            });
        }
    }
}