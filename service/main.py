import threading
import time
import html
from datetime import datetime
from typing import Dict, List
from xml.dom import minidom

import xmltodict
from lxml import etree
from requests.exceptions import HTTPError
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
        self._initialize_search_indices()

    def _initialize_search_indices(self):
        """
        Create Lucene search configurations according to config.yml,
        store them in the database and initiate reindexing.
        """
        searchable_entities = [
            entity_conf["search_index"] for entity_name, entity_conf in self.manifest["entities"].items()
            if "search_index" in entity_conf
        ]
        text_config = ""
        for unit in searchable_entities:
            try:
                for text in unit["text"]:
                    text_config += (
                        f"<text {text['type']}='{text['pattern']}'>"
                        f"<inline qname='{text['inline-qname']}'/>"
                    )

                    if "fields" in text:
                        for field in text["fields"]:
                            text_config += f"<field name='{field['name']}' expression='{field['expression']}' />"

                    if "ignore" in text:
                        text_config += f"<ignore  qname='{text['ignore']}'/>"
                    text_config += "</text>"
            except KeyError:
                raise ValueError(f"Error reading search index configuration: {unit}.")

        config = (
            "<collection xmlns='http://exist-db.org/collection-config/1.0'>"
            "<index xmlns:tei='http://www.tei-c.org/ns/1.0'>"
            "<fulltext default='none' attributes='false'/>"
            "<lucene>"
            "<analyzer class='org.apache.lucene.analysis.standard.StandardAnalyzer'/>"
            f"{text_config}"
            "</lucene>"
            "</index>"
            "</collection>"
        )
        collection = self.manifest['collection']
        collection_alternative = self.manifest['collection_alternative']

        config_path = f"/db/system/config{collection}"
        config_path_alternative = f"/db/system/config{collection_alternative}"
        try:
            self.db.query(
                f'(xmldb:create-collection("/db/system/config", "{collection}"),'
                f'xmldb:store("{config_path}", "collection.xconf", "{config}"),'
                f'xmldb:reindex("{collection}"))'
            )

            self.db.query(
                f'(xmldb:create-collection("/db/system/config", "{collection_alternative}"),'
                f'xmldb:store("{config_path_alternative}", "collection.xconf", "{config}"),'
                f'xmldb:reindex("{collection_alternative}"))'
            )
        except HTTPError as e:
            print(e)

        collection_alt = self.manifest['collection_alternative']
        config_path_alt = f"/db/system/config{collection}"
        try:
            self.db.query(
                f'(xmldb:create-collection("/db/system/config", "{collection_alt}"),'
                f'xmldb:store("{config_path_alt}", "collection.xconf", "{config}"),'
                f'xmldb:reindex("{collection_alt}"))'
            )
        except HTTPError as e:
            print(e)

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
                raise ValueError(
                    f"Invalid format: {output_format}."
                    f"Only 'xml' and 'json' are supported."
                )
        return resource

    def get_search_results(self, entity: str, keyword: str, width: int) -> Dict:
        """
        Make a full text search query against the database. The database index must be
        configured as a prerequisite. At the moment the query is hard coded to a single
        XML node (//*:text).
        :param entity: The name of the entity as configured in config.yml
        :param keyword: The string to search for
        :param width: The width of the context strings surrounding the found keyword
        """
        try:
            self.manifest_entities[entity]["search_index"]
        except KeyError:
            return {"error": f"Search is not available for {entity}."}
        entity_xpath = self.manifest_entities[entity]["xpath"]
        entity_entrypoint = self.manifest_entities[entity]["search_index"]["entrypoint"]
        should_get_document_id = self.manifest_entities[entity]["search_index"]["results"]["get_document_id"]
        
        id_processing_default = f"$hit/ancestor::{entity_xpath.lstrip('//')}/@xml:id/string()"
        id_processing_local = f"$hit/@xml:id/string()"
        id_processing_root = f"$hit/ancestor::*:TEI/@xml:id/string()"
        
        coll_path = self.manifest["collection"]
        if "use_alternative_collection" in self.manifest_entities[entity]["search_index"] and self.manifest_entities[entity]["search_index"]["use_alternative_collection"] is True:
            if self.manifest_entities[entity]["search_index"]:
                coll_path = self.manifest["collection_alternative"]

        try:
            query = (
                f"declare namespace tei = 'http://www.tei-c.org/ns/1.0'; "
                f"import module namespace "
                f"kwic = 'http://exist-db.org/xquery/kwic' "
                f"at 'resource:org/exist/xquery/lib/kwic.xql'; "
                f"for $hit in "
                f"collection('{coll_path}')"
                f"{entity_entrypoint}[ft:query(.,'{keyword}') and ancestor::{entity_xpath.lstrip('//')}] "
                f"let $score := ft:score($hit) "
                f"order by $score descending "
                f"return <envelope><kwic>{{kwic:summarize($hit, <config width='{width}'/>)}}</kwic>"
                f"<score>{{$score}}</score>"
                f"<type>{entity}</type>"
            )
            if should_get_document_id:
                query += f"<id>{{{id_processing_default}}}</id>"
            else:
                query += (
                    f"<id>{{{id_processing_local}}}</id>"
                    f"<related>{{{id_processing_root}}}</related>"
                )

            query += "</envelope>"

            query_results = self.db.query(query)
            results = query_results.css_select("envelope")
        except HTTPError as e:
            results  = []
        output = []
        for r in results:
            for p in r.xpath(".//p"): 
                context_previous = p.xpath(".//span[@class='previous']").pop().full_text
                context_hi = p.xpath(".//span[@class='hi']").pop().full_text
                context_following = p.xpath(".//span[@class='following']").pop().full_text
                score = r.xpath(".//score").pop().full_text
                entity_id = r.xpath(".//id").pop().full_text
                entity_type = r.xpath(".//type").pop().full_text

                entry = {
                    "score": score,
                    "previous": " ".join(context_previous.split()),
                    "hi": " ".join(context_hi.split()),
                    "following": " ".join(context_following.split()),
                    "entity_id": entity_id,
                }

                if not should_get_document_id:
                    entity_related_id = r.xpath(".//related").pop().full_text
                    entry["entity_related_id"] = entity_related_id

                output.append(entry)
        return {
            "count": len(output),
            "results": output
        }

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
