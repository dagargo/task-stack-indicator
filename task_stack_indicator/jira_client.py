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
from threading import Lock
from gi.repository import GdkPixbuf
from task_stack_indicator.simple_rest_client import RestException

logger = logging.getLogger(__name__)
headers = {"Content-Type": "application/json", "Accept" : "application/json"}

IN_PROGRESS_JQL = 'assignee = currentUser() AND status = \'In progress\' ORDER BY priority DESC'
NOT_PLANNED_JQL = 'assignee = currentUser() AND (duedate is EMPTY OR fixVersion is EMPTY) AND status != Closed ORDER BY priority DESC'
WATCHED_JQL = 'watcher = currentUser() AND updatedDate > -{:d}d ORDER BY updatedDate DESC'
IN_DUE_JQL = 'assignee = currentUser() AND status != Closed AND duedate < {:d}d ORDER BY duedate ASC, priority DESC'
CREATE_ISSUE_URL = '{:s}/secure/CreateIssueDetails!init.jspa?pid={:s}&issuetype={:s}&summary={:s}&description={:s}&assignee={:s}&reporter={:s}'

def get_new_issue_url(jira_url, project_id, issue_type_id, summary, description, user):
    return CREATE_ISSUE_URL.format(jira_url, project_id, issue_type_id, summary, description, user, user)

class JiraClient(object):

    def __init__(self):
        self.pixbufs = {}
        self.lock = Lock()

    def get_issues(self, jira_url, username, password, jql):
        issues = []
        jql_url = jira_url + "/rest/api/2/search?jql=" + jql
        auth = (username, password)
        try:
            response = requests.get(jql_url, auth=auth, headers=headers)
            if response.status_code != 200:
                raise RestException(response.status_code, response.reason, response.text)
            else:
                for issue in response.json().get("issues"):
                    fields = issue.get("fields")
                    priority = fields.get("priority")
                    if priority:
                        image_url = priority.get("iconUrl")
                    else:
                        issue_type = fields.get("issuetype")
                        if issue_type:
                            image_url = issue_type.get("iconUrl")
                        else:
                            image_url = None
                    key = issue.get("key")
                    summary = key + " - " + fields.get("summary")
                    url = jira_url + "/browse/" + key
                    issue = {"image_url": image_url, "summary" : summary, "id" : url}
                    if image_url:
                        with self.lock:
                            pixbuf = self.pixbufs.get(image_url)
                            if not pixbuf:
                                response = requests.get(image_url)
                                loader = GdkPixbuf.PixbufLoader()
                                loader.write(response.content)
                                loader.close()
                                pixbuf = loader.get_pixbuf()
                                self.pixbufs[image_url] = pixbuf
                    issues.append(issue)
        except ConnectionError as e:
            logger.error("Error while connecting to JIRA")
        return issues

    def get_image(self, image_url):
        return self.pixbufs.get(image_url)

    def create_issue(self, jira_url, username, password, issue):
        post_url = jira_url + "/rest/api/2/issue"
        auth = (username, password)
        entity = None
        try:
            response = requests.post(post_url, auth=auth, headers=headers, data=issue)
            if response.status_code != 201:
                raise RestException(response.status_code, response.reason, response.text)
            else:
                entity = response.json()
        except ConnectionError as e:
            logger.error("Error while connecting to JIRA")
        return entity

    def get_simple_items(self, url, username, password):
        items = []
        auth = (username, password)
        try:
            response = requests.get(url, auth=auth, headers=headers)
            if response.status_code != 200:
                raise RestException(response.status_code, response.reason, response.text)
            else:
                for i in response.json():
                    id = i.get("id")
                    name = i.get("name")
                    item = { "id": id, "name": name}
                    items.append(item)
        except ConnectionError as e:
            logger.error("Error while connecting to JIRA")
        return items

    def get_issue_types(self, jira_url, username, password):
        return self.get_simple_items(jira_url + "/rest/api/2/issuetype", username, password)

    def get_projects(self, jira_url, username, password):
        return self.get_simple_items(jira_url + "/rest/api/2/project", username, password)
