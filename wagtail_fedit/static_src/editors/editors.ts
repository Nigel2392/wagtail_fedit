import { BaseWagtailFeditEditor, ResponseObject } from "./base/base";

export {
    BaseFuncEditor,
    WagtailFeditFuncEditor,
    BlockFieldEditor,
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
