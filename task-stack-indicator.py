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
from gi.repository import Gtk, GdkPixbuf
from gi.repository import GObject
from threading import Thread
import json
import os
import requests
import webbrowser
import urllib
import threading
from os.path import expanduser

class TaskStackIndicator():

    DIR = expanduser("~") + "/.task-stack-indicator"
    CONFIG_FILE = DIR + "/config"
    DATA_FILE = DIR + "/tasks"
    IN_PROGRES_JQL = "assignee = currentUser() AND status = 'In progress' ORDER BY priority DESC"
    WATCHED_JQL = "watcher = currentUser() AND updatedDate > -{:d}d ORDER BY updatedDate DESC"
    GLADE_FILE = "/usr/local/share/task-stack-indicator/gui.glade"
    ICON_FILE = "/usr/share/icons/Humanity/apps/22/level3.svg"

    def __init__(self):
        self.indicator = AppIndicator.Indicator.new("task-stack-indicator",
                                                "level0",
                                                AppIndicator.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.load_config()
        self.load_tasks()
        file = open(TaskStackIndicator.GLADE_FILE, 'r')
        self.glade_contents = file.read()
        file.close()
        self.edit_task_windows = {}
        self.create_task_windows = []
        self.configuration_window = ConfigurationWindow(self)
        self.indicator.connect("new-icon", lambda indicator: self.update_menu())
        self.update_icon_and_menu(False)
        self.pixbuf_url_factory = PixbufUrlFactory()

    def load_config(self):
        if not os.path.exists(TaskStackIndicator.DIR):
            os.makedirs(TaskStackIndicator.DIR)
        try:
            file = open(TaskStackIndicator.CONFIG_FILE, 'r')
            self.config = json.loads(file.read())
        except IOError as e:
            self.config = { "jira_url" : "", "username": "", "password": "", "refresh": 5, "window": 7}
            self.save_config()
        else:
            file.close()

    def load_tasks(self):
        self.in_progress = []
        self.watched = []
        try:
            file = open(TaskStackIndicator.DATA_FILE, 'r')
            self.tasks = json.loads(file.read())
        except IOError as e:
            self.tasks = { "nextTaskId" : 0, "tasks" : []}
            self.save_tasks()
        else:
            file.close()

    def load_in_progress_issues(self):
        self.in_progress = self.load_jira_issues(TaskStackIndicator.IN_PROGRES_JQL)

    def load_watched_issues(self):
        jql = TaskStackIndicator.WATCHED_JQL.format(self.config.get("window"))
        self.watched = self.load_jira_issues(jql)
        
    def load_jira_issues(self, jql):
        issues = []
        jira_url = self.config.get("jira_url")
        if jira_url:
            jql_url = jira_url + "/rest/api/2/search?jql=" + jql
            auth = (self.config.get("username"), self.config.get("password"))
            response = requests.get(jql_url, auth=auth)
            for issue in response.json().get("issues"):
                fields = issue.get("fields")
                priority = fields.get("priority")
                if priority:
                    icon_url = priority.get("iconUrl")
                else:
                    issue_type = fields.get("issuetype")
                    if issue_type:
                        icon_url = issue_type.get("iconUrl")
                    else:
                        icon_url = None
                summary = fields.get("summary")
                url = jira_url + "/browse/" + issue.get("key")
                issue = {"image_url": icon_url, "summary" : summary, "id" : url}
                issues.append(issue)
        return issues

    def update_icon_and_menu(self, background=True):
        total = min(len(self.in_progress) + len(self.tasks.get("tasks")), 5)
        icon = "level%d" % total
        if icon != self.indicator.get_icon():
            #This will trigger a call to update_menu
            self.indicator.set_icon(icon)
        else:
            self.update_menu(background)
            
    def update_menu(self, background=True):
        menu = Gtk.Menu()

        self.add_tasks_to_menu(menu, self.tasks.get("tasks"), self.edit_task)
        self.add_tasks_to_menu(menu, self.in_progress, self.open_url)
        self.add_tasks_to_menu(menu, self.watched, self.open_url)

        item = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ADD)
        item.connect("activate", lambda widget: self.create_task())
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

        if background:
            GObject.idle_add(self.indicator.set_menu, menu)
        else:
            self.indicator.set_menu(menu)

    def create_task(self):
         create_task_window = CreateTaskWindow(self)
         create_task_window.open()
         self.create_task_windows.append(create_task_window)

    def edit_task(self, widget, key):
        for task in self.tasks["tasks"]:
            if task["id"] == key:
                break
        edit_task_window = self.edit_task_windows.get(key)
        if not edit_task_window:
            edit_task_window = EditTaskWindow(self, task)
            self.edit_task_windows[key] = edit_task_window
        edit_task_window.open()

    def open_url(self, widget, url):
        webbrowser.open_new_tab(url)

    def add_tasks_to_menu(self, menu, tasks, callback):
        if tasks:
            for task in tasks:
                item = Gtk.ImageMenuItem(task.get("summary"))
                image_url = task.get("image_url")
                if image_url:
                    pixbuf = self.pixbuf_url_factory.get(image_url)
                else:
                    pixbuf = Gtk.IconTheme.get_default().load_icon("tomboy-panel", 22, Gtk.IconLookupFlags.FORCE_SVG)
                image = Gtk.Image()
                image.set_from_pixbuf(pixbuf)
                item.set_image(image)
                item.set_always_show_image(True);
                item.connect("activate", callback, task.get("id"))
                item.show()
                menu.append(item)

            item = Gtk.SeparatorMenuItem()
            item.show()
            menu.append(item)

    def update_interface_in_background(self):
        Thread(target = self.update_interface).start()

    def update_interface(self):
        self.load_tasks()
        self.load_watched_issues()
        self.load_in_progress_issues()
        self.update_icon_and_menu()

    def update_periodically(self):
        self.update_interface_in_background()
        ms = self.config.get("refresh") * 60000
        GObject.timeout_add(ms, self.update_periodically)

    def save_tasks(self):
        fd = open(TaskStackIndicator.DATA_FILE, 'w')
        fd.write(json.dumps(self.tasks))
        fd.close()
        
    def save_config(self):
        fd = open(TaskStackIndicator.CONFIG_FILE, 'w')
        fd.write(json.dumps(self.config))
        fd.close()

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
        self.delete_button = self.builder.get_object("task_delete_button")

