from datetime import datetime
from typing import List

from models import EntityMeta

FILTER_PERSON = 'person'
FILTER_ORGANIZATION = 'org'

def get_gnd_ids(collection: List[EntityMeta], filter_type: str='') -> List:
    person_gnd_ids = []

    for person in collection:
        gnd_uri: str = person.properties.get('gnd')
        person_type: str = person.properties.get('type')

        if len(filter_type) and person_type != filter_type:
            continue

        if is_valid_gnd_uri(gnd_uri):
            gnd_id = gnd_uri.split('/')[-1]
            person_gnd_ids.append(gnd_id)

    return person_gnd_ids

def is_valid_gnd_uri(gnd_uri: str) -> bool:
    if gnd_uri is None:
        return False

    return '/gnd/' in gnd_uri

def make_beacon_header(filter_type: str='all') -> str:

    description = 'Alle Normdatensätze von {filter} in der digitalen Briefedition "Ferdinand Gregorovius Poesie und Wissenschaft Gesammelte deutsche und italienische Briefe"'

    if filter_type == FILTER_PERSON:
        description = description.replace('{filter}', 'Personen')
    elif filter_type == FILTER_ORGANIZATION:
        description = description.replace('{filter}', 'Körperschaften')
    else:
        description = description.replace('{filter}', 'Personen und Körperschaften')

    metadata: dict = {
        'FORMAT': 'BEACON',
        'PREFIX': 'http://d-nb.info/gnd/',
        'VERSION': '0.1',
        'TARGET': 'https://gregorovius-edition.dhi-roma.it/gnd/{ID}',
        'FEED': 'https://gregorovius-edition.dhi-roma.it/api/beacon/' + filter_type,
        'CONTACT': 'Wildegans Solutions <kontakt@wildegans-solutions.de>, Angela Steinsiek <steinsiek@dhi-roma.it>',
        'INSTITUTION': 'Deutsches Historisches Institut Rom',
        'DESCRIPTION': description,
        'TIMESTAMP': datetime.now()
    }

    header = ''
    for field in metadata:
        header += f'#{field}: {metadata[field]}\n'

    return header