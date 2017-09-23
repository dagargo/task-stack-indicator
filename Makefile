NAME = task-stack-indicator
ICONS_BASEDIR = /usr/share/icons
ICONS_THEME_DIR = $(ICONS_BASEDIR)/hicolor
ICONS_DIR = $(ICONS_THEME_DIR)/scalable/apps

all: build

build:
	python3 setup.py bdist_egg

install:
	python3 setup.py install
	cp res/$(NAME) /usr/local/bin
	cp res/$(NAME).desktop /usr/share/applications
	cp res/task-stack-indicator.svg $(ICONS_DIR)
	cp res/gnome/* $(ICONS_DIR)
	gtk-update-icon-cache -f -t  $(ICONS_THEME_DIR)
	if [ -d $(ICONS_BASEDIR)/ubuntu-mono-dark ]; then \
		cp res/dark/*  $(ICONS_BASEDIR)/ubuntu-mono-dark/status/22; \
		cp res/light/* $(ICONS_BASEDIR)/ubuntu-mono-light/status/22; \
		gtk-update-icon-cache -f -t  $(ICONS_BASEDIR)/ubuntu-mono-dark; \
		gtk-update-icon-cache -f -t  $(ICONS_BASEDIR)/ubuntu-mono-light; \
	fi
	for po in locale/*.po; do \
		locale=$${po%.*}; \
		dest_dir="/usr/share/$$locale/LC_MESSAGES/"; \
		mkdir -p $$dest_dir; \
		msgfmt $$locale.po -o $$dest_dir/$(NAME).mo; \
	done

uninstall:
	rm -f /usr/local/bin/$(NAME)
	rm -f /usr/share/applications/$(NAME).desktop
	rm -f $(ICONS_DIR)/task-stack-indicator.svg
	rm -f $(ICONS_DIR)/task-stack-indicator-*.svg
	gtk-update-icon-cache -f -t  $(ICONS_THEME_DIR)
	if [ -d $(ICONS_BASEDIR)/ubuntu-mono-dark ]; then \
		rm -f $(ICONS_BASEDIR)/ubuntu-mono-dark/status/22/task-stack-indicator-*.svg; \
		rm -f $(ICONS_BASEDIR)/ubuntu-mono-light/status/22/task-stack-indicator-*.svg; \
		gtk-update-icon-cache -f -t  $(ICONS_BASEDIR)/ubuntu-mono-dark; \
		gtk-update-icon-cache -f -t  $(ICONS_BASEDIR)/ubuntu-mono-light; \
	fi
	for po in locale/*.po; do \
		locale=$${po%.*}; \
		dest_dir="/usr/share/$$locale/LC_MESSAGES/"; \
		rm -f $$dest_dir/$(NAME).mo; \
	done

clean:
	python3 setup.py clean --all
	py3clean .
	rm -rf dist $(shell python3 setup.py --name).egg-info
	rm -rf .eggs
	find . -name '*~' | xargs rm -f
	rm -f *~
	rm -f locale/*~
	rm -f \#*
	rm -rf __pycache__
