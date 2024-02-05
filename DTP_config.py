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

import os
import xml.etree.ElementTree as ET

import validators


class DTPConfig:
    """
    The class is used to map DTP configuration from an XML file.

    Attributes
    ----------
    version : str
        configuration file version
    token : str
        the developer token
    dtp_domain : str
        a domain URL
    api_uris : dictionary
        a map of the API uris
    ontology_uris : dictionary
        a map of the ontology uris        

    Methods
    -------
    get_api_uri(api_type, ID = ' ')
        if the type is a valid type from the XML configuration, then it returns the link,
        if the ID is provided, then the returned link will contain it
    get_ontology_uri(ontology_type)
        if the type is a valid type from the XML configuration, then it returns
        the corresponding ontology URI
    get_token()
        return the developer token
    get_kpi_domain()
        returns the KPI domain
    get_domain()
        returns the DTP domain
    get_version()
        returns the config. file version
    get_object_types()
        returns list, str, object types
    get_object_type_classes()
        returns list, str, object type classes
    get_object_type_conversion_map()
        returns dictionary, str, object type maps   
    """

    def __read_dev_token(self, input_dev_token_file):
        if not os.path.exists(input_dev_token_file):
            raise Exception("Sorry, the dev token file does not exist.")

        token = ''

        f = open(input_dev_token_file, "r")
        lines = f.readlines()

        for line in lines:
            token = token + line.rstrip(' \t\n\r')
        f.close()

        if len(token) == 0:
            raise Exception("Sorry, the dev token file seems to be empty.")

        return token

    def __map_api_urls(self, uris):
        for uri in uris:
            self.api_uris[uri.attrib['function'].strip(' \t\n\r')] = uri.text.strip(' \t\n\r')

    def __map_ontology_uris(self, uris):
        for uri in uris:
            self.ontology_uris[uri.attrib['function'].strip(' \t\n\r')] = uri.text.strip(' \t\n\r')

    def __init__(self, xml_path):
        config = ET.parse(xml_path).getroot()

        self.version = config.find('VERSION').text.strip(' \t\n\r')

        token_path = config.find('DEV_TOKEN').text.strip(' \t\n\r')
        self.token = self.__read_dev_token(token_path)

        self.dtp_domain = config.find('DTP_DOMAIN').text.strip(' \t\n\r')
        if not validators.url(self.dtp_domain):
            raise Exception("Sorry, the DTP domain URL is not a valid URL.")

        if self.dtp_domain[-1] != '/':
            self.dtp_domain = self.dtp_domain + '/'

        self.kpi_domain = config.find('KPI_DOMAIN').text.strip(' \t\n\r')
        if not validators.url(self.kpi_domain):
            raise Exception("Sorry, the DTP domain URL is not a valid URL.")

        if self.kpi_domain[-1] != '/':
            self.kpi_domain = self.kpi_domain + '/'

        self.log_dir = config.find('LOG_DIR').text.strip(' \t\n\r')
        assert self.log_dir != "/path/to/log/dir", "Please set LOG_DIR in DTP_config.xml"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.api_uris = {}
        uris = config.find('API_URLS')
        if not uris is None:
            self.__map_api_urls(uris)

        self.ontology_uris = {}
        uris = config.find('ONTOLOGY_URIS')
        if not uris is None:
            self.__map_ontology_uris(uris)

    def get_api_url(self, api_type, id=' '):
        if len(id.strip(' \t\n\r')) == 0:
            return self.api_uris[api_type]
        else:
            return self.api_uris[api_type].replace('_ID_', id)

    def get_ontology_uri(self, ontology_type):
        return self.ontology_uris[ontology_type]

    def get_token(self):
        return self.token

    def get_kpi_domain(self):
        return self.kpi_domain

    def get_domain(self):
        return self.dtp_domain

    def get_version(self):
        return self.version

    def get_log_path(self):
        return self.log_dir
