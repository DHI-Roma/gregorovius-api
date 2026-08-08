"""
Generation of the CMIF (Correspondence Metadata Interchange Format) document.

This logic used to live in gregorovius-data-sync, which built the document
during a synchronization run and wrote it straight into the database. Since
synchronization has been retired, the document is generated here instead,
either on demand by the /cmif endpoint or ahead of time by bin/generate_cmif.py.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import delb
from delb import Document, TagNode

logger = logging.getLogger(__name__)

EDITION_URL = "https://gregorovius-edition.dhi-roma.it"
SOURCE_BIBL_ID = "f1f96c77-675a-460a-85b9-74ffebb9453e"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

delb.register_namespace('tei', 'http://www.tei-c.org/ns/1.0')
delb.register_namespace('TEI', 'http://www.tei-c.org/ns/1.0')


class UnresolvedReference(Exception):
    """Raised when a correspAction refers to an entity missing from the registers"""


def index_by_id(resources) -> Dict[str, TagNode]:
    """
    Index database resources by their @xml:id
    :param resources: Resources as queried by the Service
    :return: Mapping of @xml:id to the corresponding node
    """
    index = {}
    for resource in resources:
        node = resource.node
        try:
            index[str(node[XML_ID])] = node
        except (KeyError, TypeError):
            continue
    return index


def get_identifier(node: TagNode, fallback: str) -> str:
    """
    Get the authority file URI of an entity, falling back to its edition URL
    :param node: Entity node from one of the registers
    :param fallback: URI to use when the entity has no GND identifier
    :return: Identifier URI
    """
    identifier = None
    for idno in node.css_select('idno'):
        if 'd-nb' in idno.full_text:
            identifier = idno.full_text
    return identifier if identifier is not None else fallback


def get_person(person_id: str, persons: Dict[str, TagNode]) -> delb.tag:
    """
    Build a CMIF persName node for a person in the person index
    :param person_id: @xml:id of the person
    :param persons: Person index as returned by index_by_id
    :return: persName node with a reference to the person's identifier
    """
    person = persons.get(person_id)
    if person is None:
        raise UnresolvedReference(
            f'There is no person with the id {person_id} in the person index.'
        )

    identifier = get_identifier(person, f'{EDITION_URL}/persons/{person_id}')

    reg_name = person.css_select('persName[type=reg]').last
    if reg_name is None:
        full_name = ''
    else:
        full_name = ', '.join(part.full_text for part in reg_name.xpath('.//*'))

    return delb.tag('persName', {'ref': identifier}, full_name)


def get_org(org_id: str, persons: Dict[str, TagNode]) -> delb.tag:
    """
    Build a CMIF orgName node for an organization in the person index
    :param org_id: @xml:id of the organization
    :param persons: Person index as returned by index_by_id, which covers
                    both person and org nodes
    :return: orgName node with a reference to the organization's identifier
    """
    org = persons.get(org_id)
    if org is None:
        raise UnresolvedReference(
            f'There is no organization with the id {org_id} in the person index.'
        )

    identifier = get_identifier(org, f'{EDITION_URL}/persons/{org_id}')

    org_name = org.css_select('orgName').last
    name = org_name.full_text if org_name is not None else ''

    return delb.tag('orgName', {'ref': identifier}, name)


def get_place(place_id: str, places: Dict[str, TagNode]) -> delb.tag:
    """
    Build a CMIF placeName node for a place in the place index
    :param place_id: @xml:id of the place
    :param places: Place index as returned by index_by_id
    :return: placeName node with a reference to the place's identifier
    """
    place = places.get(place_id)
    if place is None:
        raise UnresolvedReference(
            f'There is no place with the id {place_id} in the place index.'
        )

    # Places nest, so this picks up an idno of a contained place when the place
    # itself has none. That is what the synchronization script did as well, and
    # the resulting reference still points at the surrounding location.
    idno = place.css_select('idno').first
    geo_id = idno.full_text if idno is not None else f'{EDITION_URL}/places/{place_id}'

    place_name = place.css_select('placeName').first
    name = place_name.full_text if place_name is not None else ''

    return delb.tag('placeName', {'ref': geo_id}, name)


def is_published(letter: TagNode) -> bool:
    """
    Check whether a letter is flagged as published
    :param letter: TEI node of the letter
    :return: True if the letter may be published
    """
    availability = letter.css_select('availability').first
    if availability is None:
        return False
    try:
        return str(availability['status']) == 'free'
    except (KeyError, TypeError):
        return False


def build_corresp_desc(
        letter: TagNode,
        persons: Dict[str, TagNode],
        places: Dict[str, TagNode]
) -> Optional[TagNode]:
    """
    Build the CMIF correspDesc of a single letter by resolving the register
    keys of its correspAction nodes into references
    :param letter: TEI node of the letter
    :param persons: Person index as returned by index_by_id
    :param places: Place index as returned by index_by_id
    :return: correspDesc node, or None if the letter has none
    """
    source = letter.css_select('correspDesc').last
    if source is None:
        return None

    corresp_desc = source.clone(deep=True)

    replacements = (
        ('persName', get_person, persons),
        ('orgName', get_org, persons),
        ('placeName', get_place, places),
    )
    for tag_name, resolve, index in replacements:
        selector = (
            f'correspAction[type=sent] {tag_name}, '
            f'correspAction[type=received] {tag_name}'
        )
        for node in corresp_desc.css_select(selector).as_list():
            node.add_following_siblings(resolve(str(node['key']), index))
            node.detach()

    for node in corresp_desc.css_select('correspContext, p').as_list():
        node.detach()

    corresp_desc.attributes['source'] = f'#{SOURCE_BIBL_ID}'
    corresp_desc.attributes['ref'] = f'{EDITION_URL}/letters/{str(letter[XML_ID])}'

    return corresp_desc


def build_skeleton() -> Document:
    """
    Build the CMIF document without any correspondence metadata in it
    :return: CMIF document
    """
    timestamp = datetime.now().replace(microsecond=0).astimezone().isoformat()
    return Document(
        '<TEI type="cmif" xmlns="http://www.tei-c.org/ns/1.0">'
        '<teiHeader>'
        '<fileDesc>'
        '<titleStmt>'
        '<title>'
        'Ferdinand Gregorovius Correspondence Edition CMIF API'
        '</title>'
        '<editor>'
        'Oliver Pohl'
        '<email>oliverpohl@wildegans-solutions.de</email>'
        '</editor>'
        '</titleStmt>'
        '<publicationStmt>'
        '<publisher>'
        '<ref target="http://www.dhi-roma.it">German Historical Institute Rome</ref>'
        '</publisher>'
        f'<date when="{timestamp}"/>'
        '<availability>'
        '<licence target="https://creativecommons.org/licenses/by/4.0/">'
        'This file is licensed under the terms of the Creative-Commons-License CC-BY 4.0'
        '</licence>'
        '</availability>'
        f'<idno type="url">{EDITION_URL}/api/cmif</idno>'
        '</publicationStmt>'
        '<sourceDesc>'
        f'<bibl type="online" xml:id="{SOURCE_BIBL_ID}">'
        'Ferdinand Gregorovius. Poesie und Wissenschaft: '
        'Gesammelte deutsche und italienische Briefe, hg. von Angela Steinsiek '
        'unter Mitarbeit von Oliver Pohl. '
        'Deutsches Historisches Institut Rom, Rom 2017-2021.'
        f'<ref target="{EDITION_URL}">{EDITION_URL}</ref>'
        '</bibl>'
        '</sourceDesc>'
        '</fileDesc>'
        '<profileDesc/>'
        '</teiHeader>'
        '<text><body><p/></body></text>'
        '</TEI>'
    )


def build_cmif(
        letters: List[TagNode],
        persons: Dict[str, TagNode],
        places: Dict[str, TagNode]
) -> str:
    """
    Build the CMIF document from letters and registers
    :param letters: TEI nodes of the letters
    :param persons: Person index as returned by index_by_id
    :param places: Place index as returned by index_by_id
    :return: Serialized CMIF document
    """
    document = build_skeleton()
    profile_desc = document.css_select('profileDesc').last

    # Sorting keeps the output stable across runs, so that regenerating the
    # document produces a readable diff
    letters = sorted(letters, key=lambda letter: str(letter[XML_ID]))

    for letter in letters:
        if not is_published(letter):
            continue
        try:
            corresp_desc = build_corresp_desc(letter, persons, places)
        except UnresolvedReference as error:
            logger.warning(
                'Skipping letter %s in CMIF document: %s',
                str(letter[XML_ID]), error
            )
            continue
        if corresp_desc is not None:
            profile_desc.append_children(corresp_desc)

    return str(document)


def generate_cmif(service) -> str:
    """
    Build the CMIF document from the entities held by the service
    :param service: Service instance holding the queried entities
    :return: Serialized CMIF document
    """
    persons = index_by_id(service.entities['persons'])
    places = index_by_id(service.entities['places'])
    letters = [resource.node for resource in service.entities['letters']]

    logger.info(
        'Generating CMIF document from %s letters, %s persons, %s places',
        len(letters), len(persons), len(places)
    )

    return build_cmif(letters, persons, places)
