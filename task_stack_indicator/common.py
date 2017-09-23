# -*- coding: utf-8 -*-
#
# Copyright 2017 David García Goñi
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

from gi.repository import Gtk
import pkg_resources

TASKS_URL = 'tasks_url'
TASKS_USERNAME = 'tasks_username'
TASKS_PASSWORD = 'tasks_password'
JIRA_URL = 'jira_url'
JIRA_USERNAME = 'jira_username'
JIRA_PASSWORD = 'jira_password'
REFRESH_PERIOD = 'refresh_period'
DUE_DAYS = 'due_days'
WATCHING = 'watching_days'
TASK_LIMIT = 'task_limit'
ID = 'id'
SUMMARY = 'summary'
DESCRIPTION = 'description'
IMAGE_URL = 'image_url'
NAME = 'name'

GLADE_FILE = pkg_resources.resource_filename(__name__, 'resources/gui.glade')

def new_gtk_builder():
    builder = Gtk.Builder()
    builder.add_from_file(GLADE_FILE)
    return builder

def new_config():
    return { TASKS_URL: '', TASKS_USERNAME: '', TASKS_PASSWORD: '', TASK_LIMIT: 7, JIRA_URL : '', JIRA_USERNAME: '', JIRA_PASSWORD: '', REFRESH_PERIOD: 5, DUE_DAYS: 15, WATCHING: 7 }

builder = new_gtk_builder()
