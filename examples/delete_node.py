# -*- coding: utf-8 -*-`

#  Copyright (c) Centre Inria d'Université Côte d'Azur, University of Cambridge 2023.
#  Authors: Kacper Pluta <kacper.pluta@inria.fr>, Alwyn Mathew <am3156@cam.ac.uk>
#
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
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
