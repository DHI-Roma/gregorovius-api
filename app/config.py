import yaml

with open('config.yml', 'r') as config_file:
    CFG = yaml.load(config_file, Loader=yaml.FullLoader)

ENTITY_NAMES = list(CFG['entities'])
ENTITIES = CFG["entities"].items()
ROOT_COLLECTION = CFG["collection"]

try:
    XSLT_FLAG = CFG['xslt']
except KeyError:
    XSLT_FLAG = False
