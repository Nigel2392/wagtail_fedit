export {
    WagtailFeditPublishMenu,
}

class WagtailFeditPublishMenu {
    publishButton: HTMLElement;
    publishButtonsWrapper: HTMLElement;


    constructor(publishButton: HTMLElement) {
        this.publishButton = publishButton;
        this.publishButtonsWrapper = publishButton.parentElement.querySelector(".wagtail-fedit-form-buttons");
        const buttons = this.publishButtonsWrapper.querySelectorAll(".wagtail-fedit-userbar-button");
        
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
