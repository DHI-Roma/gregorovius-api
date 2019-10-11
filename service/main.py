import threading
import time
from datetime import datetime
from typing import Dict, List

import xmltodict
from lxml import etree
from snakesist.exist_client import ExistClient

from models import EntityMeta
from .helpers import xml_to_entitymeta


class UpdateWatcher:
    """
    Watcher for changes in the database
    """

    def __init__(self, db: ExistClient, entities: Dict):
        self.last_checked = datetime.now().isoformat(timespec="seconds")
        self.entities = entities
        self.db = db
    
    def _reset_timestamp(self):
        """
        Reset the timestamp of the last check to the current time
        """
        self.last_checked = datetime.now().isoformat(timespec="seconds")

    def _updated_resources(self) -> List:
        """
        Get a list of resources updated since the last check
        """
        updated_resources = self.db.retrieve_resources(
            f"""xmldb:find-last-modified-since(
            collection('{self.db.root_collection}'), 
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
                    for name, resource_list in self.entities.items()
                    for resource in resource_list
                    if resource.abs_resource_id in updated
                ]
            time.sleep(2)
    
    def watch_resources(self):
        """
        Start watcher in a new thread
        """
        thread = threading.Thread(target=self.update_resources)
        thread.daemon = True
        thread.start()


class Service:
    """
    Service for querying the database
    """

    def __init__(self, db: ExistClient, manifest: Dict, watch_updates: bool = False):
        self.manifest = manifest
        self.manifest_entities = manifest['entities']
        self.db = db
        self.entities = {
            name: self.db.retrieve_resources(manifest["xpath"])
            for name, manifest in self.manifest_entities.items()
        }
        try:
            self.id_attr = self.manifest['default_id_attribute']
        except KeyError:
            self.id_attr = '{http://www.w3.org/XML/1998/namespace}id'
        if watch_updates:
            UpdateWatcher(self.db, self.entities)

    def get_entities(self, entity_name: str) -> List[EntityMeta]:
        """
        Query a list of entities by entity name
        :param entity_name: Name of the entity as configured in the manifest
        :return: List of entities, each modelled according to the EntityMeta model
        """
        return [
            xml_to_entitymeta(
                self.manifest_entities[entity_name],
                entity_name,
                resource,
                self.id_attr
            )
            for resource in self.entities[entity_name]
        ]

    def get_entity(self, entity_name: str, entity_id: str, output_format: str) -> str:
        """
        Query a an entity by its entity name and ID
        :param entity_name: Name of the entity as configured in the manifest
        :param entity_id: ID of the entity
        :param output_format: Output format, "xml" or "json"
        :return: Entity in specified format if found, else None
        """
        resource = next((
            resource for resource in self.entities[entity_name]
            if resource.node[self.id_attr] == entity_id
        ), None)
        if resource:
            if output_format == "xml":
                return str(resource.node)
            elif output_format == "json":
                try:
                    output = resource.node.css_select("teiHeader").pop()
                except IndexError:
                    output = resource.node
                return xmltodict.parse(str(output))
            else:
                raise ValueError(f"Invalid format: {output_format}. Only 'xml' and 'json' are supported.")
        return resource

    @staticmethod
    def sanitize_stylesheet(stylesheet: str) -> str:
        """
        Sanitize XSLT stylesheet by checking for red flags and providing
        the root element by default. Warning: This means the processed
        stylesheets must not contain the xsl:stylesheet wrapper.
        :param stylesheet: XSLT Stylesheet
        :return: Transformation result
        """
        red_flags = ["xsl:import", "xsl:load", "document(", "<![CDATA["]
        if any(red_flag in stylesheet for red_flag in red_flags):
            return ""
        return (
            f'<xsl:stylesheet '
            f'xmlns:xsl="http://www.w3.org/1999/XSL/Transform" '
            f'xmlns:telota="http://www.telota.de" '
            f'xmlns:tei="http://www.tei-c.org/ns/1.0" '
            f'xmlns:v-bind="https://vuejs.org/v2/api/#v-bind" '
            f'xmlns:v-on="https://vuejs.org/v2/api/#v-on" '
            f'xmlns:func="http://exslt.org/functions" '
            f'extension-element-prefixes="func">'
            f'{stylesheet}'
            f'</xsl:stylesheet>'
        )

    def xslt_transform_entity(self, entity_name: str, entity_id: str, stylesheet: bytes) -> str:
        """
        Perform XSLT 1.0 Transformation on XML entity
        :param entity_name: Name of the entity as configured in the manifest
        :param entity_id: ID of the entity
        :param stylesheet: XSLT Stylesheet as received via the POST request body
        :return:
        """
        entity = next((
            resource for resource in self.entities[entity_name]
            if resource.node[self.id_attr] == entity_id
        ), None)
        stylesheet = self.sanitize_stylesheet(stylesheet.decode())
        try:
            xslt_root = etree.XML(stylesheet)
            transform = etree.XSLT(xslt_root)
            doc = etree.fromstring(str(entity))
            return str(transform(doc))
        except (etree.XMLSyntaxError, etree.XSLTApplyError, etree.XSLTParseError) as e:
            return f'Error occurred during XSLT transformation: {e}'
