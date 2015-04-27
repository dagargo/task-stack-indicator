name = task-stack-indicator
python_name = task_stack_indicator.py
installation_path = /usr/local/share/$(name)

install:
	for r in 22 32 48; do \
	    cp res/task-stack-indicator-$$r.svg /usr/share/icons/Humanity/apps/$$r/task-stack-indicator.svg; \
	done
	cp res/dark/*  /usr/share/icons/ubuntu-mono-dark/status/22
	cp res/light/* /usr/share/icons/ubuntu-mono-light/status/22
	cp res/color/* /usr/share/icons/hicolor/22x22/status
	mkdir -p $(installation_path)
	cp -v *.py $(installation_path)
	ln -sf $(installation_path)/$(python_name) /usr/local/bin/$(name)
	for po in locale/*.po; do \
	    locale=$${po%.*}; \
	    dest_dir="$(installation_path)/$$locale/LC_MESSAGES/"; \
	    mkdir -p $$dest_dir; \
	    msgfmt $$locale.po -o $$dest_dir/$(name).mo; \
	done
	cp gui.glade /usr/local/share/task-stack-indicator
	gtk-update-icon-cache /usr/share/icons/Humanity
	gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark
	gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light
	gtk-update-icon-cache /usr/share/icons/hicolor
	cp $(name).desktop /usr/share/applications
    
uninstall:
	for r in 22 32 48; do \
	    rm -f /usr/share/icons/Humanity/apps/$$r/task-stack-indicator.svg; \
	done
	rm -f /usr/share/icons/ubuntu-mono-dark/status/22/task-stack-indicator-*.svg
	rm -f /usr/share/icons/ubuntu-mono-light/status/22/task-stack-indicator-*.svg
	rm -f /usr/share/icons/hicolor/22x22/status/task-stack-indicator-*.svg
	unlink /usr/local/bin/$(name)
	rm -rf $(installation_path)
	gtk-update-icon-cache /usr/share/icons/Humanity
	gtk-update-icon-cache /usr/share/icons/ubuntu-mono-dark
	gtk-update-icon-cache /usr/share/icons/ubuntu-mono-light
	gtk-update-icon-cache /usr/share/icons/hicolor
	rm -f /usr/share/applications/$(name).desktop

clean:
	rm -f *~
	rm -f locale/*~
	rm -f \#*
	rm -rf __pycache__
