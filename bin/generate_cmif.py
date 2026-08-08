#!/usr/bin/env python
"""
Generate the CMIF document from the data in eXist and write it to a file.

The generated document is meant to be committed to the gregorovius-data
repository, from where it is packaged into the XAR archive and deployed
into the database.
"""

import argparse
import logging
import os
import sys

from lxml import etree
from snakesist.exist_client import ExistClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The manifest is read relative to the working directory
os.chdir(ROOT_DIR)
sys.path.insert(0, ROOT_DIR)

from app.config import CFG, ROOT_COLLECTION  # noqa: E402
from service import Service  # noqa: E402
from service.cmif_service import generate_cmif  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--host', default='db',
        help='Host of the eXist instance (default: db)'
    )
    parser.add_argument(
        '--port', type=int, default=8080,
        help='Port of the eXist instance (default: 8080)'
    )
    parser.add_argument(
        '--user', default='admin',
        help='User of the eXist instance (default: admin)'
    )
    parser.add_argument(
        '--password', default='',
        help='Password of the eXist instance (default: empty)'
    )
    parser.add_argument(
        '--output', default='data/cmif.xml',
        help='Path of the generated document (default: data/cmif.xml)'
    )
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    args = parse_args()

    db = ExistClient(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        parser=etree.XMLParser(recover=True)
    )
    db.root_collection = ROOT_COLLECTION

    service = Service(db, CFG, watch_updates=False)
    cmif = generate_cmif(service)

    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write(cmif)

    count = cmif.count('<correspDesc')
    print(f'Wrote {count} correspDesc entries to {output_path}')


if __name__ == '__main__':
    main()
