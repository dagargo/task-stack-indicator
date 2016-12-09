name = task-stack-indicator
python_name = task_stack_indicator.py

install:
	python3 setup.py install
	if [ -d /usr/share/icons/Humanity ]; then \
		cp res/task-stack-indicator.svg /usr/share/icons/Humanity/apps/48/task-stack-indicator.svg; \
		cp res/dark/*  /usr/share/icons/ubuntu-mono-dark/status/22; \
		cp res/light/* /usr/share/icons/ubuntu-mono-light/status/22; \
	fi
	cp res/task-stack-indicator.svg /usr/share/icons/hicolor/48x48/apps/task-stack-indicator.svg
	cp res/color/* /usr/share/icons/hicolor/22x22/status
	cp res/dark/*  /usr/share/icons/gnome/22x22/status
	cp res/$(name) /usr/local/bin
	for po in locale/*.po; do \
	    locale=$${po%.*}; \
	    dest_dir="/usr/share/$$locale/LC_MESSAGES/"; \
	    mkdir -p $$dest_dir; \
	    msgfmt $$locale.po -o $$dest_dir/$(name).mo; \
	done
	if [ -d /usr/share/icons/Humanity ]; then \
		gtk-update-icon-cache /usr/share/icons/Humanity; \
		gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark; \
		gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light; \
	fi
	gtk-update-icon-cache /usr/share/icons/hicolor
	gtk-update-icon-cache /usr/share/icons/gnome
	cp res/$(name).desktop /usr/share/applications

uninstall:
	rm -f /usr/share/icons/Humanity/apps/48/task-stack-indicator.svg
	rm -f /usr/share/icons/hicolor/48x48/apps/task-stack-indicator.svg
	rm -f /usr/share/icons/ubuntu-mono-dark/status/22/task-stack-indicator-*.svg
	rm -f /usr/share/icons/ubuntu-mono-light/status/22/task-stack-indicator-*.svg
	rm -f /usr/share/icons/hicolor/22x22/status/task-stack-indicator-*.svg
	rm -f /usr/share/icons/gnome/22x22/status/task-stack-indicator-*.svg
	rm -f /usr/local/bin/$(name)
	if [ -d /usr/share/icons/Humanity ]; then \
		gtk-update-icon-cache /usr/share/icons/Humanity; \
		gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark; \
		gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light; \
	fi
	gtk-update-icon-cache /usr/share/icons/hicolor
	gtk-update-icon-cache /usr/share/icons/gnome
	rm -f /usr/share/applications/$(name).desktop

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
