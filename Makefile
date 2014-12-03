install:
	apt-get install libappindicator3-1
	cp res/dark/*  /usr/share/icons/Humanity-Dark/apps/22
	cp res/light/* /usr/share/icons/Humanity/apps/22
	cp task-stack-indicator.py /usr/local/bin
	mkdir -p /usr/local/share/task-stack-indicator
	cp gui.glade /usr/local/share/task-stack-indicator
	gtk-update-icon-cache /usr/share/icons/Humanity-Dark
	gtk-update-icon-cache /usr/share/icons/Humanity
    
uninstall:
	rm -f /usr/share/icons/Humanity/apps/22/level*.svg
	rm -f /usr/share/icons/Humanity-Dark/apps/22/level*.svg
	rm -f /usr/local/bin/task-stack-indicator.py
	rm -f /usr/local/share/task-stack-indicator
	gtk-update-icon-cache /usr/share/icons/Humanity-Dark
	gtk-update-icon-cache /usr/share/icons/Humanity

clean:
	rm -f *~
	rm -f \#*
