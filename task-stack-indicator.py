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
import threading
import json
import os
import requests
import webbrowser
import urllib3
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
        if not os.path.exists(TaskStackIndicator.DIR):
            os.makedirs(TaskStackIndicator.DIR)

        self.indicator = AppIndicator.Indicator.new("task-stack-indicator",
                                                "level0",
                                                AppIndicator.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.load_config()
        self.load_tasks()
        self.update_menu()
        file = open(TaskStackIndicator.GLADE_FILE, 'r')
        self.glade_contents = file.read()
        file.close()
        self.pool_manager = urllib3.PoolManager()
        self.pixbuf_url_factory = PixbufUrlFactory(self.pool_manager)
        self.indicator.connect("new-icon", lambda w: self.update_menu(w))

    def load_config(self):
        file = open(TaskStackIndicator.CONFIG_FILE, 'r')
        try:
            self.config = json.loads(file.read())
        except ValueError as e:
            self.config = { "jira_url" : "", "username": "", "password": "", "refresh": 5, "window": 7}
            self.save_config()
        else:
            file.close()

    def load_all(self):
        self.load_tasks()
        self.load_watched_issues()
        self.load_in_progress_issues()

    def load_tasks(self):
        self.in_progress = []
        self.watched = []
        file = open(TaskStackIndicator.DATA_FILE, 'r')
        try:
            self.tasks = json.loads(file.read())
        except ValueError as e:
            self.tasks = { "nextTaskId" : 0, "tasks" : []}
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
            jql_url = jira_url + "/rest/api/2/search?jql=" + urllib.parse.quote(jql)
            basic_auth = self.config.get("username") + ":" + self.config.get("password")
            headers = urllib3.util.make_headers(basic_auth=basic_auth)
            response = self.pool_manager.request('GET', jql_url, headers=headers)
            data = response.data.decode('utf8')
            for issue in json.loads(data).get("issues"):
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
                issue = {"image_url": icon_url, "summary" : summary, "data" : url}
                issues.append(issue)
        return issues

    def update_menu(self):
        menu = Gtk.Menu()

        self.add_issues_list_to_menu(menu, self.tasks.get("tasks"), self.edit_task)
        self.add_issues_list_to_menu(menu, self.in_progress, self.open_url)
        self.add_issues_list_to_menu(menu, self.watched, self.open_url)

        menuItem = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ADD)
        menuItem.connect("activate", self.add_task)
        menuItem.show()
        menu.append(menuItem)

        menuItem = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_REFRESH)
        menuItem.connect("activate", lambda w: self.load_all_in_background(w))
        menuItem.show()
        menu.append(menuItem)

        #menuItem = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_PREFERENCES)
        #menuItem.connect("activate", self.configure)
        #menuItem.show()
        #menu.append(menuItem)

        separator = Gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        menuItem = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT)
        menuItem.connect("activate", self.exit)
        menuItem.show()
        menu.append(menuItem)

        total = min(len(self.in_progress) + len(self.tasks.get("tasks")), 5)
        self.indicator.set_icon("level%d" % total)
        
        self.indicator.set_menu(menu)

    def open_url(self, widget, url):
        webbrowser.open_new_tab(url)

    def add_issues_list_to_menu(self, menu, tasks, callback):
        if tasks:
            for task in tasks:
                menuItem = Gtk.ImageMenuItem(task.get("summary"))
                image_url = task.get("image_url")
                if image_url:
                    pixbuf = self.pixbuf_url_factory.get(image_url)
                else:
                    pixbuf = Gtk.IconTheme.get_default().load_icon("tomboy-panel", 22, Gtk.IconLookupFlags.FORCE_SVG)
                image = Gtk.Image()
                image.set_from_pixbuf(pixbuf)
                menuItem.set_image(image)
                menuItem.set_always_show_image(True);
                menuItem.connect("activate", callback, task.get("data"))
                menuItem.show()
                menu.append(menuItem)

            menuItem = Gtk.SeparatorMenuItem()
            menuItem.show()
            menu.append(menuItem)

    def configure_task(self, widget, task_id):
        print("Configuring...")

    def load_all_in_background(self, widget):
        threading.Thread(target=self.load_all_and_update_menu).start()

    def load_all_and_update_menu(self):
        self.load_config()
        self.load_all()
        GObject.idle_add(self.update_menu)

    def load_all_periodically(self):
        self.load_all_in_background(None)
        seconds = self.config.get("refresh") * 60
        self.timer = threading.Timer(seconds, self.load_all_periodically)
        self.timer.start()
            
    def configure(self, widget):
        builder = Gtk.Builder()
        builder.add_from_string(self.glade_contents)
        config_window = builder.get_object("config_window")
        config_window.connect("delete-event", lambda w, e: w.hide() or True)
        config_window.set_icon_from_file(TaskStackIndicator.ICON_FILE)
        config_window.set_position(Gtk.WindowPosition.CENTER)
        config_cancel_button = builder.get_object("config_cancel_button")
        config_cancel_button.connect("clicked", lambda e: config_window.hide())
        config_accept_button = builder.get_object("config_accept_button")
        config_accept_button.connect("clicked", lambda e: self.save_config(builder))
        config_window.show()

    def save_config(self, builder):
        print("Saving config...")

    def create_task_window_builder(self):
        builder = Gtk.Builder()
        builder.add_from_string(self.glade_contents)
        task_window = builder.get_object("task_window")
        task_window.connect("delete-event", lambda w, e: w.hide() or True)
        task_window.set_icon_from_file(TaskStackIndicator.ICON_FILE)
        task_window.set_position(Gtk.WindowPosition.CENTER)
        task_cancel_button = builder.get_object("task_cancel_button")
        task_cancel_button.connect("clicked", lambda e: task_window.hide())
        task_accept_button = builder.get_object("task_accept_button")
        task_summary_entry = builder.get_object("task_summary")      
        return (builder, task_window, task_accept_button, task_summary_entry)

    def add_task(self, widget):
        (builder, window, accept_button, summary_entry) = self.create_task_window_builder()
        accept_button.connect("clicked", self.create_task, window, summary_entry)
        window.show()

    def edit_task(self, widget, data):
        found = False
        for task in self.tasks.get("tasks"):
            if task.get("data") == data:
                found = True
                break
        if found:
            (builder, window, accept_button, summary_entry) = self.create_task_window_builder()  
            summary_entry.set_text(task.get("summary"))
            accept_button.connect("clicked", self.update_task, window, summary_entry, task)
            window.show()
        else:
            print("Warning!")

    def create_task(self, widget, task_window, task_summary_entry):
        summary = task_summary_entry.get_text()
        if summary == "":
            print("Warning!")
        else:
            task_id = self.tasks.get("nextTaskId")
            task = {"image_url": None, "summary" : summary, "data" : task_id}
            self.tasks["nextTaskId"] = task_id + 1
            self.tasks.get("tasks").append(task)
            self.update_menu()
            self.save_tasks()
        task_window.hide()

    def update_task(self, widget, task_window, task_summary_entry, task):
        summary = task_summary_entry.get_text()
        if summary == "":
            print("Warning!")
        else:
            task["summary"] = summary
            self.update_menu()
            self.save_tasks()
        task_window.hide()

    def save_tasks(self):
        fd = open(TaskStackIndicator.DATA_FILE, 'w')
        fd.write(json.dumps(self.tasks))
        fd.close()
        
    def save_config(self):
        fd = open(TaskStackIndicator.CONFIG_FILE, 'w')
        fd.write(json.dumps(self.config))
        fd.close()

    def exit(self, widget):
        self.timer.cancel()
        Gtk.main_quit()

    def main(self):
        GObject.threads_init()
        self.load_all_periodically()
        Gtk.main()

class PixbufUrlFactory:

    def __init__(self, pool_manager):
        self.pixbufs = {}
        self.pool_manager = pool_manager
        
    def get(self, image_url):
        pixbuf = self.pixbufs.get(image_url)
        if not pixbuf:
            response = self.pool_manager.urlopen('GET', image_url)
            loader = GdkPixbuf.PixbufLoader()
            loader.write(response.data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            self.pixbufs[image_url] = pixbuf
        return pixbuf

if __name__ == "__main__":
    indicator = TaskStackIndicator()
    indicator.main()
