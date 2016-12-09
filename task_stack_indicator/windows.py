#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2016 David García Goñi
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
from gi.repository import GLib
import task_stack_indicator.common as common

class TaskStackIndicatorWindow(object):

    def __init__(self, task_stack_indicator, window_name, custom_builder=None):
        self.task_stack_indicator = task_stack_indicator
        if not custom_builder:
            custom_builder = common.builder
        self.builder = custom_builder
        self.window = self.builder.get_object(window_name)
        self.window.connect("delete-event", lambda widget, event: widget.hide() or True)
        self.window.set_position(Gtk.WindowPosition.CENTER)

class ConfigurationWindow(TaskStackIndicatorWindow):

    def __init__(self, task_stack_indicator):
        super(ConfigurationWindow, self).__init__(task_stack_indicator, "config_window")
        self.cancel_button = self.builder.get_object("config_cancel_button")
        self.cancel_button.connect('clicked',  lambda widget: self.window.hide())
        self.accept_button = self.builder.get_object("config_accept_button")
        self.spin_task_limit = self.builder.get_object(common.TASK_LIMIT)
        self.spin_refresh = self.builder.get_object(common.REFRESH_PERIOD)
        self.entry_tasks_url = self.builder.get_object(common.TASKS_URL)
        self.entry_tasks_username = self.builder.get_object(common.TASKS_USERNAME)
        self.entry_tasks_password = self.builder.get_object(common.TASKS_PASSWORD)
        self.entry_jira_url = self.builder.get_object(common.JIRA_URL)
        self.entry_jira_username = self.builder.get_object(common.JIRA_USERNAME)
        self.entry_jira_password = self.builder.get_object(common.JIRA_PASSWORD)
        self.spin_due = self.builder.get_object(common.DUE_DAYS)
        self.spin_watching = self.builder.get_object(common.WATCHING)
        self.accept_button.connect('clicked',  lambda widget: self.save_config())

    def load(self):
        self.spin_task_limit.set_value(self.task_stack_indicator.config[common.TASK_LIMIT])
        self.spin_refresh.set_value(self.task_stack_indicator.config[common.REFRESH_PERIOD])
        self.entry_tasks_url.set_text(self.task_stack_indicator.config[common.TASKS_URL])
        self.entry_tasks_username.set_text(self.task_stack_indicator.config[common.TASKS_USERNAME])
        self.entry_tasks_password.set_text(self.task_stack_indicator.config[common.TASKS_PASSWORD])
        self.entry_jira_url.set_text(self.task_stack_indicator.config[common.JIRA_URL])
        self.entry_jira_username.set_text(self.task_stack_indicator.config[common.JIRA_USERNAME])
        self.entry_jira_password.set_text(self.task_stack_indicator.config[common.JIRA_PASSWORD])
        self.spin_due.set_value(self.task_stack_indicator.config[common.DUE_DAYS])
        self.spin_watching.set_value(self.task_stack_indicator.config[common.WATCHING])

    def open(self):
        if not self.window.props.visible:
            self.load()
        self.window.present()

    def save_config(self):
        self.window.hide()
        self.task_stack_indicator.config[common.TASK_LIMIT] = int(self.spin_task_limit.get_value())
        self.task_stack_indicator.config[common.REFRESH_PERIOD] = int(self.spin_refresh.get_value())
        self.task_stack_indicator.config[common.TASKS_URL] = self.entry_tasks_url.get_text()
        self.task_stack_indicator.config[common.TASKS_USERNAME] = self.entry_tasks_username.get_text()
        self.task_stack_indicator.config[common.TASKS_PASSWORD] = self.entry_tasks_password.get_text()
        self.task_stack_indicator.config[common.JIRA_URL] = self.entry_jira_url.get_text()
        self.task_stack_indicator.config[common.JIRA_USERNAME] = self.entry_jira_username.get_text()
        self.task_stack_indicator.config[common.JIRA_PASSWORD] = self.entry_jira_password.get_text()
        self.task_stack_indicator.config[common.DUE_DAYS] = int(self.spin_due.get_value())
        self.task_stack_indicator.config[common.WATCHING] = int(self.spin_watching.get_value())
        self.task_stack_indicator.save_config()
        self.task_stack_indicator.authorized = True
        #We refresh the interface first because the queries can take a while
        self.task_stack_indicator.update_icon_and_menu()
        self.task_stack_indicator.update_interface_in_background()

class TaskWindow(TaskStackIndicatorWindow):

    def __init__(self, task_stack_indicator, custom_builder):
        super(TaskWindow, self).__init__(task_stack_indicator, 'task_window', custom_builder)
        self.cancel_button = self.builder.get_object('task_cancel_button')
        self.cancel_button.connect('clicked',  lambda widget: self.window.hide())
        self.accept_button = self.builder.get_object('task_accept_button')
        self.accept_button.set_can_default(True)
        self.accept_button.grab_default()
        self.summary_entry = self.builder.get_object('task_summary')
        self.summary_entry.connect('changed', lambda editable: self.accept_button.set_sensitive(editable.get_text()))
        self.summary_entry.set_activates_default(True)
        self.description_buffer = self.builder.get_object('description_buffer')
        self.delete_button = self.builder.get_object('task_delete_button')
        self.upload_button = self.builder.get_object('task_upload_button')


    def set_data(self, summary, description):
        self.summary_entry.set_text(summary)
        self.description_buffer.set_text(description)

