import yaml
import time
import xmltodict
import threading
import schedule
from delb import TagNode
from datetime import datetime
from typing import Dict, List
from .model import EntityMeta
from snakesist.exist_client import ExistClient, Resource

ID_ATTR_NAME = '{http://www.w3.org/XML/1998/namespace}id'

with open('config.yml', 'r') as config_file:
    CFG = yaml.load(config_file, Loader=yaml.FullLoader)

ENTITY_NAMES = list(CFG['entities'])

db = ExistClient()
db.root_collection = CFG['collection']

entities = {
    name: db.retrieve_resources(manifest["xpath"])
    for name, manifest in CFG["entities"].items()
}


class UpdateWatcher:
    def __init__(self):
        self.last_checked = datetime.now().isoformat(timespec="seconds")
    
    def _reset_timestamp(self):
        self.last_checked = datetime.now().isoformat(timespec="seconds")

    def _updated_resources(self) -> List:
        updated_resources = db.retrieve_resources(
            f"""xmldb:find-last-modified-since(
            collection('{db.root_collection}'), 
            xs:dateTime('{self.last_checked}'))"""
        )
        self._reset_timestamp()
        return [res.abs_resource_id for res in updated_resources]
 
    def update_resources(self):
        """
        Check and update resources if necessary
        """
        while True:
            updated = self._updated_resources()
            if updated:
                [
                    resource.update_pull() 
                    for name, resource_list in entities.items()
                    for resource in resource_list
                    if resource.abs_resource_id in updated
                ]
            time.sleep(2)
    
    def watch_resources(self):
        thread = threading.Thread(target=self.update_resources)
        thread.daemon = True
        thread.start()


def normalize_whitespace(input: str) -> str:
    """
    Remove unnecessary whitespace from string
    """

    return ' '.join(input.split())


def apply_filter(value: str, filter_name: str) -> str:
    """
    Apply a filter to a string value
    """
    from .filters import Functions as f
    try:
        filter = getattr(f, filter_name)
        value = filter(value)
    except AttributeError:
        print(f"Filter is undefined: {filter_name}")
    finally:
        return value



def process_property_value(node: TagNode, prop: Dict) -> str:
    """
    Extract a property value from an XML node
    """
    output = None
    if 'attrib' in prop:
        for val in prop['attrib']:
            try:
                output = normalize_whitespace(node[val])
            except KeyError:
                continue
    else:
        output = normalize_whitespace(node.full_text)
    if "filter" in prop:
        output = apply_filter(output, prop["filter"])
    return output
    

def process_properties(manifest: Dict, parent_node) -> Dict:
    output = {}
    for prop_name, prop_items in manifest.items():
        prop_node = None
        output[prop_name] = None
        try:
            xpaths = prop_items["xpath"]
        except KeyError:
            xpaths = []
        for path in xpaths:
            try:
                prop_nodes = parent_node.xpath(path)
                if prop_nodes and "multiple" in prop_items:
                    values = []
                    for prop_node in prop_nodes:
                        value = process_property_value(prop_node, prop_items)
                        values.append(value)
                    output[prop_name] = values
                else:
                    prop_node = prop_nodes.pop()
                    value = process_property_value(prop_node, prop_items)
                    output[prop_name] = value
            except IndexError:
                pass
        if "properties" in prop_items:
            subprops = process_properties(prop_items["properties"], parent_node)
            output[prop_name] = subprops
    return output


def xml_to_entitymeta(
    entity_name: str, 
    db_resource: Resource) -> EntityMeta:
    """
    Transform eXist resource into EntityMeta model
    """
    manifest = CFG["entities"][entity_name]["properties"]
    properties = process_properties(manifest, db_resource.node)

    db_id = {
        "abs": db_resource.abs_resource_id,
        "node": db_resource.node_id
    }

    return EntityMeta(
        id=db_resource.node[ID_ATTR_NAME],
        db_id=db_id,
        entity=entity_name,
        properties=properties
    )


class Service:

    @staticmethod
    def get_entities(entity_name: str) -> List[EntityMeta]:
        """
        Query a list of entities by entity name
        """
        return [
            xml_to_entitymeta(
                entity_name=entity_name,
                db_resource=resource,
            )
            for resource in entities[entity_name]
        ]
    
    @staticmethod
    def get_entity(entity_name: str, entity_id: str, format: str) -> str:
        """
        Query a an entity by entity name and ID
        """
        manifest = CFG["entities"][entity_name]
        resource = next((
            resource for resource in entities[entity_name]
            if resource.node[ID_ATTR_NAME] == entity_id
        ), None)
        if resource:
            if format == "xml":
                return str(resource.node)
            elif format == "json":
                try: 
                    output = resource.node.css_select("teiHeader").pop()
                except IndexError:
                    output = resource.node
                return xmltodict.parse(str(output))
            else:
                raise ValueError(f"Invalid format: {format}. Only 'xml' and 'json' are supported.")
        return resource
 

UpdateWatcher().watch_resources()

