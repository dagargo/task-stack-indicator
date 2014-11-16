#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2012 David García Goñi
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the applicable version of the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public
# License version 3 and version 2.1 along with this program.  If not, see
# <http://www.gnu.org/licenses>
#

# http://developer.ubuntu.com/resources/technologies/application-indicators/
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

    def __init__(self):
        # icons taken from /usr/share/icons/ubuntu-mono-dark/*
        self.indicator = appindicator.Indicator("task-stack-indicator",
                                                "level0",
                                                appindicator.CATEGORY_OTHER,
                                                os.path.dirname(os.path.realpath(__file__)))
        self.indicator.set_status(appindicator.STATUS_ACTIVE)

        self.menu = gtk.Menu()
        self.indicator.set_menu(self.menu)
        self.load_config()
        self.load_tasks()
        self.update_menu(None)

    def load_tasks(self):
        self.in_progress = []
        self.watched = []
        if not os.path.exists(TaskStackIndicator.DIR):
            os.makedirs(TaskStackIndicator.DIR)
        
        fd = open(TaskStackIndicator.DATA_FILE, 'a+')
        try:
            self.tasks = json.loads(fd.read())
        except ValueError as e:
            self.tasks = { "nextTaskId" : 0, "tasks" : []}
        else:
            fd.close()
    
    def load_config(self):
        self.jira_icons = {}
        fd = open(TaskStackIndicator.CONFIG_FILE, 'a+')
        try:
            config = json.loads(fd.read())
            self.jira_url = config.get("jira_url")
            if not self.jira_url.endswith("/"):
                self.jira_url = self.jira_url + "/"
            self.username = config.get("username")
            self.password = config.get("password")
            self.refresh = config.get("refresh") * 60 # We use it in seconds
            self.window = config.get("window")
        except ValueError as e:
            self.jira_url = None
        else:
            fd.close()

    def load_all_issues(self):
        self.load_in_progress_issues()
        self.load_watched_issues()

    def load_in_progress_issues(self):
        self.in_progress = self.load_jira_issues("assignee = currentUser() AND status = 'In progress' ORDER BY priority DESC")

    def load_watched_issues(self):
        self.watched = self.load_jira_issues("watcher = currentUser() AND updatedDate > -%dd AND type = Task ORDER BY updatedDate DESC" % (self.window,))
        
    def load_jira_issues(self, jql):
        issues = []
        if self.jira_url:
            jql_url = self.jira_url + "/rest/api/2/search?jql=" + jql
            response = requests.get(jql_url, auth=(self.username, self.password))
            for issue in json.loads(response.text).get("issues"):
                icon_url = issue.get("fields").get("priority").get("iconUrl")
                icon_id = issue.get("fields").get("priority").get("id")
                image = self.jira_icons.get(icon_id)
                if not image:           
                    imgResponse = urllib2.urlopen(icon_url)
                    loader = gtk.gdk.PixbufLoader()
                    loader.write(imgResponse.read())
                    loader.close()
                    image = gtk.Image()
                    image.set_from_pixbuf(loader.get_pixbuf())
                    self.jira_icons[icon_id] = image
                    
                summary = issue.get("fields").get("summary")
                url = self.jira_url + "browse/" + issue.get("key")
                issues.append({"image": image, "summary" : summary, "data" : url})
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
        menuItem.connect("activate", self.reload_jira_issues_in_background)
        menuItem.show()
        self.menu.append(menuItem)

        menuItem = gtk.SeparatorMenuItem()
        menuItem.show()
        self.menu.append(menuItem)

        menuItem = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
        menuItem.connect("activate", self.exit)
        menuItem.show()
        self.menu.append(menuItem)

        total = min(len(self.in_progress) + len(self.tasks.get("tasks")), 5)
        self.indicator.set_icon("level%d" % total)

    def add_issues_list_to_menu(self, tasks, callback):
        if tasks:
            for task in tasks:
                menuItem = gtk.ImageMenuItem(task.get("summary"))
                menuItem.set_image(task.get("image"))
                menuItem.set_always_show_image(True);
                menuItem.connect("activate", callback, task.get("data"))
                menuItem.show()
                self.menu.append(menuItem)

            menuItem = gtk.SeparatorMenuItem()
            menuItem.show()
            self.menu.append(menuItem)

    def open_url(self, widget, url):
        webbrowser.open_new_tab(url)

    def delete_task(self, widget, task_id):
        for task in self.tasks.get("tasks"):
            if task.get("data") == task_id:
                self.tasks.get("tasks").remove(task)
                break
        gobject.idle_add(self.update_menu, None)

    def reload_jira_issues_in_background(self, widget):
        try:
            threading.Thread(target=self.reload_jira_issues).start()
        except ValueError as e:
           print "Error in thread"

    def reload_jira_issues(self):
        self.load_all_issues()
        gobject.idle_add(self.update_menu, None)

    def load_jira_issues_periodically(self):
        self.reload_jira_issues_in_background(None)
        self.timer = threading.Timer(300, self.load_jira_issues_periodically)
        self.timer.start()
        
    def add_task(self, widget):
        summary = self.get_task_summary("Name")
        if summary != None:
            next_task_id = self.tasks.get("nextTaskId")
            task = {"image": None, "summary" : summary, "data" : next_task_id}
            self.tasks["nextTaskId"] = next_task_id + 1
            self.tasks.get("tasks").append(task)
            gobject.idle_add(self.update_menu, None)

    def get_task_summary(self, widget):
        dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, "Tarea")
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

    def exit(self, widget):
        fd = open(TaskStackIndicator.DATA_FILE, 'w')
        fd.write(json.dumps(self.tasks))
        fd.close()
        self.timer.cancel()
        gtk.main_quit()

    def main(self):
        gobject.threads_init()
        self.load_jira_issues_periodically()
        gtk.main()

if __name__ == "__main__":
    indicator = TaskStackIndicator()
    try:
        indicator.main()
    except:
        indicator.exit(None)
