name = task-stack-indicator
python_name = task_stack_indicator.py
installation_path = /usr/local/share/$(name)

install:
	apt-get install libappindicator3-1
	cp res/dark/*  /usr/share/icons/Humanity-Dark/apps/22
	cp res/light/* /usr/share/icons/Humanity/apps/22
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
	gtk-update-icon-cache /usr/share/icons/Humanity-Dark
	gtk-update-icon-cache /usr/share/icons/Humanity
	cp $(name).desktop /usr/share/applications
    
uninstall:
	rm -f /usr/share/icons/Humanity/apps/22/level*.svg
	rm -f /usr/share/icons/Humanity-Dark/apps/22/level*.svg
	unlink /usr/local/bin/$(name)
	rm -rf $(installation_path)
	gtk-update-icon-cache /usr/share/icons/Humanity-Dark
	gtk-update-icon-cache /usr/share/icons/Humanity
	rm -f /usr/share/applications/$(name).desktop

clean:
	rm -f *~
	rm -f locale/*~
	rm -f \#*
	rm -rf __pycache__
