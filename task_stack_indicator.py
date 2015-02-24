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
import os
import webbrowser
from os.path import expanduser
from os.path import exists
import logging
import locale
from jql_jira_client import JqlJiraClient
from jql_jira_client import UnauthorizedException

logger = logging.getLogger(__name__)

class TaskStackIndicator(object):

    NAME = "task-stack-indicator"
    DIR = expanduser("~") + "/." + NAME
    CONFIG_FILE = DIR + "/config"
    DATA_FILE = DIR + "/tasks"
    IN_PROGRES_JQL = "assignee = currentUser() AND status = 'In progress' ORDER BY priority DESC"
    WATCHED_JQL = "watcher = currentUser() AND updatedDate > -{:d}d ORDER BY updatedDate DESC"
    IN_DUE_JQL = "assignee = currentUser() AND status != Closed AND duedate < now() ORDER BY priority DESC, duedate DESC"
    LOCALE_DIR = "/usr/local/share/" + NAME + "/locale"
    GLADE_FILE = "/usr/local/share/" + NAME + "/gui.glade"
    ICON_FILE = "/usr/share/icons/Humanity/apps/22/level3.svg"

    def __init__(self):
        locale.bindtextdomain(TaskStackIndicator.NAME, TaskStackIndicator.LOCALE_DIR)
        locale.textdomain(TaskStackIndicator.NAME)
        self.indicator = AppIndicator.Indicator.new(TaskStackIndicator.NAME,
                                                "level0",
                                                AppIndicator.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.config = { "jira_url" : "", "username": "", "password": "", "refresh": 5, "window": 7}
        self.tasks = { "nextTaskId" : 0, "tasks" : []}
        if not exists(TaskStackIndicator.DIR):
            makedirs(TaskStackIndicator.DIR)
        self.authorized = True
        self.load_config()
        self.in_progress = []
        self.watched = []
        self.in_due = []
        self.lock = Lock()
        self.load_tasks()
        file = open(TaskStackIndicator.GLADE_FILE, 'r')
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
            file = open(TaskStackIndicator.CONFIG_FILE, 'r')
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
                file = open(TaskStackIndicator.DATA_FILE, 'r')
                self.tasks = json.loads(file.read())
                logger.debug("Tasks file readed")
            except IOError as e:
                self.save_tasks()
                logger.error("Error while reading tasks file")
            else:
                file.close()

    def load_in_progress_issues(self):
        self.in_progress = self.load_jira_issues(TaskStackIndicator.IN_PROGRES_JQL)

    def load_watched_issues(self):
        jql = TaskStackIndicator.WATCHED_JQL.format(self.config.get("window"))
        self.watched = self.load_jira_issues(jql)

    def load_in_due_issues(self):
        self.in_due = self.load_jira_issues(TaskStackIndicator.IN_DUE_JQL)

    def load_jira_issues(self, jql):
        issues = []
        jira_url = self.config.get("jira_url")
        if jira_url and self.authorized:
            try:
                issues = self.jql_jira_client.load_issues(jira_url, self.config.get("username"), self.config.get("password"), jql)
            except UnauthorizedException as e:
                self.authorized = False
                logger.error("Unauthorized to log in JIRA")
        return issues

    def update_icon_and_menu(self):
        total = min(len(self.in_progress) + len(self.tasks.get("tasks")), 5)
        icon = "level%d" % total
        if icon != self.indicator.get_icon():
            #This will trigger a call to update_menu
            self.indicator.set_icon(icon)
        else:
            GLib.idle_add(self.update_menu)

    def update_menu(self):

        menu = Gtk.Menu()

        if self.tasks.get("tasks"):
            self.add_tasks_to_menu(menu, self.tasks.get("tasks"), self.show_edit_task_window)
            separator = Gtk.SeparatorMenuItem()
            separator.show()
            menu.append(separator)

        if self.in_progress:
            self.add_tasks_to_menu(menu, self.in_progress, self.open_url)
            separator = Gtk.SeparatorMenuItem()
            separator.show()
            menu.append(separator)

        if self.config.get("jira_url") and self.authorized:
            item = Gtk.ImageMenuItem("Tasks with passed due date")
            item.show()
            item.set_submenu(Gtk.Menu())
            if self.in_due:
                self.add_tasks_to_menu(item.get_submenu(), self.in_due, self.open_url)
                menu.append(item)
                separator = Gtk.SeparatorMenuItem()
                separator.show()
                menu.append(separator)

            item = Gtk.ImageMenuItem("Watched tasks recently updated")
            item.show()
            item.set_submenu(Gtk.Menu())
            if self.watched:
                self.add_tasks_to_menu(item.get_submenu(), self.watched, self.open_url)
                menu.append(item)
                separator = Gtk.SeparatorMenuItem()
                separator.show()
                menu.append(separator)

        item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ADD)
        item.connect("activate", lambda widget: self.show_create_task_window())
        item.show()
        menu.append(item)

        item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_REFRESH)
        item.connect("activate", lambda widget: self.update_interface_in_background())
        item.show()
        menu.append(item)

        item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_PREFERENCES)
        item.connect("activate", lambda widget: self.configuration_window.open())
        item.show()
        menu.append(item)

        separator = Gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT)
        item.connect("activate", lambda widget: self.exit())
        item.show()
        menu.append(item)

        self.indicator.set_menu(menu)

    def show_create_task_window(self):
        if not self.create_task_window.window.props.visible:
            self.create_task_window.set_data("", "")
        self.create_task_window.window.present()

    def get_task_by_id(self, id):
        task_found = None
        for task in self.tasks["tasks"]:
            if task["id"] == id:
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
                edit_task_window.set_data(task.get("summary"), task.get("description"))
        edit_task_window.window.present()

    def open_url(self, widget, url):
        webbrowser.open_new_tab(url)

    def add_tasks_to_menu(self, menu, tasks, callback):
        for task in tasks:
            item = Gtk.ImageMenuItem(task.get("summary"))
            image_url = task.get("image_url")
            if image_url:
                pixbuf = self.jql_jira_client.get_image(image_url)
            else:
                pixbuf = Gtk.IconTheme.get_default().load_icon("tomboy-panel", 22, Gtk.IconLookupFlags.FORCE_SVG)
            image = Gtk.Image()
            image.set_from_pixbuf(pixbuf)
            item.set_image(image)
            item.set_always_show_image(True);
            item.connect("activate", callback, task.get("id"))
            item.show()
            menu.append(item)

    def update_interface_in_background(self):
        Thread(target = self.update_interface).start()

    def update_interface(self):
        self.load_tasks()
        self.load_watched_issues()
        self.load_in_due_issues()
        self.load_in_progress_issues()
        self.update_icon_and_menu()

    def update_periodically(self):
        self.update_interface_in_background()
        ms = self.config.get("refresh") * 60000
        GLib.timeout_add(ms, self.update_periodically)

    def save_tasks(self):
        fd = open(TaskStackIndicator.DATA_FILE, 'w')
        fd.write(json.dumps(self.tasks))
        fd.close()
        
    def save_config(self):
        fd = open(TaskStackIndicator.CONFIG_FILE, 'w')
        fd.write(json.dumps(self.config))
        fd.close()

    def create_task(self, summary, description):
        self.create_task_window.window.hide()
        self.create_task_window = None
        with self.lock:
            task_id = self.tasks["nextTaskId"]
            task = {"image_url": None, "summary" : summary, "id" : task_id, "description" : description}
            self.tasks["nextTaskId"] = task_id + 1
            self.tasks["tasks"].append(task)
            self.save_tasks()
        self.update_icon_and_menu()

    def update_task(self, id, summary, description):
        self.edit_task_windows.pop(id).window.hide()
        with self.lock:
            task = self.get_task_by_id(id)
            task["summary"] = summary
            task["description"] = description
            self.save_tasks()
        self.update_icon_and_menu()

    def delete_task(self, id):
        self.edit_task_windows.pop(id).window.hide()
        with self.lock:
            self.tasks["tasks"].remove(self.get_task_by_id(id))
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
        self.window.set_icon_from_file(TaskStackIndicator.ICON_FILE)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        
