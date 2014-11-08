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
from os.path import expanduser


class TaskStackIndicator(threading.Thread):

    DIR = expanduser("~") + "/.TaskStackIndicator"
    CONFIG_FILE = DIR + "/config"
    DATA_FILE = DIR + "/data"

    def __init__(self):
        # icons taken from /usr/share/icons/ubuntu-mono-dark/*
        self.indicator = appindicator.Indicator("indicator-workstack",
                                                "tomboy-panel",
                                                appindicator.CATEGORY_OTHER)
        self.indicator.set_status(appindicator.STATUS_ACTIVE)

        self.menu = gtk.Menu()
        self.loadNotes()
        self.loadIssues()
        self.fillMenu(None)

        self.indicator.set_menu(self.menu)

    def loadNotes(self):
        if not os.path.exists(TaskStackIndicator.DIR):
            os.makedirs(TaskStackIndicator.DIR)
        
        fd = open(TaskStackIndicator.DATA_FILE, 'a+')
        try:
            self.notes = json.loads(fd.read())
        except ValueError as e:
            self.notes = []
        else:
            fd.close()
    
    def loadIssues(self):
        fd = open(TaskStackIndicator.CONFIG_FILE, 'a+')
        try:
            config = json.loads(fd.read())
            self.jira_url = config.get("jira_url")
            username = config.get("username")
            password = config.get("password")
            response = requests.get(self.jira_url + "/rest/api/2/search?jql=assignee=" + username + " AND status = 'In progress' ORDER BY priority DESC", auth=(username, password))
            self.issues = json.loads(response.text).get("issues")
            print response.text
        except ValueError as e:
            self.issues = []
        else:
            fd.close()

    def fillMenu(self, widget):
        for i in self.menu.get_children():
            self.menu.remove(i)

        if self.notes:
            for task in self.notes:
                menuItem = gtk.MenuItem(task.get("name"))
                menuItem.connect("activate", self.deleteTask, task)
                menuItem.show()
                self.menu.append(menuItem)

            menuItem = gtk.SeparatorMenuItem()
            menuItem.show()
            self.menu.append(menuItem)

        if self.issues:
            for issue in self.issues:
                response = urllib2.urlopen(issue.get("fields").get("priority").get("iconUrl"))
                loader = gtk.gdk.PixbufLoader()
                loader.write(response.read())
                loader.close()
                image = gtk.Image()
                image.set_from_pixbuf(loader.get_pixbuf())
                image.show()

                menuItem = gtk.ImageMenuItem(issue.get("fields").get("summary"))
                menuItem.set_image(image)
                menuItem.set_always_show_image(True);
                menuItem.connect("activate", self.openUrl, self.jira_url + "/browse/" + issue.get("key"))
                menuItem.show()
                self.menu.append(menuItem)

            menuItem = gtk.SeparatorMenuItem()
            menuItem.show()
            self.menu.append(menuItem)

        menuItem = gtk.MenuItem("Añadir tarea")
        menuItem.connect("activate", self.addTask)
        menuItem.show()
        self.menu.append(menuItem)

        menuItem = gtk.ImageMenuItem(stock_id=gtk.STOCK_REFRESH)
        menuItem.connect("activate", self.reload)
        menuItem.show()
        self.menu.append(menuItem)

        menuItem = gtk.SeparatorMenuItem()
        menuItem.show()
        self.menu.append(menuItem)

        #menuItem = gtk.MenuItem("Salir")
        menuItem = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
        menuItem.connect("activate", self.exit)
        menuItem.show()
        self.menu.append(menuItem)

    def openUrl(self, widget, url):
        webbrowser.open(url)

    def deleteTask(self, widget, task):
		self.notes.remove(task)
		self.fillMenu(None)

    def reload(self, widget):
        self.loadNotes()
        self.fillMenu(None)

    def addTask(self, widget):
        name = self.getTaskName("Name")
        if name != None:
		    task = {"name": name}
		    self.notes.append(task)
		    self.fillMenu(None)

    def getTaskName(self, widget):
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
        fd.write(json.dumps(self.notes))
        fd.close()
        gtk.main_quit()

    def main(self):
        gtk.main()

if __name__ == "__main__":
    indicator = TaskStackIndicator()
    indicator.main()
