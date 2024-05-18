from ..adapters import (
    FieldAdapter,
    DomPositionedFieldAdapter,
    BlockAdapter,
    DomPositionedBlockAdapter,
    ModelAdapter,
    BackgroundImageFieldAdapter,
    adapter_registry,
)


adapter_registry.register(FieldAdapter)
adapter_registry.register(DomPositionedFieldAdapter)
adapter_registry.register(BlockAdapter)
adapter_registry.register(DomPositionedBlockAdapter)
adapter_registry.register(ModelAdapter)
adapter_registry.register(BackgroundImageFieldAdapter)

