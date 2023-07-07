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
    parser = argparse.ArgumentParser(description='Revert multiple sessions with log files')
    parser.add_argument('--xml_path', '-x', type=str, help='path to config xml file', default='../DTP_config.xml')
    parser.add_argument('--revert_dir', '-r', type=str, help='path to session directory', required=True)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    dtp_config = DTPConfig(args.xml_path)
    dtp_api = DTPApi(dtp_config)
    print(f'Reverting session from dir {args.revert_dir}')
    dtp_api.revert_sessions(args.revert_dir)
    print(f'All session reverted.')
