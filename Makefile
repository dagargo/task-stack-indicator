install:
	apt-get install python-appindicator
	cp res/dark/*  /usr/share/icons/Humanity-Dark/apps/22
	cp res/light/* /usr/share/icons/Humanity/apps/22
	cp TaskStackIndicator.py /usr/local/bin
	gtk-update-icon-cache /usr/share/icons/Humanity-Dark
	gtk-update-icon-cache /usr/share/icons/Humanity
    
deinstall:
	rm -f /usr/share/icons/Humanity/apps/22/level*.svg
	rm -f /usr/share/icons/Humanity-Dark/apps/22/level*.svg
	rm -f /usr/local/bin/TaskStackIndicator.py
	gtk-update-icon-cache /usr/share/icons/Humanity-Dark
	gtk-update-icon-cache /usr/share/icons/Humanity

clean:
	rm *~
