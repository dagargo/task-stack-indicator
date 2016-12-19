name = task-stack-indicator
icons = /usr/share/icons

install:
	python3 setup.py install
	cp res/$(name) /usr/local/bin
	cp res/$(name).desktop /usr/share/applications
	cp res/task-stack-indicator.svg $(icons)/gnome/scalable/apps/task-stack-indicator.svg
	if [ ! -d $(icons)/gnome/48x48/status ]; then \
		mkdir -p $(icons)/gnome/48x48/status; \
	fi
	cp res/dark/*  $(icons)/gnome/48x48/status
	gtk-update-icon-cache -f -t  $(icons)/gnome
	if [ -d $(icons)/ubuntu-mono-dark ]; then \
		cp res/dark/*  $(icons)/ubuntu-mono-dark/status/22; \
		cp res/light/* $(icons)/ubuntu-mono-light/status/22; \
		gtk-update-icon-cache -f -t  $(icons)/ubuntu-mono-dark; \
		gtk-update-icon-cache -f -t  $(icons)/ubuntu-mono-light; \
	fi
	for po in locale/*.po; do \
		locale=$${po%.*}; \
		dest_dir="/usr/share/$$locale/LC_MESSAGES/"; \
		mkdir -p $$dest_dir; \
		msgfmt $$locale.po -o $$dest_dir/$(name).mo; \
	done

uninstall:
	rm -f /usr/local/bin/$(name)
	rm -f /usr/share/applications/$(name).desktop
	rm -f $(icons)/gnome/scalable/apps/task-stack-indicator.svg
	rm -f $(icons)/gnome/48x48/status/task-stack-indicator-*.svg
	gtk-update-icon-cache -f -t  $(icons)/gnome
	if [ -d $(icons)/ubuntu-mono-dark ]; then \
		rm -f $(icons)/ubuntu-mono-dark/status/22/task-stack-indicator-*.svg; \
		rm -f $(icons)/ubuntu-mono-light/status/22/task-stack-indicator-*.svg; \
		gtk-update-icon-cache -f -t  $(icons)/ubuntu-mono-dark; \
		gtk-update-icon-cache -f -t  $(icons)/ubuntu-mono-light; \
	fi
	for po in locale/*.po; do \
		locale=$${po%.*}; \
		dest_dir="/usr/share/$$locale/LC_MESSAGES/"; \
		rm -f $$dest_dir/$(name).mo; \
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
