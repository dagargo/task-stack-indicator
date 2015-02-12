name = task-stack-indicator
program = $(name).py
installation_path = /usr/local/share/$(name)

install:
	apt-get install libappindicator3-1
	cp res/dark/*  /usr/share/icons/Humanity-Dark/apps/22
	cp res/light/* /usr/share/icons/Humanity/apps/22
	cp $(program) /usr/local/bin
	mkdir -p $(installation_path)/
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
	rm -f /usr/local/bin/$(program)
	rm -rf $(installation_path)
	gtk-update-icon-cache /usr/share/icons/Humanity-Dark
	gtk-update-icon-cache /usr/share/icons/Humanity
	rm -f /usr/share/applications/$(name).desktop

clean:
	rm -f *~
	rm -f locale/*~
	rm -f \#*