class CreateTaskWindow(TaskWindow):

    def __init__(self, task_stack_indicator):
        super(CreateTaskWindow, self).__init__(task_stack_indicator)
        self.accept_button.set_sensitive(False)
        self.delete_button.hide()
        self.accept_button.connect("clicked", lambda widget: self.create_task())

    def open(self):
        self.window.present()

    def create_task(self):
        self.window.hide()
        summary = self.summary_entry.get_text()
        task_id = self.task_stack_indicator.tasks["nextTaskId"]
        task = {"image_url": None, "summary" : summary, "id" : task_id}
        self.task_stack_indicator.tasks["nextTaskId"] = task_id + 1
        self.task_stack_indicator.tasks["tasks"].append(task)
        self.task_stack_indicator.save_tasks()
        self.task_stack_indicator.update_icon_and_menu()
        self.task_stack_indicator.create_task_windows.remove(self)

class EditTaskWindow(TaskWindow):

    def __init__(self, task_stack_indicator, task):
        super(EditTaskWindow, self).__init__(task_stack_indicator)
        self.task = task
        self.summary_entry.set_text(task.get("summary"))
        self.accept_button.connect("clicked", lambda widget: self.update_task())
        self.delete_button.connect("clicked", lambda widget: self.delete_task())

    def open(self):
        self.window.present()

    def update_task(self):
        self.window.hide()
        self.task["summary"] = self.summary_entry.get_text()
        self.task_stack_indicator.save_tasks()
        self.task_stack_indicator.update_icon_and_menu()
        self.task_stack_indicator.edit_task_windows.pop(self.task["id"])

    def delete_task(self):
        self.window.hide()
        self.task_stack_indicator.tasks["tasks"].remove(self.task)
        self.task_stack_indicator.save_tasks()
        self.task_stack_indicator.update_icon_and_menu()
        self.task_stack_indicator.edit_task_windows.pop(self.task["id"])

class PixbufUrlFactory(object):

    def __init__(self):
        self.pixbufs = {}
        
    def get(self, image_url):
        pixbuf = self.pixbufs.get(image_url)
        if not pixbuf:
            response = requests.get(image_url)
            loader = GdkPixbuf.PixbufLoader()
            loader.write(response.content)
            loader.close()
            pixbuf = loader.get_pixbuf()
            self.pixbufs[image_url] = pixbuf
        return pixbuf

if __name__ == "__main__":
    TaskStackIndicator().main()
