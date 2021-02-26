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

import gi
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3 as AppIndicator
from gi.repository import Gtk
from gi.repository import GLib
from threading import Thread
from threading import Lock
from datetime import datetime
import json
import webbrowser
from os import makedirs
from os.path import expanduser
from os.path import exists
import logging
import locale
import gettext
from gettext import gettext as _
import pkg_resources
from task_stack_indicator.windows import PreferencesWindow
from task_stack_indicator.windows import CreateTaskWindow
from task_stack_indicator.windows import EditTaskWindow
from task_stack_indicator.windows import IssueFieldsTaskWindow
import task_stack_indicator.common as common
import task_stack_indicator.jira_client as jira_client
from task_stack_indicator.jira_client import JiraClient
from task_stack_indicator.simple_rest_client import RestException
import task_stack_indicator.simple_rest_client as src
import sys
import getopt

APP_NAME = 'task-stack-indicator'
locale.textdomain(APP_NAME)
gettext.textdomain(APP_NAME)

version = pkg_resources.get_distribution('TaskStackIndicator').version

CONFIG_DIR = expanduser("~") + "/." + APP_NAME
if not exists(CONFIG_DIR):
    makedirs(CONFIG_DIR)
CONFIG_FILE = CONFIG_DIR + "/config"
DATA_FILE = CONFIG_DIR + "/tasks"


STATUS_ICON_FILE = 'task-stack-indicator-%d-symbolic'


def print_help():
    print ('Usage: {:s} [-v]'.format(APP_NAME))


log_level = logging.INFO

try:
    opts, args = getopt.getopt(sys.argv[1:], "hv")
except getopt.GetoptError:
    print_help()
    sys.exit(1)
for opt, arg in opts:
    if opt == '-h':
        print_help()
        sys.exit()
    elif opt == '-v':
        log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


