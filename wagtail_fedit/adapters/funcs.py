from django.utils.functional import classproperty
from .block import BlockAdapter
from .field import FieldAdapter
from itertools import chain


# https://stackoverflow.com/a/29088221/18020941
def dj_model_to_dict(instance):
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        data[f.name] = f.value_from_object(instance)
    for f in opts.many_to_many:
        data[f.name] = [i.id for i in f.value_from_object(instance)]
    return data


class FuncAdapterMixin:
    base_identifier = None
    base_required_kwargs = []
    js_constructor = "wagtail_fedit.editors.BaseFuncEditor"
    js_function = None

    @classproperty
    def identifier(cls):
        if not cls.base_identifier:
            raise NotImplementedError("base_identifier is required")
        
        return f"{cls.base_identifier}_func"
    
    def get_element_id_parts(self) -> list[str]:
        return super().get_element_id_parts() + [
            self.kwargs["target"],
        ]

    @classproperty
    def required_kwargs(cls):

        if cls.js_function:
            return cls.base_required_kwargs + [
                "target",
            ]

        return cls.base_required_kwargs + [
            "name",
            "target",
        ]

    def get_response_data(self, parent_context=None):
        data = super().get_response_data(parent_context)
        name = self.js_function or self.kwargs["name"]
        target = self.kwargs["target"]
        target = target.format(object=self.object)
        data["func"] = {
            "name": name,
            "target": target,
        }
        return data

class BaseFieldFuncAdapter(FuncAdapterMixin, FieldAdapter):
    base_identifier = FieldAdapter.identifier
    base_required_kwargs = FieldAdapter.required_kwargs

class BaseBlockFuncAdapter(FuncAdapterMixin, BlockAdapter):
    base_identifier = BlockAdapter.identifier
    required_kwargs = BlockAdapter.required_kwargs

    def get_response_data(self, parent_context=None):
        data = super().get_response_data(parent_context)
        data["block"] = self.block.get_prep_value()
        return data