class CreateTaskWindow(TaskWindow):

    def __init__(self, task_stack_indicator):
        custom_builder = common.new_gtk_builder()
        super(CreateTaskWindow, self).__init__(task_stack_indicator, custom_builder)
        self.accept_button.set_sensitive(False)
        self.delete_button.hide()
        self.upload_button.hide()
        self.accept_button.connect('clicked',  lambda widget: GLib.idle_add(self.task_stack_indicator.create_task, self.summary_entry.get_text(), self.description_buffer.get_text(self.description_buffer.get_start_iter(), self.description_buffer.get_end_iter(), True)))

class EditTaskWindow(TaskWindow):

    def __init__(self, task_stack_indicator, task):
        custom_builder = common.new_gtk_builder()
        super(EditTaskWindow, self).__init__(task_stack_indicator, custom_builder)
        self.accept_button.connect('clicked',  lambda widget: GLib.idle_add(self.task_stack_indicator.update_task, task[common.ID], self.summary_entry.get_text(), self.description_buffer.get_text(self.description_buffer.get_start_iter(), self.description_buffer.get_end_iter(), True)))
        self.delete_button.connect('clicked',  lambda widget: GLib.idle_add(self.task_stack_indicator.delete_task, task[common.ID]))
        self.upload_button.connect('clicked',  lambda widget: GLib.idle_add(self.upload_task))
        self.update_upload_button()
        self.summary_entry.set_text(task[common.SUMMARY])
        self.description_buffer.set_text(task[common.DESCRIPTION])

    def update_upload_button(self):
        sensitive = self.task_stack_indicator.is_jira_enabled() and self.task_stack_indicator.projects and self.task_stack_indicator.issue_types
        if not sensitive:
            self.upload_button.hide()

    def upload_task(self):
        issue_fields_window = IssueFieldsTaskWindow(self.task_stack_indicator, self, self.task_stack_indicator.projects, self.task_stack_indicator.issue_types)
        issue_fields_window.window.present()

class IssueFieldsTaskWindow(TaskStackIndicatorWindow):

    def __init__(self, task_stack_indicator, parent, projects, issue_types):
        super(IssueFieldsTaskWindow, self).__init__(task_stack_indicator, "issue_fields_window")
        self.parent = parent
        self.window.set_modal(True)
        self.window.set_transient_for(parent.window)
        self.accept_button = self.builder.get_object("issue_fields_accept_button")
        self.accept_button.set_can_default(True)
        self.accept_button.grab_default()
        self.cancel_button = self.builder.get_object("issue_fields_cancel_button")
        self.cancel_button.connect('clicked',  lambda widget: self.window.hide())

        self.projects_combo = self.builder.get_object("projects_combobox")
        self.projects_model = Gtk.ListStore(str, str)
        for project in projects:
            self.projects_model.append([project[common.ID], project[common.NAME]])
        self.projects_combo.set_model(self.projects_model)
        cell = Gtk.CellRendererText()
        self.projects_combo.pack_start(cell, True)
        self.projects_combo.add_attribute(cell, 'text', 1)
        self.projects_combo.set_active(0)

        self.issue_types_combo = self.builder.get_object("issue_types_combobox")
        self.issue_types_model = Gtk.ListStore(str, str)
        for issue_type in issue_types:
            self.issue_types_model.append([issue_type[common.ID], issue_type[common.NAME]])
        self.issue_types_combo.set_model(self.issue_types_model)
        cell = Gtk.CellRendererText()
        self.issue_types_combo.pack_start(cell, True)
        self.issue_types_combo.add_attribute(cell, 'text', 1)
        self.issue_types_combo.set_active(0)

        self.accept_button.connect('clicked',  lambda widget: GLib.idle_add(self.open_new_issue))

    def open_new_issue(self):
        project_id = self.projects_model[self.projects_combo.get_active()][0]
        issue_type_id = self.issue_types_model[self.issue_types_combo.get_active()][0]
        summary = urllib.parse.quote(self.parent.summary_entry.get_text())
        description = urllib.parse.quote(self.parent.description_buffer.get_text(self.parent.description_buffer.get_start_iter(), self.parent.description_buffer.get_end_iter(), True))
        jira_url = self.task_stack_indicator.config[common.JIRA_URL]
        user = self.task_stack_indicator.config[common.JIRA_USERNAME]
        url = jira_client.get_new_issue_url(jira_url, project_id, issue_type_id, summary, description, user)
        webbrowser.open_new_tab(url)
        self.window.hide()