class Indicator(object):

    def __init__(self):
        self.indicator = AppIndicator.Indicator.new(APP_NAME,
                                                    STATUS_ICON_FILE % 0,
                                                    AppIndicator.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.config = common.new_config()
        self.tasks = []
        # TODO: move to jira_client.
        # This is needed to avoid JIRA to disable the account if the maximum tries has been reached
        self.authorized = True
        self.load_config()
        self.in_progress = []
        self.in_due = []
        self.not_planned = []
        self.watched = []
        self.projects = []
        self.issue_types = []
        self.lock = Lock()
        self.edit_task_windows = {}
        self.create_task_window = CreateTaskWindow(self)
        self.configuration_window = PreferencesWindow(self)
        self.indicator.connect(
            'new-icon', lambda indicator: GLib.idle_add(self.update_menu))
        self.about_dialog = common.builder.get_object('about_dialog')
        self.about_dialog.set_position(Gtk.WindowPosition.CENTER)
        self.about_dialog.set_version(version)
        self.about_dialog.connect(
            'delete_event', lambda widget, event: widget.hide() or True)
        self.jira_client = JiraClient()
        self.update_icon_and_menu()

    def load_config(self):
        logger.debug('Reading config file...')
        try:
            file = open(CONFIG_FILE, 'r')
            self.config = json.loads(file.read())
            logger.debug('Tasks file readed')
        except IOError as e:
            self.save_config()
            logger.error('Error while reading config file')
        else:
            file.close()

    def load_tasks(self):
        if self.config[common.TASKS_URL]:
            logger.debug('Loading remote tasks...')
            self.tasks = src.get_tasks(
                self.config[common.TASKS_URL], self.config[common.TASKS_USERNAME], self.config[common.TASKS_PASSWORD])
            self.tasks = sorted(
                self.tasks, key=lambda task: task[common.SUMMARY])
            for task in self.tasks:
                task['image_url'] = None
        else:
            logger.debug('Loading local tasks...')
            with self.lock:
                try:
                    file = open(DATA_FILE, 'r')
                    self.tasks = json.loads(file.read())
                    logger.debug('Tasks file readed')
                except IOError as e:
                    logger.error('Error while reading tasks file')
                else:
                    file.close()

    def load_in_progress_issues(self):
        self.in_progress = self.load_jira_issues(jira_client.IN_PROGRESS_JQL)

    def load_in_due_issues(self):
        jql = jira_client.IN_DUE_JQL.format(self.config[common.DUE_DAYS])
        self.in_due = self.load_jira_issues(jql)

    def load_not_planned_issues(self):
        self.not_planned = self.load_jira_issues(jira_client.NOT_PLANNED_JQL)

    def load_watched_issues(self):
        jql = jira_client.WATCHED_JQL.format(self.config[common.WATCHING])
        self.watched = self.load_jira_issues(jql)

    def load_jira_issues(self, jql):
        issues = []
        jira_url = self.config[common.JIRA_URL]
        if self.is_jira_enabled():
            try:
                issues = self.jira_client.get_issues(
                    jira_url, self.config[common.JIRA_USERNAME], self.config[common.JIRA_PASSWORD], jql)
            except RestException as e:
                self.process_rest_exception(e)
        return issues

    def process_rest_exception(self, exception):
        if exception.code == 401:
            self.authorized = False
        message = "Error {:d} ({:s}) while connecting to url: {:s}".format(
            exception.code, exception.reason, exception.text)
        logger.error(message)

    def update_icon_and_menu(self):
        total_in_progress = len(self.in_progress) + len(self.tasks)
        total = min(round(total_in_progress * 5.0 /
                          self.config[common.TASK_LIMIT]), 5)
        icon = STATUS_ICON_FILE % total
        if icon != self.indicator.get_icon():
            # This will trigger a call to update_menu
            logger.debug('Setting icon to {:s}...'.format(icon))
            self.indicator.set_icon(icon)
        else:
            GLib.idle_add(self.update_menu)

    def update_menu(self):
        menu = Gtk.Menu()

        if self.tasks:
            self.add_tasks_to_menu(
                menu, self.tasks, self.show_edit_task_window)
            separator = Gtk.SeparatorMenuItem()
            separator.show()
            menu.append(separator)

        if self.in_progress:
            self.add_tasks_to_menu(menu, self.in_progress, self.open_url)

        if self.is_jira_enabled():
            due = self.config[common.DUE_DAYS]
            if due > 0:
                self.add_sub_menu(
                    menu, _('Tasks with due date in n days').format(due), self.in_due)

            self.add_sub_menu(menu, _('Non planned tasks'), self.not_planned)

            watching = self.config[common.WATCHING]
            if watching > 0:
                self.add_sub_menu(menu, _('Watched tasks updated in the last n days').format(
                    watching), self.watched)

            if self.in_due or self.not_planned or self.watched:
                separator = Gtk.SeparatorMenuItem()
                separator.show()
                menu.append(separator)

        self.add_item(menu, Gtk.STOCK_ADD,
                      lambda widget: self.show_create_task_window())

        self.add_item(menu, Gtk.STOCK_REFRESH,
                      lambda widget: self.force_update_interface())

        self.add_item(menu, Gtk.STOCK_PREFERENCES,
                      lambda widget: self.configuration_window.open())

        separator = Gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        self.add_item(menu, Gtk.STOCK_ABOUT, lambda widget: self.show_about())

        separator = Gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        self.add_item(menu, Gtk.STOCK_QUIT, lambda widget: self.exit())

        self.indicator.set_menu(menu)

    def add_sub_menu(self, menu, msg, tasks):
        item = Gtk.ImageMenuItem(msg)
        item.show()
        item.set_submenu(Gtk.Menu())
        menu.append(item)
        self.add_tasks_to_menu(item.get_submenu(), tasks, self.open_url)
        item.set_sensitive(tasks)

    def add_item(self, menu, text, l):
        item = Gtk.ImageMenuItem.new_from_stock(text)
        item.connect("activate", l)
        item.show()
        menu.append(item)

    def show_create_task_window(self):
        if not self.create_task_window.window.props.visible:
            self.create_task_window.set_data('', '')
        self.create_task_window.window.present()

    def get_task_by_id(self, id):
        task_found = None
        for task in self.tasks:
            if task[common.ID] == id:
                task_found = task
                break
        return task_found

    def show_edit_task_window(self, widget, id):
        task = self.get_task_by_id(id)
        edit_task_window = self.edit_task_windows.get(id)
        if edit_task_window:
            if not edit_task_window.window.props.visible:
                edit_task_window.set_data(
                    task[common.SUMMARY], task[common.DESCRIPTION])
                edit_task_window.update_upload_button()
        else:
            edit_task_window = EditTaskWindow(self, task)
            self.edit_task_windows[id] = edit_task_window
        edit_task_window.window.present()

    def open_url(self, widget, url):
        webbrowser.open_new_tab(url)

    def get_image(self, image_url):
        return self.pixbufs.get(image_url)

    def add_tasks_to_menu(self, menu, tasks, callback):
        for task in tasks:
            item = Gtk.ImageMenuItem(task[common.SUMMARY])
            image_url = task[common.IMAGE_URL]
            if image_url:
                pixbuf = self.jira_client.get_image(image_url)
                image = Gtk.Image()
                image.set_from_pixbuf(pixbuf)
                item.set_image(image)
                item.set_always_show_image(True)
            item.connect('activate', callback, task.get(common.ID))
            item.show()
            menu.append(item)

    def force_update_interface(self):
        self.authorized = True
        self.update_interface_in_background()

    def update_interface_in_background(self):
        Thread(target=self.update_interface).start()

    def update_interface(self):
        self.load_tasks()
        self.load_watched_issues()
        self.load_in_due_issues()
        self.load_in_progress_issues()
        self.load_not_planned_issues()
        self.load_projects()
        self.load_issue_types()
        self.update_icon_and_menu()

    def update_periodically(self):
        self.update_interface_in_background()
        ms = self.config[common.REFRESH_PERIOD] * 60000
        GLib.timeout_add(ms, self.update_periodically)

    def save_tasks(self):
        fd = open(DATA_FILE, 'w')
        fd.write(json.dumps(self.tasks))
        fd.close()

    def save_config(self):
        fd = open(CONFIG_FILE, 'w')
        fd.write(json.dumps(self.config))
        fd.close()

    def create_task(self, summary, description):
        self.create_task_window.window.hide()
        if self.config[common.TASKS_URL]:
            logger.debug('Creating remote task...')
            task = {common.SUMMARY: summary, common.DESCRIPTION: description}
            new_task = src.create_task(
                self.config[common.TASKS_URL], self.config[common.TASKS_USERNAME], self.config[common.TASKS_PASSWORD], task)
            new_task[common.IMAGE_URL] = None
            self.load_tasks()
        else:
            logger.debug('Creating local task...')
            next_task_id = -1
            for t in self.tasks:
                if t[common.ID] > next_task_id:
                    next_task_id = t[common.ID]
            next_task_id += 1
            new_task = {common.IMAGE_URL: None, common.SUMMARY: summary,
                        common.ID: next_task_id, common.DESCRIPTION: description}
            with self.lock:
                self.tasks.append(new_task)
                self.tasks = sorted(
                    self.tasks, key=lambda task: task[common.SUMMARY])
                self.save_tasks()
        self.update_icon_and_menu()

    def update_task(self, id, summary, description):
        self.edit_task_windows.pop(id).window.hide()
        if self.config[common.TASKS_URL]:
            logger.debug('Updating remote task...')
            task = {common.SUMMARY: summary, common.DESCRIPTION: description}
            src.update_task(self.config[common.TASKS_URL] + '/' + id,
                            self.config[common.TASKS_USERNAME], self.config[common.TASKS_PASSWORD], task)
            self.load_tasks()
        else:
            logger.debug('Updating local task...')
            with self.lock:
                task = self.get_task_by_id(id)
                task[common.SUMMARY] = summary
                task[common.DESCRIPTION] = description
                self.save_tasks()
        self.update_icon_and_menu()

    def delete_task(self, id):
        self.edit_task_windows.pop(id).window.hide()
        if self.config[common.TASKS_URL]:
            logger.debug('Deleting remote task...')
            src.delete_task(self.config[common.TASKS_URL] + '/' + id,
                            self.config[common.TASKS_USERNAME], self.config[common.TASKS_PASSWORD])
            self.load_tasks()
        else:
            logger.debug('Deleting local task...')
            with self.lock:
                self.tasks.remove(self.get_task_by_id(id))
                self.save_tasks()
        self.update_icon_and_menu()

    def load_projects(self):
        jira_url = self.config[common.JIRA_URL]
        if self.is_jira_enabled():
            try:
                self.projects = self.jira_client.get_projects(
                    jira_url, self.config[common.JIRA_USERNAME], self.config[common.JIRA_PASSWORD])
            except RestException as e:
                self.process_rest_exception(e)

    def load_issue_types(self):
        jira_url = self.config[common.JIRA_URL]
        if self.is_jira_enabled():
            try:
                self.issue_types = self.jira_client.get_issue_types(
                    jira_url, self.config[common.JIRA_USERNAME], self.config[common.JIRA_PASSWORD])
            except RestException as e:
                self.process_rest_exception(e)

    def is_jira_enabled(self):
        jira_url = self.config[common.JIRA_URL]
        return jira_url and self.authorized

    def show_about(self):
        self.about_dialog.show()
        self.about_dialog.present()

    def exit(self):
        Gtk.main_quit()

    def main(self):
        self.update_periodically()
        Gtk.main()


if __name__ == "__main__":
    Indicator().main()
