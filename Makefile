name = task-stack-indicator
python_name = task_stack_indicator.py

install:
	python3 setup.py install
	cp res/$(name) /usr/local/bin
	cp res/$(name).desktop /usr/share/applications
	cp res/task-stack-indicator.svg /usr/share/icons/gnome/128x128/apps/task-stack-indicator.svg
	if [ -d /usr/share/icons/ubuntu-mono-dark ]; then \
		cp res/dark/*  /usr/share/icons/ubuntu-mono-dark/status/22; \
		cp res/light/* /usr/share/icons/ubuntu-mono-light/status/22; \
	fi
	cp res/dark/*  /usr/share/icons/gnome/48x48/status
	if [ -d /usr/share/icons/ubuntu-mono-dark ]; then \
		gtk-update-icon-cache -f /usr/share/icons/ubuntu-mono-dark; \
		gtk-update-icon-cache -f /usr/share/icons/ubuntu-mono-light; \
	fi
	gtk-update-icon-cache -f /usr/share/icons/gnome
	for po in locale/*.po; do \
		locale=$${po%.*}; \
		dest_dir="/usr/share/$$locale/LC_MESSAGES/"; \
		mkdir -p $$dest_dir; \
		msgfmt $$locale.po -o $$dest_dir/$(name).mo; \
	done

uninstall:
	rm -f /usr/local/bin/$(name)
	rm -f /usr/share/applications/$(name).desktop
	rm /usr/share/icons/gnome/128x128/apps/task-stack-indicator.svg
	rm -f /usr/share/icons/ubuntu-mono-dark/status/22/task-stack-indicator-*.svg
	rm -f /usr/share/icons/ubuntu-mono-light/status/22/task-stack-indicator-*.svg
	rm -f /usr/share/icons/gnome/48x48/status/task-stack-indicator-*.svg
	if [ -d /usr/share/icons/ubuntu-mono-dark ]; then \
		gtk-update-icon-cache -f /usr/share/icons/ubuntu-mono-dark; \
		gtk-update-icon-cache -f /usr/share/icons/ubuntu-mono-light; \
	fi
	gtk-update-icon-cache -f /usr/share/icons/gnome
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
