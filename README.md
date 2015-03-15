task-stack-indicator
====================

task-stack-indicator is an application indicator that allows you to control your task stack.

It allows to manage locally stored tasks.

Also, it offers integration with Atlassian JIRA and provides
- the issues assigned to you in progress,
- the issues assigned to you with a due date in x days,
- the issues assigned to you but not planned (either due date or fix version is empty) and
- the watched issues updated in the last y days.

It is possible to connect to JIRA from behind a proxy by setting the environment variables http_proxy and https_proxy.

Installation
------------

The package dependencies for Ubuntu are
- libappindicator3-1
- python3

To install them, simply execute `sudo apt-get install libappindicator3-1 python3`.
