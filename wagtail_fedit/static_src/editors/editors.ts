import { EditorModal } from "../components/modal";
import { FormIFrame } from "../global";
import { BaseWagtailFeditEditor, ResponseObject, WrapperElement, newCloseButton } from "./base/base";
import { initNewEditors, refreshPage } from "./base/init";

export {
    BaseFuncEditor,
    WagtailFeditFuncEditor,
    FieldEditor,
    BlockEditor,
    DomPositionedFieldEditor,
    DomPositionedBlockEditor,
    backgroundImageAdapter,
};

type FuncResponseObject = ResponseObject & {
    func: {
        name: string;
        target: string;
    };
};

type BackgroundImageResponse = FuncResponseObject & {
    url: string;
    css_variable_name: string;
};
    


class BaseFuncEditor extends BaseWagtailFeditEditor {

    static get funcMap() {
        return window as any;
    }

    onResponse(response: FuncResponseObject) {
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

        const func = (<typeof BaseFuncEditor>this.constructor).funcMap[name];
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


class FieldEditor extends BaseWagtailFeditEditor {
    onResponse(response: ResponseObject) {
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
                    blockWrapper.style.opacity = "1";
                };
            }
        });
    }
}


type Constructor<T = BaseWagtailFeditEditor> = new (...args: any[]) => T;


function MovableMixin<T extends Constructor>(base: T) {
    return class extends base {
        constructor(...args: any[]) {
            super(...args);
            
            let directionButtons = this.wrapperElement.querySelectorAll("[data-direction]");
            for (let i = 0; i < directionButtons.length; i++) {
                let button = directionButtons[i] as HTMLElement;
                let url = button.dataset.url;
                button.addEventListener("click", (e) => {
                    
                    e.preventDefault();
                    
                    this.api.fetch(url, "POST", {}).then((response: any) => {
                        if (response.success) {
                            this.refetchParent(refreshPage);
                        } else {
                            response.error ? alert("Failed to move block: " + response.error) : alert("Failed to move block");
                        }
                    }).catch((error: any) => {
                        console.error("Failed to move block", error);
                        alert("Failed to move block");
                    });
                });
            }
        }
    }
}


function AddableMixin<T extends Constructor>(base: T) {
    return class extends base {
        constructor(...args: any[]) {
            super(...args);
            
            let addButton = this.wrapperElement.querySelector("[data-add]") as HTMLElement;
            if (!addButton) {
                console.error("\"Add\" button not found, cannot further initialize AddableMixin");
                return;
            }

            const url = addButton.dataset.url;
            const addModal = new EditorModal({
                modalId: `${this.wrapperElement.id}-modal`,
            });
            addButton.addEventListener("click", (e) => {
                e.preventDefault();
                addModal.openModal();
                const addiFrame = new FormIFrame({
                   id: "wagtail-fedit-iframe",
                   className: null,
                   url: url,
                   onLoad: ({ newFrame: HTMLIFrameElement }) => {

                        addiFrame.formElement.onsubmit = (e) => {
                            e.preventDefault();

                            const formData = new FormData(addiFrame.formElement);
                            this.api.fetch(url, "POST", formData).then((response: any) => {
                                if (response.success) {
                                    addModal.closeModal();
                                    this.refetchParent(refreshPage);
                                } else {
                                    response.error ? alert("Failed to add block: " + response.error) : alert("Failed to add block");
                                }
                            }).catch((error: any) => {
                                console.error("Failed to add block", error);
                                alert("Failed to add block");
                            });
                        };
                    }
                });
    
                addiFrame.destroy();
                addModal.appendChild(addiFrame.element);

                addModal.appendChild(
                    newCloseButton(
                        addModal.closeModal.bind(addModal)
                    )
                );

            });
        }
    }
}


class BlockEditor extends AddableMixin(MovableMixin(FieldEditor)) {

}


class DomPositionedFieldEditor extends FieldEditor {
    get buttonsElement() {
        let elem = this.wrapperElement.querySelector(".wagtail-fedit-buttons")
        return elem  as HTMLElement
    }

    get formElement() {
        let elem = this.wrapperElement.querySelector(".wagtail-fedit-adapter-form")
        return elem  as HTMLElement
    }

    get contentElement() {
        let elem = this.wrapperElement.querySelector(".wagtail-fedit-adapter-content")
        return elem  as HTMLElement
    }
    
    get frameOptions() {
        return {
            onResize: (oldHeight: number, newHeight: number) => {
                this.iframe.element.style.height = `${newHeight}px`;
            },
        }
    }

    openEditor() {
        this.openIframe(this.formElement, (iframe) => {
            this.contentElement.style.display = "none";
        });
    }

    closeEditor() {
        this.opened = false;
        window.history.pushState(null, this.initialTitle, window.location.href.split("#")[0]);
        document.title = this.initialTitle;
        this.contentElement.style.display = "block";
        this.iframe.destroy();
        this.executeEvent(window.wagtailFedit.EVENTS.EDITOR_CLOSE);
        delete this.iframe;
    }
}

class DomPositionedBlockEditor extends AddableMixin(MovableMixin(DomPositionedFieldEditor)) {

}


function backgroundImageAdapter(element: HTMLElement, response: BackgroundImageResponse) {
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
