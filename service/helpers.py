from delb import TagNode
from typing import Dict
from snakesist.exist_client import Resource

from models import EntityMeta


def normalize_whitespace(value: str) -> str:
    """
    Remove unnecessary whitespace from string
    :param value: String to be processed
    :return: Normalized string
    """
    return ' '.join(value.split())


def apply_filter(value: TagNode, filter_name: str) -> str:
    """
    Apply a filter that makes changes to an XML node and outputs a value.
    :param value: XML node to be processed
    :param filter_name: Name of the filter function defined in filters.py
    :return: Processed output
    """
    from .filters import Functions as f
    try:
        filter_func = getattr(f, filter_name)
    except AttributeError:
        print(f"Filter is undefined: {filter_name}")
    return filter_func(value)


def process_property_value(node: TagNode, property_manifest: Dict) -> str:
    """
    Extract a property value from an XML node
    :param node: XML node as `delb.TagNode`
    :param property_manifest: Manifest snippet of the property
    :return:
    """
    output = None
    if 'attrib' in property_manifest:
        for val in property_manifest['attrib']:
            try:
                if "filter" in property_manifest:
                    output = apply_filter(node[val], property_manifest["filter"])
                else:
                    output = normalize_whitespace(node[val])
            except KeyError:
                continue
    else:
        if "filter" in property_manifest:
            output = apply_filter(node, property_manifest["filter"])
        else:
            output = normalize_whitespace(node.full_text)
    return output


def process_xpath_list(node, property_manifest: Dict):
    """
    Return a list of values as a result of running a list of XPath
    expressions against an input node
    :param node: Input node
    :param property_manifest: Manifest snippet of the property
    :return: List of values
    """
    def complement_xpath(current_node, path):
        """
        Return current node if XPath value is "."
        else process XPath normally
        """
        if path == ".":
            return [current_node]
        else:
            return current_node.xpath(path)

    if node:
        return [
            process_property_value(child_node, property_manifest)
            for path in property_manifest["xpath"]
            for child_node in complement_xpath(node, path)
        ]
    return []


def process_properties(property_manifest: Dict, parent_node) -> Dict:
    return {
        prop_name: process_property(prop_name, prop_items, parent_node)
        for prop_name, prop_items in property_manifest.items()
    }


def process_property(prop_name: str, property_manifest: Dict, parent_node):
    """
    Process node into dictionary according to property manifest
    :param prop_name: Name of the property
    :param property_manifest: Manifest snippet of the property
    :param parent_node: Node to be processed
    :return: Extracted values as dictionary
    """
    has_subprops = "properties" in property_manifest
    has_xpath = "xpath" in property_manifest
    has_multi = "multiple" in property_manifest
    if has_subprops:
        if has_multi and not has_xpath:
            return [
                process_properties(props, parent_node)
                for props in property_manifest["properties"]
            ]
        elif has_multi and has_xpath:
            return [
                process_properties(property_manifest["properties"], node)
                for path in property_manifest["xpath"]
                for node in parent_node.xpath(path)
            ]
        elif not has_multi and not has_xpath:
            return process_properties(property_manifest["properties"], parent_node)
        elif not has_multi and has_xpath:
            return [
                process_properties(property_manifest["properties"], node)
                for path in property_manifest["xpath"]
                for node in parent_node.xpath(path)
            ].pop()
    elif not has_subprops:
        assert has_xpath, f"XPath expression required for {prop_name}"
        if has_multi:
            return [
                node
                for node in process_xpath_list(parent_node, property_manifest)
            ]
        try:
            return process_xpath_list(parent_node, property_manifest)[0]
        except IndexError:
            return None


def xml_to_entitymeta(
        property_manifest: Dict,
        entity_name: str,
        db_resource: Resource,
        id_attrib: str
) -> EntityMeta:
    """
    Transform eXist resource into EntityMeta model
    :param property_manifest: Manifest snippet of the property
    :param entity_name: Name of the entity as configured in the manifest
    :param db_resource: Resource queried from the database
    :param id_attrib: Name of the XML attribute containing the entity ID
    :return:
    """
    properties = process_properties(property_manifest["properties"], db_resource.node)
    try:
        node_id = db_resource.node[id_attrib]
    except (KeyError, TypeError):
        print(f"Warning: No @xml:id found for '{entity_name}' item! Item endpoint will not be accessible.")
        node_id = ''
    return EntityMeta(
        id=node_id,
        entity=entity_name,
        properties=properties
    )
