NAME = task-stack-indicator
ICONS_BASEDIR = /usr/local/share/icons
ICONS_THEME_DIR = $(ICONS_BASEDIR)/hicolor
ICONS_DIR = $(ICONS_THEME_DIR)/scalable/apps

all: build

build:
	python3 setup.py bdist_egg

install:
	python3 setup.py install
	cp res/$(NAME) /usr/local/bin
	cp res/$(NAME).desktop /usr/share/applications
	cp res/*.svg $(ICONS_DIR)
	gtk-update-icon-cache -f -t  $(ICONS_THEME_DIR)
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
	for po in locale/*.po; do \
		locale=$${po%.*}; \
		dest_dir="/usr/share/$$locale/LC_MESSAGES/"; \
		rm -f $$dest_dir/$(NAME).mo; \
	done

update_pot:
	xgettext -L Glade task_stack_indicator/resources/gui.glade -o locale/messages.pot
	xgettext -L Python task_stack_indicator/indicator.py --keyword=_ -j -o locale/messages.pot

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
