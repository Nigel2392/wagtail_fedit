from ..adapters import (
    FieldAdapter,
    BlockAdapter,
    adapter_registry,
)


adapter_registry.register(FieldAdapter)
adapter_registry.register(BlockAdapter)

