#!/usr/bin/env python3
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
#
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
from jql_jira_client import JqlJiraClient
from jql_jira_client import UnauthorizedException

logger = logging.getLogger(__name__)

NAME = "task-stack-indicator"

CONFIG_DIR = expanduser("~") + "/." + NAME
if not exists(CONFIG_DIR):
    makedirs(CONFIG_DIR)
LOCALE_DIR = "/usr/local/share/" + NAME + "/locale"
GLADE_FILE = "/usr/local/share/" + NAME + "/gui.glade"
CONFIG_FILE = CONFIG_DIR + "/config"
DATA_FILE = CONFIG_DIR + "/tasks"

locale.bindtextdomain(NAME, LOCALE_DIR)
locale.textdomain(NAME)
_ = locale.gettext

IN_PROGRES_JQL = "assignee = currentUser() AND status = 'In progress' ORDER BY priority DESC"
WATCHED_JQL = "watcher = currentUser() AND updatedDate > -{:d}d ORDER BY updatedDate DESC"
IN_DUE_JQL = "assignee = currentUser() AND status != Closed AND duedate < {:d}d ORDER BY priority DESC, duedate DESC"
NOT_PLANNED_JQL = "assignee = currentUser() AND (duedate is EMPTY OR fixVersion is EMPTY) AND status != Closed ORDER BY priority DESC"
ICON_FILE = "/usr/share/icons/Humanity/apps/22/level3.svg"

JIRA_URL = "jira_url"
USERNAME = "username"
PASSWORD = "password"
REFRESH = "refresh_period"
DUE_DATE = "due_days"
WATCHING = "watching_days"
TASK_LIMIT = "task_limit"
NEXT_TASK_ID = "next_task_id"
TASKS = "tasks"
ID = "id"
SUMMARY = "summary"
DESCRIPTION = "description"
IMAGE_URL = "image_url"

