# -*- coding: utf-8 -*-
#
# Copyright 2016 David García Goñi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import requests
from requests.exceptions import ConnectionError
import json

logger = logging.getLogger(__name__)

def get_tasks(url, username, password, headers=None):
    auth = (username, password)
    try:
        response = requests.get(url, auth=auth, headers=headers, verify=False)
        if response.status_code != 200:
            raise RestException(response.status_code, response.reason, response.text)
        else:
            return response.json()
    except ConnectionError as e:
        logger.error(e)
        logger.error("Error while connecting to " + url)
        return []

def create_task(url, username, password, task, headers=None):
    auth = (username, password)
    try:
        data = json.dumps(task)
        response = requests.post(url, auth=auth, headers=headers, data=data, verify=False)
        if response.status_code != 200:
            raise RestException(response.status_code, response.reason, response.text)
    except ConnectionError as e:
        logger.error(e)
        logger.error("Error while connecting to " + url)

def update_task(url, username, password, task, headers=None):
    auth = (username, password)
    try:
        data = json.dumps(task)
        response = requests.put(url, auth=auth, headers=headers, data=data, verify=False)
        if response.status_code != 200:
            raise RestException(response.status_code, response.reason, response.text)
    except ConnectionError as e:
        logger.error(e)
        logger.error("Error while connecting to " + url)

def delete_task(url, username, password, headers=None):
    auth = (username, password)
    try:
        response = requests.delete(url, auth=auth, headers=headers, verify=False)
        if response.status_code != 200:
            raise RestException(response.status_code, response.reason, response.text)
    except ConnectionError as e:
        logger.error(e)
        logger.error("Error while connecting to " + url)

class RestException(Exception):

    def __init__(self, code, reason, text):
        self.code = code
        self.reason = reason
        self.text = text
