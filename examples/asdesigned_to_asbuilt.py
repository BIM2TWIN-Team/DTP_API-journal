# -*- coding: utf-8 -*-`
#  Copyright (c) Sophia Antipolis-Méditerranée, University of Cambridge 2023.
#  Authors: Kacper Pluta <kacper.pluta@inria.fr>, Alwyn Mathew <am3156@cam.ac.uk>
#  This file cannot be used without a written permission from the author(s).

import argparse
import os
import time
from datetime import datetime

try:
    from DTP_config import DTPConfig
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, "../")
    from DTP_config import DTPConfig

from DTP_API import DTPApi
import helpers
from helpers import logger_global


def parse_args():
    """
    Get parameters from user
    """
    parser = argparse.ArgumentParser(description='Create as-built from as-designed node')
    parser.add_argument('--xml_path', '-x', type=str, help='path to config xml file', required=True)
    parser.add_argument('--simulation', '-s', default=False, action='store_true')
    parser.add_argument('--log_dir', '-l', type=str, help='path to log dir', required=True)

    return parser.parse_args()


if __name__ == "__main__":
    logger_global.info('New session has been started.')
    args = parse_args()
    dtp_config = DTPConfig(args.xml_path)
    dtp_api = DTPApi(dtp_config, simulation_mode=args.simulation)

    # initialise session logger
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
    log_path = os.path.join(args.log_dir, f"db_session-{time.strftime('%Y%m%d-%H%M%S')}.log")
    dtp_api.init_logger(log_path)

    elements = dtp_api.query_all_pages(dtp_api.fetch_asdesigned_nodes, "ifc:Class", "IfcWall")

    for element in elements['items']:
        asbuild_iri = helpers.create_as_performed_iri(element['_iri'])
        timestamp = helpers.get_timestamp_dtp_format(datetime.now())
        element_type = dtp_config.get_ontology_uri('Wall')
        dtp_api.create_asbuilt_node(asbuild_iri, 100, timestamp, element_type, element['_iri'])
