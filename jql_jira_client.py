# -*- coding: utf-8 -*-
#
# Copyright 2014 David García Goñi
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
from threading import Lock
from gi.repository import GdkPixbuf

logger = logging.getLogger(__name__)

class JqlJiraClient(object):

    def __init__(self):
        self.pixbufs = {}
        self.lock = Lock()

    def load_issues(self, jira_url, username, password, jql):
        issues = []
        jql_url = jira_url + "/rest/api/2/search?jql=" + jql
        auth = (username, password)
        try:
            response = requests.get(jql_url, auth=auth)
            if response.status_code == 401:
                raise UnauthorizedException()
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
                    summary = fields.get("summary")
                    url = jira_url + "/browse/" + issue.get("key")
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
        
class UnauthorizedException(Exception):
    pass
