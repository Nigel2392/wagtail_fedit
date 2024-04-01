from wagtail import blocks
from wagtail.blocks.list_block import ListValue
from wagtail.fields import StreamValue

def get_block_name(block):
    if isinstance(block, StreamValue.StreamChild):
        return block.block_type
    elif isinstance(block, ListValue.ListChild):
        return "item"
    elif isinstance(block, ListValue):
        return block.block.name
    elif isinstance(block, (blocks.StructValue, blocks.BoundBlock)):
        return block.block.name
    else:
        raise ValueError("Unknown block type: %s" % type(block))

def get_block_path(block):
    if isinstance(block, StreamValue.StreamChild):
        return block.id
    elif isinstance(block, ListValue.ListChild):
        return block.id
    elif isinstance(block, ListValue):
        return block.block.name
    elif isinstance(block, (blocks.StructValue, blocks.BoundBlock)):
        return block.block.name
    else:
        raise ValueError("Unknown block type: %s" % type(block))


def find_block(block_id, field, contentpath=None):
    if contentpath is None:
        contentpath = []

    # Check and cast field to iterable if necessary, but do not append non-StreamValue names to contentpath here.
    if not isinstance(field, StreamValue) and not hasattr(field, "__iter__"):
        field = [field]

    # Adjust for ListValue to get the iterable bound_blocks.
    if isinstance(field, ListValue):
        field = field.bound_blocks

    for block in field:
        # Determine the block's name only if needed to avoid premature addition to contentpath.
        block_name = get_block_path(block)
        
        if getattr(block, "id", None) == block_id:
            # Append the block name here as it directly leads to the target.
            return block, contentpath + [block_name]
        
        # Prepare to check children without altering the current path yet.
        if isinstance(block.value, blocks.StructValue):
            for _, value in block.value.bound_blocks.items():
                found, found_path = find_block(block_id, value, contentpath + [block_name])
                if found:
                    return found, found_path

        elif isinstance(block.value, (StreamValue, StreamValue.StreamChild, ListValue)):
            found, found_path = find_block(block_id, block.value, contentpath + [block_name])
            if found:
                return found, found_path

    # Return None and the current path if no block is found at this level.
    return None, contentpath


def can_fedit(block):
    """
        Check if a block is marked as non-editable on the frontend.
    """
    if isinstance(block, blocks.BoundBlock):
        return getattr(block.block.meta, "fedit", True)

    return getattr(block.meta, "fedit", True)


def value_for_form(block_value, block, value):
    if not block:
        return value
    
    if isinstance(value, blocks.BoundBlock):
        return value.value
    
    if hasattr(block, "fedit_value_for_form"):
        return block.fedit_value_for_form(value)
    
    if isinstance(block, blocks.StructBlock):
        for field_name, sub in block.child_blocks.items():
            if not value:
                continue
            block_value[field_name] = value_for_form(block_value[field_name], sub, value[field_name])
        return block_value
    
    if isinstance(block, blocks.FieldBlock):
        return block.value_from_form(value)
    
    return value


def get_initial_for_form(block_value, block, parent_structblock = False):
    if isinstance(block, (StreamValue.StreamChild, ListValue.ListChild, blocks.BoundBlock)):
        return get_initial_for_form(block.value, block.block)

    if hasattr(block, "fedit_initial_for_form"):
        return block.fedit_initial_for_form(block_value)

    if isinstance(block, (blocks.FieldBlock)) and not parent_structblock:
        return {"value": block_value}
    
    if isinstance(block, (blocks.StructBlock)):
        d = {}
        for key, value in block_value.items():
            if value and hasattr(value, "block"):
                d[key] = get_initial_for_form(value, value.block, parent_structblock=True)
            elif value:
                d[key] = value
            else:
                d[key] = None
        return d
    
    return block_value
