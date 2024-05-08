import { EditorModal, ModalElement, modalIdentifier } from "../components/modal";


describe("EditorModal", () => {
    let modal: EditorModal;
    let modalOpened: boolean;
    let modalClosed: boolean;
    let modalDestroyed: boolean;

    beforeEach(() => {
        modal = new EditorModal({
            modalId: "test-modal",
            onClose: () => { modalClosed = true; },
            onOpen: () => { modalOpened = true; },
            onDestroy: () => { modalDestroyed = true; },
        });
    });

    afterEach(() => {
        modal.destroy();
    });

    it("should create a modal", () => {
        expect(document.querySelector(`.${modalIdentifier}-wrapper`)).toBe(null);
        expect(document.querySelector(`.${modalIdentifier}`)).toBe(null);

        modal.buildModal();
        modal.openModal();

        expect(document.querySelector(`.${modalIdentifier}-wrapper`)).toBeInstanceOf(HTMLElement);
        expect(document.querySelector(`.${modalIdentifier}`)).toBeInstanceOf(HTMLElement);

        expect(modal.wrapper).toBeInstanceOf(HTMLElement);
        expect(modal.modal).toBeInstanceOf(HTMLElement);
    });

    it("should add a class to the modal", () => {
        modal.openModal();
        modal.addClass("test-class");
        expect(modal.modal.classList.contains("test-class")).toBe(true);
    });

    it("should remove a class from the modal", () => {
        modal.buildModal();
        modal.openModal();
        modal.addClass("test-class");
        modal.removeClass("test-class");
        expect(modal.modal.classList.contains("test-class")).toBe(false);
    });

    it("should open the modal", () => {
        modal.buildModal();
        modal.openModal();
        expect(modal.wrapper.classList.contains("open")).toBe(true);
        expect(modalOpened).toBe(true);
        const elem = document.querySelector(`.${modalIdentifier}`);
        expect(elem).toBeInstanceOf(HTMLElement);
    });

    it("should close the modal", () => {
        let elem = document.querySelector(`.${modalIdentifier}`) as ModalElement;

        if (elem) {
            fail("Modal element should not exist yet");
        }
        
        modal.buildModal();
        modal.openModal();
        elem = document.querySelector(`.${modalIdentifier}`) as ModalElement;
        expect(elem).toBeInstanceOf(HTMLElement);

        elem.modal.closeModal();

        expect(modal.wrapper.classList.contains("open")).toBe(false);
        expect(modalClosed).toBe(true);
    });

    it("should destroy the modal", () => {
        let elem = document.querySelector(`.${modalIdentifier}`) as ModalElement;

        if (elem) {
            fail("Modal element should not exist yet");
        }

        modal.buildModal();
        modal.openModal();
        elem = document.querySelector(`.${modalIdentifier}`) as ModalElement;
        expect(elem).toBeInstanceOf(HTMLElement);

        modal.destroy();

        elem = document.querySelector(`.${modalIdentifier}`) as ModalElement;
        expect(elem).toBe(null);
        expect(modalDestroyed).toBe(true);
    });

});
