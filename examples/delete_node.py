# -*- coding: utf-8 -*-`
#  Copyright (c) Sophia Antipolis-Méditerranée, University of Cambridge 2023.
#  Authors: Kacper Pluta <kacper.pluta@inria.fr>, Alwyn Mathew <am3156@cam.ac.uk>
#  This file cannot be used without a written permission from the author(s).

import argparse

try:
    from DTP_config import DTPConfig
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, "../")
    from DTP_config import DTPConfig

from DTP_API import DTPApi


def parse_args():
    """
    Get parameters from user
    """
    parser = argparse.ArgumentParser(description='Delete a node from DTP')
    parser.add_argument('--xml_path', '-x', type=str, help='path to config xml file', default='../DTP_config.xml')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    dtp_config = DTPConfig(args.xml_path)
    dtp_api = DTPApi(dtp_config)
    node_iri = 'http://bim2twin.eu/pilot_kivitasku/as_built-13kDfD$ZLCXPIxpkUxAVdK_1'
    resp = dtp_api.delete_node_from_graph_with_iri(node_iri)
    if resp:
        print(f'Node deleted.')
    else:  # check if node exists
        print(f'Deleting failed!' if dtp_api.check_if_exist(node_iri) else 'Node doesnt exists.')
