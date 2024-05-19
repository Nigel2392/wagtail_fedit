from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .adapters.base import BaseAdapter


class RegistryLookUpError(Exception):
    pass

class DuplicateAdapterError(Exception):
    pass


class AdapterRegistry:
    def __init__(self):
        self.adapters: dict[str, Type["BaseAdapter"]] = {}

    def __getitem__(self, identifier: str) -> Type["BaseAdapter"]:
        """
        Retrieve an adapter by its identifier or raise a RegistryLookUpError if not found.
        """
        try:
            return self.adapters[identifier]
        except KeyError:
            raise RegistryLookUpError(f"No adapter found with identifier '{identifier}'.")

    def register(self, adapter_class: Type["BaseAdapter"]):
        """
        Register an adapter class with the registry.
        """
        if adapter_class.identifier in self.adapters:
            raise DuplicateAdapterError(f"An adapter with identifier '{adapter_class.identifier}' is already registered.")

        self.adapters[adapter_class.identifier] = adapter_class

        adapter_class.on_register(self)

    def unregister(self, identifier):
        """
        Unregister an adapter by its identifier.
        """
        if identifier not in self.adapters:
            raise RegistryLookUpError(f"No adapter found with identifier '{identifier}'.")

        del self.adapters[identifier]


registry = AdapterRegistry()
