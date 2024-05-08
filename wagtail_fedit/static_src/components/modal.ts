export {
    EditorModal,
    ModalOptions,
};

const modalIdentifier = "wagtail-fedit-modal";
const modalHtml = `
<div class="${modalIdentifier}-wrapper">
    <div class="${modalIdentifier}" id="${modalIdentifier}-__ID__-modal">
    </div>
</div>`


type ModalOptions = {
    modalId: string;

    onOpen?: () => void;
    onClose?: () => void;
}


class EditorModal {
    modalHtml: string;
    options: ModalOptions;

    constructor(options: ModalOptions) {
        this.options = options;
        this.modalHtml = modalHtml.replace("__ID__", this.options.modalId);
    }

    static get modalWrapper(): HTMLElement {
        var wrapper = document.querySelector(`#${modalIdentifier}-wrapper`);
        if (wrapper) {
            return wrapper as HTMLElement;
        }
        wrapper = document.createElement("div");
        wrapper.id = `${modalIdentifier}-wrapper`;
        wrapper.classList.add(`${modalIdentifier}-wrapper`);
        document.body.appendChild(wrapper);
        return wrapper as HTMLElement;
    }

    get wrapper(): HTMLElement {
        return (<typeof EditorModal>this.constructor).modalWrapper;
    }

    get modal(): HTMLElement {
        var modal = this.wrapper.querySelector(`.${modalIdentifier}`);

        if (modal && modal.id !== `${modalIdentifier}-${this.options.modalId}-modal`) {
            modal.remove();
            modal = null;
        }

        if (!modal) {
            modal = this.buildModal();
        }

        return modal as HTMLElement;
    }

    get innerHTML() {
        return this.modal.innerHTML;
    }

    set innerHTML(html: string) {
        this.modal.innerHTML = html;
    }

    get style() {
        return this.modal.style;
    }

    get classList() {
        return this.modal.classList;
    }

    get children() {
        return this.modal.children;
    }

    buildModal(): HTMLElement {
        var wrapper = this.wrapper;
        var modal = wrapper.querySelector(`.${modalIdentifier}`);
        if (!modal) {
            wrapper.innerHTML = this.modalHtml;
            modal = wrapper.querySelector(`.${modalIdentifier}`);
        }
        return modal as HTMLElement;
    }

    addClass(className: string) {
        this.modal.classList.add(className);
    }

    removeClass(className: string) {
        this.modal.classList.remove(className);
    }

    openModal() {
        this.wrapper.classList.add("open");

        if (this.options.onOpen) {
            this.options.onOpen();
        }
    }

    closeModal() {
        this.wrapper.classList.remove("open");
        this.wrapper.innerHTML = "";

        if (this.options.onClose) {
            this.options.onClose();
        }
    }

    appendChild(...children: HTMLElement[]) {
        if (children.length === 0) {
            return;
        }
        for (let i = 0; i < children.length; i++) {
            this.modal.appendChild(children[i]);
        }
    }

    removeChild(child: HTMLElement) {
        this.modal.removeChild(child);
    }

    dispatchEvent(event: string, options?: any) {
        if (!options) {
            options = {};
        }

        options.modal = this.modal;

        const customEvent = new CustomEvent(event, {
            detail: options,
        });

        this.modal.dispatchEvent(customEvent);
    }

    addEventListener(event: string, listener: EventListener) {
        this.modal.addEventListener(event, listener);
    }

    removeEventListener(event: string, listener: EventListener) {
        this.modal.removeEventListener(event, listener);
    }
}
