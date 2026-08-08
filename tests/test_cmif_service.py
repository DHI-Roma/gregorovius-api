import pytest
from delb import Document

from service.cmif_service import (
    EDITION_URL,
    SOURCE_BIBL_ID,
    UnresolvedReference,
    build_corresp_desc,
    build_cmif,
    get_org,
    get_person,
    get_place,
    is_published,
)

PERSONS = Document(
    '<listPerson xmlns="http://www.tei-c.org/ns/1.0">'
    '<person xml:id="P1">'
    '<idno type="uri">http://d-nb.info/gnd/118541951</idno>'
    '<persName type="reg"><surname>Gregorovius</surname><forename>Ferdinand</forename></persName>'
    '</person>'
    '<person xml:id="P2">'
    '<persName type="reg"><surname>Ohne</surname><forename>Normdatum</forename></persName>'
    '</person>'
    '<org xml:id="O1"><orgName type="reg">Preußische Gesandtschaft</orgName></org>'
    '</listPerson>'
).root

PLACES = Document(
    '<listPlace xmlns="http://www.tei-c.org/ns/1.0">'
    '<place xml:id="L1">'
    '<idno type="uri">http://www.geonames.org/2867714</idno>'
    '<placeName type="reg">München</placeName>'
    '</place>'
    '<place xml:id="L2"><placeName type="reg">Ohne Geonames</placeName></place>'
    '</listPlace>'
).root


@pytest.fixture
def persons():
    return {
        str(node['{http://www.w3.org/XML/1998/namespace}id']): node
        for node in PERSONS.css_select('person, org')
    }


@pytest.fixture
def places():
    return {
        str(node['{http://www.w3.org/XML/1998/namespace}id']): node
        for node in PLACES.css_select('place')
    }


def as_node(tag_definition):
    """Materialize a tag definition so that its output can be inspected"""
    holder = Document('<holder xmlns="http://www.tei-c.org/ns/1.0"/>').root
    holder.append_children(tag_definition)
    return holder.first_child


def test_get_person_uses_gnd_identifier(persons):
    node = as_node(get_person('P1', persons))
    assert node['ref'] == 'http://d-nb.info/gnd/118541951'
    assert node.full_text == 'Gregorovius, Ferdinand'


def test_get_person_falls_back_to_edition_url(persons):
    node = as_node(get_person('P2', persons))
    assert node['ref'] == f'{EDITION_URL}/persons/P2'


def test_get_person_raises_on_unknown_id(persons):
    with pytest.raises(UnresolvedReference):
        get_person('nope', persons)


def test_get_org_uses_org_name(persons):
    node = as_node(get_org('O1', persons))
    assert node['ref'] == f'{EDITION_URL}/persons/O1'
    assert node.full_text == 'Preußische Gesandtschaft'


def test_get_place_uses_geonames_identifier(places):
    node = as_node(get_place('L1', places))
    assert node['ref'] == 'http://www.geonames.org/2867714'
    assert node.full_text == 'München'


def test_get_place_falls_back_to_edition_url(places):
    node = as_node(get_place('L2', places))
    assert node['ref'] == f'{EDITION_URL}/places/L2'


def letter(letter_id='B1', status='free', place_key='L1'):
    return Document(
        '<TEI xmlns="http://www.tei-c.org/ns/1.0" '
        'xmlns:telota="http://www.telota.de" '
        f'xml:id="{letter_id}" telota:doctype="letter_fgbe">'
        '<teiHeader><fileDesc><publicationStmt>'
        f'<availability status="{status}"/>'
        '</publicationStmt><sourceDesc>'
        '<correspDesc>'
        '<correspAction type="sent">'
        '<persName key="P1">Gregorovius, Ferdinand</persName>'
        f'<placeName key="{place_key}">München</placeName>'
        '<date when="1884-11-30"/>'
        '</correspAction>'
        '<correspAction type="received">'
        '<orgName key="O1">Gesandtschaft</orgName>'
        '</correspAction>'
        '<correspContext><ref type="prev">vorher</ref></correspContext>'
        '<p>Anmerkung</p>'
        '</correspDesc>'
        '</sourceDesc></fileDesc></teiHeader>'
        '<text><body><p/></body></text>'
        '</TEI>'
    ).root


def test_build_corresp_desc_resolves_references(persons, places):
    corresp_desc = build_corresp_desc(letter(), persons, places)

    assert corresp_desc['source'] == f'#{SOURCE_BIBL_ID}'
    assert corresp_desc['ref'] == f'{EDITION_URL}/letters/B1'

    person = corresp_desc.css_select('persName').last
    assert person['ref'] == 'http://d-nb.info/gnd/118541951'
    assert 'key' not in {str(name) for name in person.attributes}

    assert corresp_desc.css_select('placeName').last['ref'] == 'http://www.geonames.org/2867714'
    assert corresp_desc.css_select('orgName').last['ref'] == f'{EDITION_URL}/persons/O1'


def test_build_corresp_desc_strips_context_and_paragraphs(persons, places):
    corresp_desc = build_corresp_desc(letter(), persons, places)

    assert len(corresp_desc.css_select('correspContext')) == 0
    assert len(corresp_desc.css_select('p')) == 0
    assert len(corresp_desc.css_select('date')) == 1


def test_build_corresp_desc_raises_on_unknown_key(persons, places):
    with pytest.raises(UnresolvedReference):
        build_corresp_desc(letter(place_key='nope'), persons, places)


def test_is_published():
    assert is_published(letter()) is True
    assert is_published(letter(status='restricted')) is False


def test_build_cmif_skips_unpublished_letters(persons, places):
    letters = [letter('B1'), letter('B2', status='restricted')]
    document = Document(build_cmif(letters, persons, places))

    refs = [str(node['ref']) for node in document.css_select('correspDesc')]
    assert refs == [f'{EDITION_URL}/letters/B1']


def test_build_cmif_skips_letters_with_unresolved_references(persons, places):
    letters = [letter('B1'), letter('B2', place_key='nope')]
    document = Document(build_cmif(letters, persons, places))

    refs = [str(node['ref']) for node in document.css_select('correspDesc')]
    assert refs == [f'{EDITION_URL}/letters/B1']


def test_build_cmif_sorts_letters_by_id(persons, places):
    letters = [letter('B2'), letter('B1')]
    document = Document(build_cmif(letters, persons, places))

    refs = [str(node['ref']) for node in document.css_select('correspDesc')]
    assert refs == [f'{EDITION_URL}/letters/B1', f'{EDITION_URL}/letters/B2']


def test_build_cmif_has_cmif_root(persons, places):
    document = Document(build_cmif([letter()], persons, places))

    assert document.root['type'] == 'cmif'
    assert document.css_select('publicationStmt date').last['when']
    assert document.css_select('bibl').last['{http://www.w3.org/XML/1998/namespace}id'] == SOURCE_BIBL_ID