class TaskStackIndicator(object):

    def __init__(self):
        self.indicator = AppIndicator.Indicator.new(NAME,
                                                "level0",
                                                AppIndicator.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.config = { TASK_LIMIT: 7, JIRA_URL : "", USERNAME: "", PASSWORD: "", REFRESH: 5, DUE_DATE: 15, WATCHING: 7 }
        self.tasks = { NEXT_TASK_ID : 0, TASKS : []}
        self.authorized = True
        self.load_config()
        self.in_progress = []
        self.in_due = []
        self.not_planned = []
        self.watched = []
        self.lock = Lock()
        self.load_tasks()
        file = open(GLADE_FILE, 'r')
        self.glade_contents = file.read()
        file.close()
        self.edit_task_windows = {}
        self.create_task_window = self.create_task_window = CreateTaskWindow(self)
        self.configuration_window = ConfigurationWindow(self)
        self.indicator.connect("new-icon", lambda indicator: GLib.idle_add(self.update_menu))
        self.update_icon_and_menu()
        self.jql_jira_client = JqlJiraClient()

    def load_config(self):
        logger.debug("Reading config file...")
        try:
            file = open(CONFIG_FILE, 'r')
            self.config = json.loads(file.read())
            logger.debug("Tasks file readed")
        except IOError as e:
            self.save_config()
            logger.error("Error while reading config file")
        else:
            file.close()

    def load_tasks(self):
        with self.lock:
            logger.debug("Reading tasks file...")
            try:
                file = open(DATA_FILE, 'r')
                self.tasks = json.loads(file.read())
                logger.debug("Tasks file readed")
            except IOError as e:
                self.save_tasks()
                logger.error("Error while reading tasks file")
            else:
                file.close()

    def load_in_progress_issues(self):
        self.in_progress = self.load_jira_issues(IN_PROGRES_JQL)

    def load_in_due_issues(self):
        jql = IN_DUE_JQL.format(self.config.get(DUE_DATE))
        self.in_due = self.load_jira_issues(jql)

    def load_not_planned_issues(self):
        self.not_planned = self.load_jira_issues(NOT_PLANNED_JQL)

    def load_watched_issues(self):
        jql = WATCHED_JQL.format(self.config.get(WATCHING))
        self.watched = self.load_jira_issues(jql)

    def load_jira_issues(self, jql):
        issues = []
        jira_url = self.config.get(JIRA_URL)
        if jira_url and self.authorized:
            try:
                issues = self.jql_jira_client.load_issues(jira_url, self.config.get(USERNAME), self.config.get(PASSWORD), jql)
            except UnauthorizedException as e:
                self.authorized = False
                logger.error("Unauthorized to log in JIRA")
        return issues

    def update_icon_and_menu(self):
        total_in_progress = len(self.in_progress) + len(self.tasks[TASKS])
        total = min(round(total_in_progress * 5.0 / self.config[TASK_LIMIT]), 5)
        icon = "level%d" % total
        if icon != self.indicator.get_icon():
            #This will trigger a call to update_menu
            self.indicator.set_icon(icon)
        else:
            GLib.idle_add(self.update_menu)

    def update_menu(self):
        menu = Gtk.Menu()

        if self.tasks.get(TASKS):
            self.add_tasks_to_menu(menu, self.tasks.get(TASKS), self.show_edit_task_window)
            separator = Gtk.SeparatorMenuItem()
            separator.show()
            menu.append(separator)

        if self.in_progress:
            self.add_tasks_to_menu(menu, self.in_progress, self.open_url)

        if self.config.get(JIRA_URL) and self.authorized:
            due = self.config[DUE_DATE]
            if due > 0:
                self.add_sub_menu(menu, _("Tasks with due date in n days").format(due), self.in_due)            

            self.add_sub_menu(menu, _("Non planned tasks"), self.not_planned)

            watching = self.config[WATCHING]
            if watching > 0:
                self.add_sub_menu(menu, _("Watched tasks updated in the last n days").format(watching), self.watched)

            if self.in_due or self.not_planned or self.watched:
	            separator = Gtk.SeparatorMenuItem()
	            separator.show()
	            menu.append(separator)

        self.add_item(menu, Gtk.STOCK_ADD, lambda widget: self.show_create_task_window())

        self.add_item(menu, Gtk.STOCK_REFRESH, lambda widget: self.force_update_interface())

        self.add_item(menu, Gtk.STOCK_PREFERENCES, lambda widget: self.configuration_window.open())

        separator = Gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        self.add_item(menu, Gtk.STOCK_QUIT, lambda widget: self.exit())

        self.indicator.set_menu(menu)
        
    def add_sub_menu(self, menu, msg, tasks):
        item = Gtk.ImageMenuItem(msg)
        item.show()
        item.set_submenu(Gtk.Menu())
        if tasks:
            self.add_tasks_to_menu(item.get_submenu(), tasks, self.open_url)
            menu.append(item)
            
    def add_item(self, menu, text, l):
        item = Gtk.ImageMenuItem.new_from_stock(text)
        item.connect("activate", l)
        item.show()
        menu.append(item)

    def show_create_task_window(self):
        if not self.create_task_window.window.props.visible:
            self.create_task_window.set_data("", "")
        self.create_task_window.window.present()

    def get_task_by_id(self, id):
        task_found = None
        for task in self.tasks[TASKS]:
            if task[ID] == id:
                task_found = task
                break
        return task_found

    def show_edit_task_window(self, widget, id):
        task = self.get_task_by_id(id)
        edit_task_window = self.edit_task_windows.get(id)
        if not edit_task_window:
            edit_task_window = EditTaskWindow(self, task)
            self.edit_task_windows[id] = edit_task_window
        else:
            if not edit_task_window.window.props.visible:
                edit_task_window.set_data(task[SUMMARY], task[DESCRIPTION])
        edit_task_window.window.present()

    def open_url(self, widget, url):
        webbrowser.open_new_tab(url)

    def add_tasks_to_menu(self, menu, tasks, callback):
        for task in tasks:
            item = Gtk.ImageMenuItem(task[SUMMARY])
            image_url = task[IMAGE_URL]
            if image_url:
                pixbuf = self.jql_jira_client.get_image(image_url)
            else:
                pixbuf = Gtk.IconTheme.get_default().load_icon("tomboy-panel", 22, Gtk.IconLookupFlags.FORCE_SVG)
            image = Gtk.Image()
            image.set_from_pixbuf(pixbuf)
            item.set_image(image)
            item.set_always_show_image(True);
            item.connect("activate", callback, task.get(ID))
            item.show()
            menu.append(item)

    def force_update_interface(self):
        self.authorized = True
        self.update_interface_in_background()

    def update_interface_in_background(self):
        Thread(target = self.update_interface).start()

    def update_interface(self):
        self.load_tasks()
        self.load_watched_issues()
        self.load_in_due_issues()
        self.load_in_progress_issues()
        self.load_not_planned_issues()
        self.update_icon_and_menu()

    def update_periodically(self):
        self.update_interface_in_background()
        ms = self.config[REFRESH] * 60000
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
        with self.lock:
            task_id = self.tasks[NEXT_TASK_ID]
            task = {IMAGE_URL: None, SUMMARY : summary, ID : task_id, DESCRIPTION : description}
            self.tasks[NEXT_TASK_ID] = task_id + 1
            self.tasks[TASKS].append(task)
            self.save_tasks()
        self.update_icon_and_menu()

    def update_task(self, id, summary, description):
        self.edit_task_windows.pop(id).window.hide()
        with self.lock:
            task = self.get_task_by_id(id)
            task[SUMMARY] = summary
            task[DESCRIPTION] = description
            self.save_tasks()
        self.update_icon_and_menu()

    def delete_task(self, id):
        self.edit_task_windows.pop(id).window.hide()
        with self.lock:
            self.tasks[TASKS].remove(self.get_task_by_id(id))
            self.save_tasks()
        self.update_icon_and_menu()

    def exit(self):
        Gtk.main_quit()

    def main(self):
        self.update_periodically()
        Gtk.main()

class TaskStackIndicatorGladeWindow(object):

    def __init__(self, task_stack_indicator, window_name):
        self.task_stack_indicator = task_stack_indicator
        self.builder = Gtk.Builder()
        self.builder.add_from_string(task_stack_indicator.glade_contents)
        self.window = self.builder.get_object(window_name)
        self.window.connect("delete-event", lambda widget, event: widget.hide() or True)
        self.window.set_icon_from_file(ICON_FILE)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        
class ConfigurationWindow(TaskStackIndicatorGladeWindow):

    def __init__(self, task_stack_indicator):
        super(ConfigurationWindow, self).__init__(task_stack_indicator, "config_window")
        self.cancel_button = self.builder.get_object("config_cancel_button")
        self.cancel_button.connect("clicked", lambda widget: self.window.hide())
        self.accept_button = self.builder.get_object("config_accept_button")
        self.spin_task_limit = self.builder.get_object(TASK_LIMIT)
        self.entry_jira_url = self.builder.get_object(JIRA_URL)
        self.entry_username = self.builder.get_object(USERNAME)
        self.entry_password = self.builder.get_object(PASSWORD)
        self.spin_refresh = self.builder.get_object(REFRESH)
        self.spin_due = self.builder.get_object(DUE_DATE)
        self.spin_watching = self.builder.get_object(WATCHING)
        self.accept_button.connect("clicked", lambda widget: self.save_config())
    
    def load(self):
        self.spin_task_limit.set_value(self.task_stack_indicator.config[TASK_LIMIT])
        self.entry_jira_url.set_text(self.task_stack_indicator.config[JIRA_URL])
        self.entry_username.set_text(self.task_stack_indicator.config[USERNAME])
        self.entry_password.set_text(self.task_stack_indicator.config[PASSWORD])
        self.spin_refresh.set_value(self.task_stack_indicator.config[REFRESH])
        self.spin_due.set_value(self.task_stack_indicator.config[DUE_DATE])
        self.spin_watching.set_value(self.task_stack_indicator.config[WATCHING])

    def open(self):
        if not self.window.props.visible:
            self.load()
        self.window.present()

    def save_config(self):
        self.window.hide()
        self.task_stack_indicator.config[TASK_LIMIT] = int(self.spin_task_limit.get_value())
        self.task_stack_indicator.config[JIRA_URL] = self.entry_jira_url.get_text()
        self.task_stack_indicator.config[USERNAME] = self.entry_username.get_text()
        self.task_stack_indicator.config[PASSWORD] = self.entry_password.get_text()
        self.task_stack_indicator.config[REFRESH] = int(self.spin_refresh.get_value())
        self.task_stack_indicator.config[DUE_DATE] = int(self.spin_due.get_value())
        self.task_stack_indicator.config[WATCHING] = int(self.spin_watching.get_value())
        self.task_stack_indicator.save_config()
        self.task_stack_indicator.authorized = True
        self.task_stack_indicator.update_interface_in_background()

class TaskWindow(TaskStackIndicatorGladeWindow):

    def __init__(self, task_stack_indicator):
        super(TaskWindow, self).__init__(task_stack_indicator, "task_window")
        self.cancel_button = self.builder.get_object("task_cancel_button")
        self.cancel_button.connect("clicked", lambda widget: self.window.hide())
        self.accept_button = self.builder.get_object("task_accept_button")
        self.accept_button.set_can_default(True)
        self.accept_button.grab_default()
        self.summary_entry = self.builder.get_object("task_summary")
        self.summary_entry.connect("changed", lambda editable: self.accept_button.set_sensitive(editable.get_text() != ""))
        self.summary_entry.set_activates_default(True)
        self.description_buffer = self.builder.get_object("description_buffer")
        self.delete_button = self.builder.get_object("task_delete_button")
        
    def set_data(self, summary, description):
        self.summary_entry.set_text(summary)
        self.description_buffer.set_text(description)        

class CreateTaskWindow(TaskWindow):

    def __init__(self, task_stack_indicator):
        super(CreateTaskWindow, self).__init__(task_stack_indicator)
        self.accept_button.set_sensitive(False)
        self.delete_button.hide()
        self.accept_button.connect("clicked", lambda widget: GLib.idle_add(self.task_stack_indicator.create_task, self.summary_entry.get_text(), self.description_buffer.get_text(self.description_buffer.get_start_iter(), self.description_buffer.get_end_iter(), True)))

class EditTaskWindow(TaskWindow):

    def __init__(self, task_stack_indicator, task):
        super(EditTaskWindow, self).__init__(task_stack_indicator)
        self.accept_button.connect("clicked", lambda widget: GLib.idle_add(self.task_stack_indicator.update_task, task[ID], self.summary_entry.get_text(), self.description_buffer.get_text(self.description_buffer.get_start_iter(), self.description_buffer.get_end_iter(), True)))
        self.delete_button.connect("clicked", lambda widget: GLib.idle_add(self.task_stack_indicator.delete_task, task[ID]))
        self.summary_entry.set_text(task.get(SUMMARY))
        description = task.get(DESCRIPTION)
        self.description_buffer.set_text(description)

if __name__ == "__main__":
    TaskStackIndicator().main()
