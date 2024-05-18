import { BaseWagtailFeditEditor, ResponseObject } from "./base/base";

export {
    BaseFuncEditor,
    WagtailFeditFuncEditor,
    BlockFieldEditor,
    DomPositionedBlockFieldEditor,
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


class BlockFieldEditor extends BaseWagtailFeditEditor {
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

class DomPositionedBlockFieldEditor extends BlockFieldEditor {
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
    
    get autoResize() {
        return true
    }

    openEditor() {
        this.openIframe(this.formElement, (iframe) => {
            this.contentElement.style.display = "none";
            this.addEventListener((window.wagtailFedit.EVENTS.EDITOR_LOAD), (event) => {
                let height = this.iframe.formElement.clientHeight;
                this.iframe.element.style.height = `${height}px`;
            });
        });
    }

    closeEditor() {
        this.opened = false;
        window.history.pushState(null, this.initialTitle, window.location.href.split("#")[0]);
        document.title = this.initialTitle;
        this.contentElement.style.display = "block";
        this.iframe.destroy();
        delete this.iframe;
        this.executeEvent(window.wagtailFedit.EVENTS.EDITOR_CLOSE);
    }
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
