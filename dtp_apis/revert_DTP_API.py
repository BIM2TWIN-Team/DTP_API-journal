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

import json
import os

import requests
import validators

from helpers import logger_global


class RevertAPI:
    """
    Mixin revert API class contains revert function to roll back to previous stage with session logs.

    Methods
    -------
    delete_node_from_graph(node_uuid)
        returns bool, True if success and False otherwise
    delete_node_from_graph_with_iri(node_iri)
        returns bool, True if success and False otherwise
    unlink_node_from_blob(node_uuid, blob_uuid)
        returns bool, True if success and False otherwise
    delete_blob_from_platform(blob_uuid)
        returns bool, True if success and False otherwise
    undo_update_asdesigned_param_node(node_iri)
        returns bool, True if success and False otherwise
    """

    def delete_node_from_graph(self, node_uuid):
        """
        The method deletes a node from DTP.

        Parameters
        ----------
        node_uuid : str, obligatory
            a valid uuid of a node to remove.

        Returns
        ------
        bool
            True if an element has been deleted and False otherwise
        """
        # creating backup of the node
        node_info = self.fetch_node_with_uuid(node_uuid)
        dump_path = os.path.join(self.node_log_dir, f"{node_uuid.rsplit('/')[-1]}.json")
        with open(dump_path, 'w') as fp:
            json.dump(node_info, fp)

        payload = ""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + self.DTP_CONFIG.get_token()
        }

        session = requests.Session()
        req = requests.Request("DELETE", self.DTP_CONFIG.get_api_url('delete_avatar', node_uuid), headers=headers,
                               data=payload)
        prepared = req.prepare()

        logger_global.info('HTTP request: \n' + self.pretty_http_request_to_string(prepared))

        if not self.simulation_mode:
            response = session.send(prepared)
            logger_global.info('Response code: ' + str(response.status_code))

            if response.ok:
                logger_global.info("The node: " + node_uuid + ", has been deleted.")
                if self.session_logger is not None:
                    self.session_logger.info(f"DTP_API - DELETE_NODE_UUID: {node_uuid}, {dump_path}")
                return True
            else:
                logger_global.error(
                    "The node: " + node_uuid + ", cannot be deleted. Status code: " + str(response.status_code))
                return False
        return True

    def delete_node_from_graph_with_iri(self, node_iri):
        """
        The method deletes a node from DTP.

        Parameters
        ----------
        node_iri : str, obligatory
            a valid iri of a node to remove.

        Returns
        ------
        bool
            True if an element has been deleted and False otherwise
        """
        # creating backup of the node
        node_info = self.fetch_node_with_iri(node_iri)
        dump_path = os.path.join(self.node_log_dir, f"{node_iri.rsplit('/')[-1]}.json")
        with open(dump_path, 'w') as fp:
            json.dump(node_info, fp)

        if not validators.url(node_iri):
            raise Exception("Sorry, the target IRI is not a valid URL.")

        payload = json.dumps({
            "query": {
                "$domain": self.DTP_CONFIG.get_domain(),
                "$iri": node_iri
            }
        })

        response = self.post_guarded_request(payload=payload, url=self.DTP_CONFIG.get_api_url('delete_avatar_iri'))
        if not self.simulation_mode:
            if response.ok:
                logger_global.info("The node: " + node_iri + ", has been deleted.")
                if self.session_logger is not None:
                    self.session_logger.info(f"DTP_API - DELETE_NODE_IRI: {node_iri}, {dump_path}")
                return True
            else:
                logger_global.error(
                    "The node: " + node_iri + ", cannot be deleted. Status code: " + str(response.status_code))
                return False
        return True

    def unlink_node_from_blob(self, node_uuid, blob_uuid):
        """
        The method unlinks a blob from a node.

        Parameters
        ----------
        node_uuid : str, obligatory
            UUID of a node from which the blob
            identified by blob_uuid will be unlinked
        blob_uuid : str, obligatory
            a valid uuid of a blob to be unlinked from
            the node identified by node_uuid

        Returns
        ------
        bool
            True if a blob has been unlinked and False otherwise
        """

        payload = json.dumps({
            "blob_uuid": blob_uuid,
            "avatar_uuids": [node_uuid],
            "ignore_conflicts": False
        })

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + self.DTP_CONFIG.get_token()
        }

        session = requests.Session()
        req = requests.Request("POST", self.DTP_CONFIG.get_api_url('unlink_blob'), headers=headers, data=payload)
        prepared = req.prepare()

        logger_global.info('HTTP request: \n' + self.pretty_http_request_to_string(prepared))

        if not self.simulation_mode:
            response = session.send(prepared)
            logger_global.info('Response code: ' + str(response.status_code))

            if response.ok:
                logger_global.info("The blob : " + blob_uuid + ", unlinked from the element: " + node_uuid)
                return True
            else:
                logger_global.error(
                    "Unlinking blob : " + blob_uuid + ", from the element: " + node_uuid + ",  failed. Status code: " + str(
                        response.status_code))
                return False
        return True

    def unlink_element_type(self, node_iri, target_iri):
        """
        Unlink element type from a node

        Parameters
        ----------
        node_iri: str, obligatory
            an iri of a node
        target_iri: str, obligatory
            an iri of a target linked node

        Returns
        -------
        bool
            True if the node is unlinked and False otherwise
        """
        payload = json.dumps([{
            "_domain": self.DTP_CONFIG.get_domain(),
            "_iri": node_iri,
            "_outE": [
                {
                    "_label": self.DTP_CONFIG.get_ontology_uri('hasElementType'),
                    "_targetIRI": target_iri
                }
            ]
        }])
        response = self.put_guarded_request(payload=payload, url=self.DTP_CONFIG.get_api_url('update_unset'))
        if not self.simulation_mode:
            if response.ok:
                logger_global.info(f"Removed link {self.DTP_CONFIG.get_ontology_uri('hasElementType')} from {node_iri} "
                                   f"to {target_iri}")
                return True
            else:
                logger_global.error("Unlink nodes failed. Response code: " + str(response.status_code))
                return False
        return True

    def unlink_task_type(self, node_iri, target_iri):
        """
        Unlink task type from a node

        Parameters
        ----------
        node_iri: str, obligatory
            an iri of a node
        target_iri: str, obligatory
            an iri of a target linked node

        Returns
        -------
        bool
            True if the node is unlinked and False otherwise
        """
        payload = json.dumps([{
            "_domain": self.DTP_CONFIG.get_domain(),
            "_iri": node_iri,
            "_outE": [
                {
                    "_label": self.DTP_CONFIG.get_ontology_uri('hasTaskType'),
                    "_targetIRI": target_iri
                }
            ]
        }])
        response = self.put_guarded_request(payload=payload, url=self.DTP_CONFIG.get_api_url('update_unset'))
        if not self.simulation_mode:
            if response.ok:
                logger_global.info(f"Removed link {self.DTP_CONFIG.get_ontology_uri('hasTaskType')} from {node_iri} "
                                   f"to {target_iri}")
                return True
            else:
                logger_global.error("Unlink nodes failed. Response code: " + str(response.status_code))
                return False
        return True

    def delete_blob_from_platform(self, blob_uuid):
        """
        The method deletes a blob from DTP

        Parameters
        ----------
        blob_uuid : str, obligatory
            a valid uuid of a blob to remove.

        Returns
        ------
        bool
            True if a blob has been deleted and False otherwise
        """

        payload = ""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + self.DTP_CONFIG.get_token()
        }

        session = requests.Session()
        req = requests.Request("DELETE", self.DTP_CONFIG.get_api_url('delete_blob', blob_uuid), headers=headers,
                               data=payload)
        prepared = req.prepare()

        logger_global.info('HTTP request: \n' + self.pretty_http_request_to_string(prepared))

        if not self.simulation_mode:
            response = session.send(prepared)
            logger_global.info('Response code: ' + str(response.status_code))

            if response.ok:
                logger_global.error("The blob: " + blob_uuid + ", has been deleted.")
                return True
            else:
                logger_global.error(
                    "The blob: " + blob_uuid + ", cannot be deleted. Status code: " + str(response.status_code))
                return False
        return True

    def unlink_constr_op(self, constr_node_iri, list_of_operation_iri):
        """
        Unlink construction and operation node

        Parameters
        ----------
        constr_node_iri : str, obligatory
            a valid construction IRI
        list_of_operation_iri : list, obligatory
            list of connected operation iri

        Returns
        -------
        bool
            True if the node is unlinked and False otherwise
        """
        # create out edges list of dictionaries
        out_edge_to_operation = []
        for operation_iri in list_of_operation_iri:
            out_edge_dict = {
                "_label": self.DTP_CONFIG.get_ontology_uri('hasOperation'),
                "_targetIRI": operation_iri
            }
            out_edge_to_operation.append(out_edge_dict)

        payload = json.dumps([{
            "_domain": self.DTP_CONFIG.get_domain(),
            "_iri": constr_node_iri,
            "_outE": [
                *out_edge_to_operation
            ]
        }])
        response = self.put_guarded_request(payload=payload, url=self.DTP_CONFIG.get_api_url('update_unset'))
        if not self.simulation_mode:
            if response.ok:
                logger_global.info(
                    f"Removed link {self.DTP_CONFIG.get_ontology_uri('hasOperation')} from {constr_node_iri} "
                    f"to {list_of_operation_iri}")
                return True
            else:
                logger_global.error("Unlink nodes failed. Response code: " + str(response.status_code))
                return False
        return True

    def unlink_operation_action(self, oper_node_iri, list_of_action_iri):
        """
        Unlink construction and operation node

        Parameters
        ----------
        oper_node_iri : str, obligatory
            a valid operation IRI
        list_of_action_iri : list, optional
            list of connection actions iri

        Returns
        -------
        bool
            True if the node is unlinked and False otherwise
        """
        # create out edges list of dictionaries
        out_edge_to_actions = []
        for action_iri in list_of_action_iri:
            out_edge_dict = {
                "_label": self.DTP_CONFIG.get_ontology_uri('hasAction'),
                "_targetIRI": action_iri
            }
            out_edge_to_actions.append(out_edge_dict)

        payload = json.dumps([{
            "_domain": self.DTP_CONFIG.get_domain(),
            "_iri": oper_node_iri,
            "_outE": [
                *out_edge_to_actions
            ]
        }])
        response = self.put_guarded_request(payload=payload, url=self.DTP_CONFIG.get_api_url('update_unset'))
        if not self.simulation_mode:
            if response.ok:
                logger_global.info(
                    f"Removed link {self.DTP_CONFIG.get_ontology_uri('hasOperation')} from {oper_node_iri} "
                    f"to {list_of_action_iri}")
                return True
            else:
                logger_global.error("Unlink nodes failed. Response code: " + str(response.status_code))
                return False
        return True


    def unlink_action_asbuilt(self, action_node_iri, target_asbuilt_iri):
        """
        Unlink action and asbuilt node

        Parameters
        ----------
        action_node_iri : str, obligatory
            a valid action IRI
        target_asbuilt_iri : list, optional
            target asbuilt iri

        Returns
        -------
        bool
            True if the node is unlinked and False otherwise
        """

        payload = json.dumps([{
            "_domain": self.DTP_CONFIG.get_domain(),
            "_iri": action_node_iri,
            "_outE": [
                {
                    "_label": self.DTP_CONFIG.get_ontology_uri('hasTarget'),
                    "_targetIRI": target_asbuilt_iri
                }
            ]
        }])
        response = self.put_guarded_request(payload=payload, url=self.DTP_CONFIG.get_api_url('update_unset'))
        if not self.simulation_mode:
            if response.ok:
                logger_global.info(
                    f"Removed link {self.DTP_CONFIG.get_ontology_uri('hasTarget')} from {action_node_iri} "
                    f"to {target_asbuilt_iri}")
                return True
            else:
                logger_global.error("Unlink nodes failed. Response code: " + str(response.status_code))
                return False
        return True

    def delete_asdesigned_param_node(self, node_iri):
        """
        The method removes isAsDesigned field from node identified with node_iri

        Parameters
        ----------
        node_iri: str, obligatory
            an iri of a node to act on

        Returns
        -------
        bool
            True if a blob has been node has been updated and False otherwise
        """
        payload = json.dumps([{
            "_domain": self.DTP_CONFIG.get_domain(),
            "_iri": node_iri,
            self.DTP_CONFIG.get_ontology_uri('isAsDesigned'): "delete"
            # 'delete' is a placeholder to ensure payload is valid
        }])

        response = self.put_guarded_request(payload=payload, url=self.DTP_CONFIG.get_api_url('update_unset'))
        if not self.simulation_mode:
            if response.ok:
                logger_global.info(f"The asDesigned fields is removed from element: {node_iri}")
                return True
            else:
                logger_global.error("Updating nodes failed. Response code: " + str(response.status_code))
                return False
        return True

    def revert_node_update(self, node_iri, dump_path):
        """
        Method to revert a node from logged node json file

        Parameters
        ----------
        node_iri: str, obligatory
            an iri of a node to act on
        dump_path: str, obligatory
            path to logged node json file

        Returns
        -------
        bool
            True if node has been updated and False otherwise
        """
        with open(dump_path) as f:
            node_info = json.load(f)

        payload = node_info['items'][0]
        response = self.put_guarded_request(payload=payload, url=self.DTP_CONFIG.get_api_url('update_set'))
        if not self.simulation_mode:
            if response.ok:
                logger_global.info(f"Revert node: {node_iri}")
                return True
            else:
                logger_global.error(
                    "Revert updating node failed. Response code: " + str(response.status_code))
                return False
        return True
