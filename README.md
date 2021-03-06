# About

This project aims to help linux users to (re-)use their CIT200 (Linksys (C)) VoIP phone on other platforms than Windows (e.g. LINUX!!!)

# Features  
* should have all functionalities that the Cit200.exe of Linksys had (except VoiceMail at the moment)

# Requirements

Software:  
- Python (version?,please test and give confirmation)
- Python library Skype4Py
- Python library pyusb

Hardware:  
- Linksys (C) CIT200 Phone including base connected via USB

# Installation and First Steps

* Clone this repository:  
    git clone https://github.com/philsmd/cit200xSkype.git  
* Install dependencies:  
    sudo pip install skype4py
    sudo pip install pyusb  
      
    Note: in some cases it might be better to use the package manager of  
    your system to install those libraries  
* Run it:  
    cd cit200xSkype
    sudo python cit200xSkype.py  
      
    Note: if you get a ValueError: execv() arg 2 must not be empty you  
    should indeed try the skype4py version of your distribution OR  
    if you are experienced enough and want to patch files yourself replace  
    the os.execlp('skype') with os.execlp('skype','--') calls in   
    [python folder (e.g /usr/local/lib/python2.7)]/dist-packages/Skype4Py/ 
    api/posix_x11.py and ../posix_dbus.py  
      
    Note2: if sudo python cit200xSkype.py exits very quickly after starting  
    it, you may need to apply the following patch to skype4py:  
  
    *** /usr/local/lib/python2.7/dist-packages/Skype4Py/api/posix_dbus.py.orig  
    --- /usr/local/lib/python2.7/dist-packages/Skype4Py/api/posix_dbus.py  
    *************** class SkypeAPI(SkypeAPIBase):    
    *** 87,88 ****  
    --- 87,98 ----  
          def run(self):  
    \+         # Bug fix 'segmentation fault core dumped' when using dbus.  
    \+         self.logger.info('thread started')  
    \+         if self.run_main_loop:  
    \+             context = self.mainloop.get_context()  
    \+             while True:  
    \+                 context.iteration(False)  
    \+                 time.sleep(0.2)  
    \+         self.logger.info('thread finished')  
    \+   
    \+     def runOld(self):  
              self.logger.info('thread started')  

# Hacking

* Simplify code (write function for message generation instead of using hard-coded message length,headers etc, that's easy,but needed?YES)
* VoiceMail implementation (sorry I don't use that service,please DONATE if you really want it,see pschmidt.it)
* Intensive testing
* GUI (if you really want/need it,why not?)
* and,and,and

# Credits and Contributors 
Credits go to:  
  
* Skype4Py team
* mike6d696b65 @ launchpad for his inputs w/ this project https://code.launchpad.net/~mike6d696b65/cit200/Cit200 (http://bazaar.launchpad.net/~mike6d696b65/cit200/Cit200/files)
* geoff for voip321 (see http://code.google.com/p/voip321/)

Did I miss somebody? Please help me to complete the list if you think I missed somebody here!

# License

This project is lincensed under the **GNU GENERAL PUBLIC LICENSE version 3**.  
