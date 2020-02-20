# :coding: utf-8
# :copyright: Copyright (c) 2018 ilp
import collections


def elementtree_to_dict(element):
    node = collections.OrderedDict()

    node.update(element.items())

    child_nodes = {}
    for child in element:
        child_nodes.setdefault(child.tag, []).append(elementtree_to_dict(child))

    for key, value in child_nodes.items():
        if len(value) == 1:
            child_nodes[key] = value[0]

    if element.text:
        node["_value"] = element.text

    node.update(child_nodes.items())

    return node
