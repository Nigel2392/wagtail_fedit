import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css'; // optional for styling

export { Tooltip };

class Tooltip {
    element: HTMLElement;
    tooltipConfig: Object;

    constructor(element: HTMLElement) {
        this.element = element;
        this.tooltipConfig = this.makeConfig();
        this.init();
    }

    init() {
        tippy(this.element, this.tooltipConfig);
    }

    makeConfig() {
        const cfg: any = {
            content: this.element.getAttribute("title"),
        };
        for (let i = 0; i < this.element.attributes.length; i++) {
            const attr = this.element.attributes[i];
            if (attr.name.startsWith("data-tooltip-")) {
                const key = attr.name.replace("data-tooltip-", "");
                cfg[key] = attr.value;
            }
        }
        this.tooltipConfig = cfg;
        return cfg;
    }
}
