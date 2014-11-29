#!/usr/bin/env python
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
import gtk
import appindicator
import threading
import json
import os
import requests
import webbrowser
import urllib2
import threading
import gobject
from os.path import expanduser

class TaskStackIndicator(threading.Thread):

    DIR = expanduser("~") + "/.TaskStackIndicator"
    CONFIG_FILE = DIR + "/config"
    DATA_FILE = DIR + "/tasks"
    IN_PROGRES_JQL = "assignee = currentUser() AND status = 'In progress' ORDER BY priority DESC"
    WATCHED_JQL = "watcher = currentUser() AND updatedDate > -%dd ORDER BY updatedDate DESC"

    def __init__(self):
        if not os.path.exists(TaskStackIndicator.DIR):
            os.makedirs(TaskStackIndicator.DIR)

        self.indicator = appindicator.Indicator("task-stack-indicator",
                                                "level0",
                                                appindicator.CATEGORY_OTHER)
        self.indicator.set_status(appindicator.STATUS_ACTIVE)

        self.menu = gtk.Menu()
        self.indicator.set_menu(self.menu)
        self.pixbuf_url_factory = PixbufUrlFactory()
        self.load_config()
        self.load_tasks()
        self.update_menu(None)
        self.indicator.connect("new-icon", self.reload_menu)

    def load_config(self):
        fd = open(TaskStackIndicator.CONFIG_FILE, 'a+')
        try:
            self.config = json.loads(fd.read())
        except ValueError as e:
            self.config = { "jira_url" : "", "username": "", "password": "", "refresh": 5, "window": 7}
            self.save_config()
        else:
            fd.close()

    def load_all(self):
        self.load_tasks()
        self.load_in_progress_issues()
        self.load_watched_issues()

    def load_tasks(self):
        self.in_progress = []
        self.watched = []
        fd = open(TaskStackIndicator.DATA_FILE, 'a+')
        try:
            self.tasks = json.loads(fd.read())
        except ValueError as e:
            self.tasks = { "nextTaskId" : 0, "tasks" : []}
        else:
            fd.close()

    def load_in_progress_issues(self):
        self.in_progress = self.load_jira_issues(TaskStackIndicator.IN_PROGRES_JQL)

    def load_watched_issues(self):
        window = self.config.get("window")
        self.watched = self.load_jira_issues(TaskStackIndicator.WATCHED_JQL % (window,))
        
    def load_jira_issues(self, jql):
        issues = []
        jira_url = self.config.get("jira_url")
        if jira_url:
            jql_url = jira_url + "/rest/api/2/search?jql=" + jql
            username = self.config.get("username")
            password = self.config.get("password")
            response = requests.get(jql_url, auth=(username, password))
            for issue in json.loads(response.text).get("issues"):
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
                url = jira_url + "browse/" + issue.get("key")
                issue = {"image_url": icon_url, "summary" : summary, "data" : url}
                issues.append(issue)
        return issues

    def update_menu(self, widget):
        for i in self.menu.get_children():
            self.menu.remove(i)

        self.add_issues_list_to_menu(self.tasks.get("tasks"), self.delete_task)
        self.add_issues_list_to_menu(self.in_progress, self.open_url)
        self.add_issues_list_to_menu(self.watched, self.open_url)

        menuItem = gtk.ImageMenuItem(stock_id=gtk.STOCK_ADD)
        menuItem.connect("activate", self.add_task)
        menuItem.show()
        self.menu.append(menuItem)

        menuItem = gtk.ImageMenuItem(stock_id=gtk.STOCK_REFRESH)
        menuItem.connect("activate", self.load_all_in_background, None)
        menuItem.show()
        self.menu.append(menuItem)

        separator = gtk.SeparatorMenuItem()
        separator.show()
        self.menu.append(separator)

        menuItem = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
        menuItem.connect("activate", self.exit)
        menuItem.show()
        self.menu.append(menuItem)

        total = min(len(self.in_progress) + len(self.tasks.get("tasks")), 5)
        self.indicator.set_icon("level%d" % total)

    def reload_menu(self, widget):
        gobject.idle_add(self.update_menu, None)

    def open_url(self, widget, url):
        webbrowser.open_new_tab(url)

    def add_issues_list_to_menu(self, tasks, callback):
        if tasks:
            for task in tasks:
                menuItem = gtk.ImageMenuItem(task.get("summary"))
                image_url = task.get("image_url")
                if image_url:
                    pixbuf = self.pixbuf_url_factory.get(image_url)
                else:
                    pixbuf = gtk.icon_theme_get_default().load_icon("tomboy-panel", 22, gtk.ICON_LOOKUP_FORCE_SVG)
                image = gtk.Image()
                image.set_from_pixbuf(pixbuf)
                menuItem.set_image(image)
                menuItem.set_always_show_image(True);
                menuItem.connect("activate", callback, task.get("data"))
                menuItem.show()
                self.menu.append(menuItem)

            menuItem = gtk.SeparatorMenuItem()
            menuItem.show()
            self.menu.append(menuItem)

    def delete_task(self, widget, task_id):
        for task in self.tasks.get("tasks"):
            if task.get("data") == task_id:
                self.tasks.get("tasks").remove(task)
                break
        gobject.idle_add(self.update_menu, None)

    def load_all_in_background(self, widget):
        threading.Thread(target=self.load_all_and_update_menu).start()

    def load_all_and_update_menu(self):
        self.load_all()
        gobject.idle_add(self.update_menu, None)

    def load_all_periodically(self):
        self.load_all_in_background(None)
        seconds = self.config.get("refresh") * 60
        self.timer = threading.Timer(seconds, self.load_all_periodically)
        self.timer.start()
        
    def add_task(self, widget):
        summary = self.get_task_summary("Name")
        if summary != None:
            task_id = self.tasks.get("nextTaskId")
            task = {"image_url": None, "summary" : summary, "data" : task_id}
            self.tasks["nextTaskId"] = task_id + 1
            self.tasks.get("tasks").append(task)
            gobject.idle_add(self.update_menu, None)
            self.save_tasks()

    def get_task_summary(self, widget):
        dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, "Task")
        entry = gtk.Entry()
        dialog.vbox.pack_end(entry)
        entry.show()
        entry.connect('activate', lambda _: dialog.response(gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        run = dialog.run()
        text = entry.get_text().decode('utf8')
        dialog.destroy()
        if run == gtk.RESPONSE_OK:
            return text
        else:
            return None

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
        gtk.main_quit()

    def main(self):
        gobject.threads_init()
        self.load_all_periodically()
        gtk.main()

class PixbufUrlFactory:

    def __init__(self):
        self.pixbufs = {}
        
    def get(self, image_url):
        pixbuf = self.pixbufs.get(image_url)
        if not pixbuf:
            imgResponse = urllib2.urlopen(image_url)
            loader = gtk.gdk.PixbufLoader()
            loader.write(imgResponse.read())
            loader.close()
            pixbuf = loader.get_pixbuf()
            self.pixbufs[image_url] = pixbuf
        return pixbuf

if __name__ == "__main__":
    indicator = TaskStackIndicator()
    try:
        indicator.main()
    except:
        indicator.exit(None)
