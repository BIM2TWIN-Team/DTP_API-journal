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


"""
The file is a collection of methods used to interact with the DTP.
For more information, contact the author(s) listed above.
"""
import argparse
import json
import logging
import os
import time

import requests
import validators
from file_read_backwards import FileReadBackwards
from tqdm import tqdm

try:
    from DTP_config import DTPConfig
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from DTP_config import DTPConfig

from dtp_apis.count_DTP_API import CountAPI
from dtp_apis.create_DTP_API import CreateAPI
from dtp_apis.fetch_DTP_API import FetchAPI
from dtp_apis.link_DTP_API import LinkAPI
from dtp_apis.revert_DTP_API import RevertAPI
from dtp_apis.send_DTP_API import SendAPI
from dtp_apis.update_DTP_API import UpdateAPI
from helpers import logger_global, get_info_from_log


class DTPApi(FetchAPI, CountAPI, CreateAPI, LinkAPI, RevertAPI, SendAPI, UpdateAPI):
    """
    Base API class for mixin classes.

    Attributes
    ----------
    simulation_mode : bool
        if True then no changes to the database are performed.
    DTP_CONFIG : class
        an instance of DTP_Config

    Methods
    -------
    init_logger(session_file)
        None
    init_external_logger(session_logger)
        None
    TODO: move to a new class all the methods, which are used for sending requests    
    post_general_request(payload, url, headers)
        returns dictionary created from JSON
    general_guarded_request(req_type, payload, url, headers)
        returns dictionary created from JSON
    post_guarded_request(payload, url, headers)
        returns dictionary created from JSON
    put_guarded_request(payload, url, headers)
        returns dictionary created from JSON
    pretty_http_request_to_string(req)
        returns request string
    """

    def __init__(self, dtp_config, simulation_mode=False):
        """
        Parameters
        ----------
        dtp_config : DTP_Config, obligatory
            an instance of DTP_Config
        simulation_mode : bool, optional
            if set to True then method changing
            the database are not send.
        """

        self.simulation_mode = simulation_mode
        self.DTP_CONFIG = dtp_config
        self.session_logger = None

        self.log_markers_node_classes = {
            'new_element': 'NEW_ELEMENT_IRI',
            'new_defect': 'NEW_DEFECT_IRI',
            'new_action': 'NEW_ACTION_IRI',
            'new_operation': 'NEW_OPERATION_IRI',
            'new_constr': 'NEW_CONSTRUCTION_IRI',
            'new_kpi': 'NEW_KPI_IRI'}

        other_log_markers = {'link_elem_blob': 'NEW_LINK_ELEMENT_BLOB',
                             'new_blob': 'NEW_BLOB',
                             'update_asdesigned_param': 'UPDATE_isAsDesigned_PARAM_NODE_OPERATION',
                             'update_action': 'UPDATE_ACTION_IRI',
                             'update_operation': 'UPDATE_OPERATION_IRI',
                             'update_construction': 'UPDATE_CONSTRUCTION_IRI',
                             'remove_param': 'REMOVED_PARAM_NODE_OPERATION',
                             'add_param': 'ADD_PARAM_NODE_OPERATION',
                             'link_element_type': 'NEW_LINK_ELEMENT_ELEMENT_TYPE',
                             'link_constr_op': 'NEW_LINK_CONSTR_OPERATION',
                             'link_op_action': 'NEW_LINK_OPERATION_ACTION',
                             'link_action_asbuilt': 'NEW_LINK_ACTION_ASBUILT',
                             'link_task_type': 'NEW_LINK_NODE_TASK_TYPE'}

        try:
            self.log_markers = self.log_markers_node_classes | other_log_markers
        except TypeError:  # dictionary merge operator only in python 3.9+
            self.log_markers = {**self.log_markers_node_classes, **other_log_markers}

        # initialise session logger
        session_log_dir = os.path.join(self.DTP_CONFIG.get_log_path(), "sessions")
        self.node_log_dir = os.path.join(self.DTP_CONFIG.get_log_path(), f"nodes-{time.strftime('%Y%m%d-%H%M%S')}")
        if not os.path.exists(session_log_dir):
            os.makedirs(session_log_dir)
        if not os.path.exists(self.node_log_dir):
            os.makedirs(self.node_log_dir)
        session_log_path = os.path.join(session_log_dir, f"db_session-{time.strftime('%Y%m%d-%H%M%S')}.log")
        self.init_logger(session_log_path)

    def set_simulation_mode(self, flag):
        """
        Method used for changing the simulation mode between on (true) and off (false).

        Parameters
        ----------
        flag: bool obligatory
           if true then the simulation mode is set to on, and off otherwise.
        Returns
        -------
        bool
            The old value of the simulation mode.
        """
        old_value = self.simulation_mode
        self.simulation_mode = flag
        return old_value

    def init_logger(self, session_file):
        """
        Method used for initializing a logger used to collect information about session: only node linking
        and creation is saved at the moment. The method should be used only for single core processing.
        For parallel processing use init_external_logger.

        Parameters
        ----------
        session_file: str obligatory
            the path to the log file, it does not need to exist.
        """

        if len(session_file.strip()) != 0:
            print(f"Session log file at {session_file}")
            formatter = logging.Formatter('%(asctime)s : %(message)s', datefmt='%d-%b-%y %H:%M:%S')
            handler = logging.FileHandler(session_file)
            handler.setFormatter(formatter)

            self.session_logger = logging.getLogger('session_DTP')
            self.session_logger.setLevel(logging.INFO)
            self.session_logger.addHandler(handler)

    def init_external_logger(self, session_logger):
        """
        The method allows for passing an external session logger to the instance of the class.

        Parameters
        ----------
        session_logger: Logger (see logging) obligatory
            an instance of the logger class.
        """

        self.session_logger = session_logger

    def post_general_request(self, payload, url=' ', headers=None):
        """
        The method allows for sending POST requests to the DTP. This version does not respect the simulation mode.
        For a simulation mode respecting version see: __post_guarded_request

        Parameters
        ----------
        payload: dict obligatory
            the query to be sent to the platform.
        url: str optional
            the URL used for the HTTPS request
        headers: dict optional
            the header of the request, if not provided the default one is used.
        """

        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + self.DTP_CONFIG.get_token()
            }

        session = requests.Session()

        if not validators.url(url):
            raise Exception("Sorry, the URL is not a valid URL: " + url)
        req = requests.Request("POST", url, headers=headers, data=payload)

        prepared = req.prepare()

        logger_global.info('HTTP request: \n' + self.pretty_http_request_to_string(prepared))

        response = session.send(prepared)
        logger_global.info('Response code: ' + str(response.status_code))

        if response.ok:
            return response
        else:
            logger_global.error(
                "The response from the DTP is an error. Check the dev token and/or the domain. Status code: " + str(
                    response.status_code))
            raise Exception(
                "The response from the DTP is an error. Check the dev token and/or the domain. Status code: " + str(
                    response.status_code))

    def general_guarded_request(self, req_type, payload, url=' ', headers=None):
        """
        The method allows for sending POST requests to the DTP. This version does respect the simulation mode.
        For a none simulation mode respecting version see: __post_general_request

        Parameters
        ----------
        payload: dict obligatory
            the query to be sent to the platform.
        url: str optional
            the URL used for the HTTPS request
        headers: dict optional
            the header of the request, if not provided the default one is used.
        """

        if headers is None:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + self.DTP_CONFIG.get_token()
            }

        req_type_fix = req_type.strip().upper()
        if len(req_type_fix) == 0:
            Exception("Request type cannot be empty!")

        if req_type_fix != 'PUT' or req_type_fix != 'POST':
            Exception("Request type has to be: PUT or POST!")

        session = requests.Session()
        req = requests.Request(req_type_fix, url, headers=headers, data=payload)
        prepared = req.prepare()
        logger_global.info('HTTP request: \n' + self.pretty_http_request_to_string(prepared))

        if not self.simulation_mode:
            response = session.send(prepared)
            logger_global.info('Response code: ' + str(response.status_code))
            return response
        return None

    def post_guarded_request(self, payload, url=' ', headers=None):
        return self.general_guarded_request('POST', payload, url, headers)

    def put_guarded_request(self, payload, url=' ', headers=None):
        return self.general_guarded_request('PUT', payload, url, headers)

    def pretty_http_request_to_string(self, req):
        """
        The method provides a printing method for pre-prepared HTTP requests.
        Source: https://stackoverflow.com/questions/20658572/python-requests-print-entire-http-request-raw
        Author: AntonioHerraizS

        Usage
        -----
        req = requests.Request("POST", DTP_CONFIG.get_api_uri('send_blob'), headers=headers,
        data=payload, files=files) # any request prepared = req.prepare() __pretty_http_request_to_string(prepared)

        Parameters
        ----------
        req : Request, obligatory
            the pre-prepared request
        """

        request_str = '{}\n{}\r\n{}\r\n\r\n{}\n{}'.format(
            '-----------START-----------',
            req.method + ' ' + req.url,
            '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
            '-----------END-----------'
        )

        return request_str

    def revert_sessions(self, session_path):
        """
        Revert multiple session in a directory

        Parameters
        ----------
        session_path: str
            path to the session directory
        """
        assert os.path.isdir(session_path), f"{session_path} is not a directory"
        log_files = [f for f in os.listdir(session_path) if f.endswith('.log')]
        sorted_log_files = sorted(log_files, reverse=False)  # newest to oldest
        for log_file in sorted_log_files:
            print(f"Reverting {log_file}")
            self.revert_last_session(os.path.join(session_path, log_file))
            print(f"Session reverted.")

    def revert_last_session(self, session_file):
        """
        The method can revert the last non-empty sessions.

        Parameters
        ----------
        session_file : str, obligatory
            path to the sessions file
        """

        counter = 0

        with FileReadBackwards(session_file, encoding="utf-8") as frb:
            for line in tqdm(frb):
                # that will be the last date once the beginning of the file is reached.
                msg_date = line[0: line.find(' : ')]
                if self.log_markers['link_elem_blob'] in line:
                    element_uuid, blob_uuid = get_info_from_log(line, self.log_markers['link_elem_blob'])
                    counter += 1
                    self.unlink_node_from_blob(element_uuid, blob_uuid)
                elif self.log_markers['new_blob'] in line:
                    blob_uuid = get_info_from_log(line, self.log_markers['new_blob'])[0]
                    self.delete_blob_from_platform(blob_uuid)
                    counter += 1
                elif self.log_markers['update_asdesigned_param'] in line:
                    element_iri = get_info_from_log(line, self.log_markers['update_asdesigned_param'])[0]
                    self.delete_asdesigned_param_node(element_iri)
                    counter += 1
                elif self.log_markers['update_action'] in line:
                    node_iri, dump_path = get_info_from_log(line, self.log_markers['update_action'])
                    self.revert_node_update(node_iri, dump_path)
                elif self.log_markers['update_operation'] in line:
                    node_iri, dump_path = get_info_from_log(line, self.log_markers['update_operation'])
                    self.revert_node_update(node_iri, dump_path)
                    counter += 1
                elif self.log_markers['update_construction'] in line:
                    node_iri, dump_path = get_info_from_log(line, self.log_markers['update_construction'])
                    self.revert_node_update(node_iri, dump_path)
                    counter += 1
                elif self.log_markers['remove_param'] in line:
                    node_iri, field, field_value = get_info_from_log(line, self.log_markers['remove_param'])
                    self.add_param_in_node(node_iri, field, field_value)
                    counter += 1
                elif self.log_markers['add_param'] in line:
                    node_iri, field = get_info_from_log(line, self.log_markers['add_param'])
                    self.delete_param_in_node(node_iri, field, is_revert_session=True)
                    counter += 1
                elif self.log_markers['link_element_type'] in line:
                    node_iri, element_type_iri = get_info_from_log(line, self.log_markers['link_element_type'])
                    self.unlink_element_type(node_iri, element_type_iri)
                    counter += 1
                elif self.log_markers['link_constr_op'] in line:
                    constr_node_iri, list_of_operation_iri = get_info_from_log(line, self.log_markers['link_constr_op'])
                    self.unlink_constr_op(constr_node_iri, list_of_operation_iri)
                    counter += 1
                elif self.log_markers['link_op_action'] in line:
                    oper_node_iri, list_of_action_iri = get_info_from_log(line, self.log_markers['link_op_action'])
                    self.unlink_operation_action(oper_node_iri, list_of_action_iri)
                elif self.log_markers['link_action_asbuilt'] in line:
                    action_node_iri, target_asbuilt_iri = get_info_from_log(line,
                                                                            self.log_markers['link_action_asbuilt'])
                    self.unlink_action_asbuilt(action_node_iri, target_asbuilt_iri)
                elif self.log_markers['link_task_type'] in line:
                    node_iri, task_type_iri = get_info_from_log(line, self.log_markers['link_task_type'])
                    self.unlink_task_type(node_iri, task_type_iri)
                    counter += 1
                else:
                    try:
                        node_class = next(
                            substring for substring in self.log_markers_node_classes.values() if substring in line)
                    except StopIteration as E:
                        continue
                    index = line.find(node_class)
                    node_iri = line[index + len(node_class) + 1:].strip()
                    try:
                        node_uuid = self.get_uuid_for_iri(node_iri)
                    except Exception as e:
                        if hasattr(e, 'message'):
                            e_msg = e.message
                        else:
                            e_msg = e
                        logger_global.error(
                            'Error at the session revert for entry at : ' + msg_date + ', the message: ' + str(
                                e_msg) + '.')
                        continue
                    self.delete_node_from_graph(node_uuid)
                    counter = counter + 1

                logger_global.info('The session started at: ' + msg_date + ', has been reverted.')

    def query_all_pages(self, fetch_function, *fetch_function_arg):
        """
        The method will query all pages for an API methods

        Parameters
        ----------
        fetch_function:
            function used to query DTP
        fetch_function_arg: tuple
            arguments to fetch_function

        Returns
        -------
        dictionary
            JSON mapped to a dictionary. The data contain nodes from all pages.
        """
        query_response_all_pages = fetch_function(*fetch_function_arg)
        elements = query_response_all_pages

        while 'next' in elements.keys() and elements['size'] != 0:
            if len(fetch_function_arg):
                elements = fetch_function(*fetch_function_arg, url=elements['next'])
            else:
                elements = fetch_function(url=elements['next'])

            if elements['size'] <= 0:
                break

            query_response_all_pages['items'] += elements['items']
            query_response_all_pages['size'] += elements['size']

        return query_response_all_pages

    def check_if_exist(self, node_iri):
        """
        The method check if the node corresponding to the given iri exist or not

        Parameters
        ----------
        node_iri: str, obligatory
            a valid node IRI.

        Returns
        -------
        bool
            return True if the node exist and False otherwise.
        """
        if not validators.url(node_iri):
            raise Exception("Sorry, the IRI is not a valid URL.")

        payload = json.dumps(
            {
                "query": {
                    "$domain": self.DTP_CONFIG.get_domain(),
                    "$iri": node_iri
                }
            }
        )

        req_url = self.DTP_CONFIG.get_api_url('get_find_elements')
        response = self.post_general_request(payload, req_url).json()

        return True if response['size'] else False


# Below code snippet for testing only

def parse_args():
    """
    Get parameters from user
    """
    parser = argparse.ArgumentParser(description='Prepare DTP graph')
    parser.add_argument('--xml_path', '-x', type=str, help='path to config xml file', required=True)
    parser.add_argument('--simulation', '-s', default=False, action='store_true')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    dtp_config = DTPConfig(args.xml_path)
    dtp_api = DTPApi(dtp_config, simulation_mode=args.simulation)
    response = dtp_api.fetch_subgraph()
    print('Response:\n', response)