class ConfigurationWindow(TaskStackIndicatorGladeWindow):

    def __init__(self, task_stack_indicator):
        super(ConfigurationWindow, self).__init__(task_stack_indicator, "config_window")
        self.cancel_button = self.builder.get_object("config_cancel_button")
        self.cancel_button.connect("clicked", lambda widget: self.window.hide())
        self.accept_button = self.builder.get_object("config_accept_button")
        self.entry_jira_url = self.builder.get_object("jira_url")
        self.entry_jira_url.set_text(self.task_stack_indicator.config["jira_url"])
        self.entry_username = self.builder.get_object("username")
        self.entry_username.set_text(self.task_stack_indicator.config["username"])
        self.entry_password = self.builder.get_object("password")
        self.entry_password.set_text(self.task_stack_indicator.config["password"])
        self.spin_refresh = self.builder.get_object("refresh")
        self.spin_refresh.set_value(self.task_stack_indicator.config["refresh"])
        self.spin_window = self.builder.get_object("window")
        self.spin_window.set_value(self.task_stack_indicator.config["window"])
        self.accept_button.connect("clicked", lambda widget: self.save_config())
        
    def open(self):
        self.window.present()

    def save_config(self):
        self.window.hide()
        self.task_stack_indicator.config["jira_url"] = self.entry_jira_url.get_text()
        self.task_stack_indicator.config["username"] = self.entry_username.get_text()
        self.task_stack_indicator.config["password"] = self.entry_password.get_text()
        self.task_stack_indicator.config["refresh"] = int(self.spin_refresh.get_value())
        self.task_stack_indicator.config["window"] = int(self.spin_window.get_value())
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
        self.accept_button.connect("clicked", lambda widget: GLib.idle_add(self.task_stack_indicator.update_task, task["id"], self.summary_entry.get_text(), self.description_buffer.get_text(self.description_buffer.get_start_iter(), self.description_buffer.get_end_iter(), True)))
        self.delete_button.connect("clicked", lambda widget: GLib.idle_add(self.task_stack_indicator.delete_task, task["id"]))
        self.summary_entry.set_text(task.get("summary"))
        description = task.get("description")
        self.description_buffer.set_text(description)

if __name__ == "__main__":
    TaskStackIndicator().main()
