from ..adapters import (
    FieldAdapter,
    BlockAdapter,
    ModelAdapter,
    BackgroundImageFieldAdapter,
    adapter_registry,
)


adapter_registry.register(FieldAdapter)
adapter_registry.register(BlockAdapter)
adapter_registry.register(ModelAdapter)
adapter_registry.register(BackgroundImageFieldAdapter)

