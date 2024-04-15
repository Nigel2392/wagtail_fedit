from typing import Type
from .base import BaseAdapter


class RegistryLookUpError(Exception):
    pass

class DuplicateAdapterError(Exception):
    pass

class AdapterSubclassError(TypeError):
    pass


class AdapterRegistry:
    def __init__(self):
        self.adapters: dict[str, Type[BaseAdapter]] = {}

    def __getitem__(self, identifier: str) -> Type[BaseAdapter]:
        try:
            return self.adapters[identifier]
        except KeyError:
            raise RegistryLookUpError(f"No adapter found with identifier '{identifier}'.")

    def register(self, adapter_class: Type[BaseAdapter]):
        if isinstance(adapter_class, BaseAdapter):
            raise AdapterSubclassError(f"{adapter_class.__class__.__name__} must be a subclass of BaseAdapter; got instance.")
        
        if adapter_class.identifier in self.adapters:
            raise DuplicateAdapterError(f"An adapter with identifier '{adapter_class.identifier}' is already registered.")

        self.adapters[adapter_class.identifier] = adapter_class

    def unregister(self, identifier):
        if identifier not in self.adapters:
            raise RegistryLookUpError(f"No adapter found with identifier '{identifier}'.")

        del self.adapters[identifier]


registry = AdapterRegistry()
