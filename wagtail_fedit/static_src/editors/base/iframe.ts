export {
    iFrame,
    FrameOptions,
};

type FrameOptions = {
    id: string;
    className: string;
    srcdoc?: string;
    url?: string;
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