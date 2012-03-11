#!/usr/bin/python
# cit200xSkype
# Copyright (C) by pschmidt (philsmd) 2012
# (see pschmidt.it)
#
# This Python Script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cit200xSkype is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this source files. If not, see
# <http://www.gnu.org/licenses/>.

# 2012-03-07: initial release (GitHub)
# Credits: to 


# HACKING,HACKING,TODO
# Create a function that generates the set of messages for us (w/o using predefined length and other headers)
# this makes it more flexible, reduce/refactor code and the communication could be faster (e.g for small skype-names we
# do not need 5 messages, instead for longer names we could need that)
# What I found out as of now:
# c5 .. .. ..  means that there are 5 messages following this message
# c3 .. .. ..  (only 3)
# The third last byte of the first messages 7-byte block is the total length (of bytes) following this message
# ... please help to understand the full meaning of all headers etc. to create a helper function that does the message
# generation for us (w/o hard-coding it)

import usb.core
import time
import Skype4Py
import sys
from os import environ

PHONE_NAME="Cit200"
ID_VENDOR=0x13b1  #ID_VENDOR=0xb113
ID_PRODUCT=0x001d #ID_PRODUCT=0x1d00
USB_IF=3 # interface
USB_EP=0x83 # endpoint
qwerty=1
contact=[] # stores some information about a contact that we queried before, send information to handset
callee=""  # last called person
incomingCall=[None,""]  # information about the last incoming call
DEBUG=False

try:
    if os.environ.get('DISPLAY'):
        skype=Skype4Py.Skype(Transport='x11')
    else:
        skype=Skype4Py.Skype()
except:
    skype=Skype4Py.Skype()  # could use dbus OR another default transport
skypeStates=['ONLINE','OFFLINE','NA','AWAY','INVISIBLE','DND','SKYPEME'] # check reihenfolge

def main():
    global skype
    if not skype.Client.IsRunning:
        skype.Client.Start()
    skype.OnAttachmentStatus=OnAttach
    skype.OnUserStatus=OnUserStatus
    skype.OnCallStatus=OnCallStatus
    print '[i] Connecting to Skype..'
    k=0
    attachTrials=6
    attached=False
    while k<attachTrials and attached is False:
        try:
            skype.Attach()
            attached=True
        except Skype4Py.errors.SkypeAPIError:
            if k<attachTrials:
                k+=1
                time.sleep(2)
            else:
                sys.exit("[-] Attaching to Skype process failed. Are you currently logged in?")
        except:
            sys.exit("[-] Attaching to Skype process failed")

    dev=usb.core.find(idVendor=ID_VENDOR,idProduct=ID_PRODUCT)
    if dev is None:
        sys.exit('[-] %s Voip Phone was NOT found'%PHONE_NAME)
    if dev.is_kernel_driver_active(USB_IF) is True:
        try:
            dev.detach_kernel_driver(USB_IF)
        except:
            sys.exit('[-] Could NOT detatch kernel driver: %s'%str(e))
    usb.util.claim_interface(dev,USB_IF)
    try:
        i=1
        c=1
        global qwerty
        while skype.Client.IsRunning:
            stat=get_status()
            if stat is not None and stat>=0 and stat<len(skypeStates):
                dev_read(dev);
                if c==1:
                    localtime=time.localtime(time.time())
                    dev_write(dev,[0xc1,0x33,0x00,0x43,0x07,0x9a,0x4f])
                    dev_write(dev,[0x05,localtime[3],localtime[4],0x06,stat,0x02,0x00]) # what about 0x06 and 0x02?
                i=1
                while i<5:
                    i+=1
                    # START OF SWITCH
                    if qwerty==1:
                        # init (first time in loop)
                        qwerty=0 
                    elif qwerty==2:
                        if DEBUG:
                            print "[i] Answer contact request"
                        # numTotalContacts,  index,chandle,cname,cstat,language,birthday,gender,home,cell,office,address,timezone, indexb,chandleb,cnameb,statb,...
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00])
                        ptr=1
                        contactItems=12
                        totalLength=len(contact)
                        if totalLength>ptr:
                            cnum=contact[0]
                            while totalLength>ptr:
                                if len(contact[ptr+2])>0:
                                    cname=format_phone_output(contact[ptr+2],13)
                                    chandle=format_phone_output(contact[ptr+1],16)  # skype name
                                else:
                                    chandle=cname=format_phone_output(contact[ptr+1],13)
                                currIndex=contact[ptr]
                                try:
                                    cstat=skypeStates.index(contact[ptr+3])
                                except:
                                    cstat=0x00
                                dev_write(dev,[0xc6,0x33,0x01,0x43,0x23,0x9a,0x4c])  # c6 means that 6 other messages/7bytes-tuples will follow!
                                dev_write(dev,[0x45,0x00,currIndex,0x00,cnum,ord(cname[0]),ord(cname[1])])
                                dev_write(dev,[0x44,ord(cname[2]),ord(cname[3]),ord(cname[4]),ord(cname[5]),ord(cname[6]),ord(cname[7])])
                                dev_write(dev,[0x43,ord(cname[8]),ord(cname[9]),ord(cname[10]),ord(cname[11]),ord(cname[12]),ord(cname[13])])
                                dev_write(dev,[0x42,ord(chandle[0]),ord(chandle[1]),ord(chandle[2]),ord(chandle[3]),ord(chandle[4]),ord(chandle[5])])
                                dev_write(dev,[0x41,ord(chandle[6]),ord(chandle[7]),ord(chandle[8]),ord(chandle[9]),ord(chandle[10]),ord(chandle[11])])
                                dev_write(dev,[0x03,ord(chandle[12]),ord(chandle[13]),cstat,0x00,0x00,0x00])
                                ptr+=contactItems
                        else:
                            dev_write(dev,[0xc1,0x33,0x01,0x43,0x06,0x9a,0x4c])
                            dev_write(dev,[0x04,0x00,0x00,0x00,0x00,0x00,0x00])
                        qwerty=0
                    elif qwerty==3:
                        if DEBUG:
                            print "[i] Echoing current state for state list"
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00]) # OR dev_write(dev,[0x83,0x32,0x01,0x43,0x02,0x9a,0x42])
                        dev_write(dev,[0xc1,0x33,0x01,0x43,0x03,0x9a,0x42])
                        dev_write(dev,[0x01,get_status(),0x00,0x00,0x00,0x00,0x00])
                        qwerty=0;
                    elif qwerty==9:
                        # if DEBUG:
                        #   print "[i] Answer calling part 1 - Call from phone"
                        # This is a constant set of bytes sent to initiate a call !?
                        dev_write(dev,[0x82,0x22,0x11,0x00,0x00,0x00,0x00])
                        dev_write(dev,[0x85,0x33,0x11,0x68,0x01,0x01,0x00])
                        dev_write(dev,[0x83,0x33,0x11,0x67,0x00,0x00,0x00])
                        dev_write(dev,[0x82,0x43,0x11,0x00,0x00,0x00,0x00])
                        qwerty=10
                    elif qwerty==10:
                        if DEBUG:
                            print "[i] Call initiated from handset";
                        dev_write(dev,[0xc1,0x33,0xff,0x43,0x04,0x9a,0x51])
                        dev_write(dev,[0x02,0x01,0x00,0x00,0x00,0x00,0x00])
                        qwerty=0;
                    elif qwerty==12:
                        # if DEBUG:
                        #     print "[i] Confirm status change";
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00])
                        dev_write(dev,[0xc1,0x33,0x01,0x43,get_status(),0x9a,0x43])
                        dev_write(dev,[0x01,0x03,0x00,0x00,0x00,0x00,0x00])
                        qwerty=0;
                    elif qwerty==4:
                        if DEBUG:
                            print "[i] Answer contact details"
                        # numTotalContacts,  index,chandle,cname,cstat,language,birthday,gender,home,cell,office,address,timezone, indexb,chandleb,cnameb,statb,...
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00])
                        dev_write(dev,[0xc9,0x33,0x01,0x43,0x34,0x9a,0x4d])
                        chandle=format_phone_output(contact[2],26)
                        # chandle=format_phone_output(contact[2]+" "+contact[3],26)      # would be nicer but NOT good/possible for initiating CALL
                        # (Skype-handle extraction in this python script==good work around?)
                        dev_write(dev,[0x48,0x00,0x00,0x00,ord(chandle[0]),ord(chandle[1]),ord(chandle[2])])
                        dev_write(dev,[0x47,ord(chandle[3]),ord(chandle[4]),ord(chandle[5]),ord(chandle[6]),ord(chandle[7]),ord(chandle[8])])
                        dev_write(dev,[0x46,ord(chandle[9]),ord(chandle[10]),ord(chandle[11]),ord(chandle[12]),ord(chandle[13]),ord(chandle[14])])
                        dev_write(dev,[0x45,ord(chandle[15]),ord(chandle[16]),ord(chandle[17]),ord(chandle[18]),ord(chandle[19]),ord(chandle[20])])
                        dev_write(dev,[0x44,ord(chandle[21]),ord(chandle[22]),ord(chandle[23]),ord(chandle[24]),ord(chandle[25]),ord(chandle[26])])
                        clang=format_phone_output(contact[5],9)
                        dev_write(dev,[0x43,0x00,0x00,0x00,0x00,0x00,ord(clang[0])])
                        dev_write(dev,[0x42,ord(clang[1]),ord(clang[2]),ord(clang[3]),ord(clang[4]),ord(clang[5]),ord(clang[6])])
                        birthday=[0xff,0x00,0x00,0x00]
                        birthdayField=contact[6]
                        if birthdayField is not None:
                            birthdayStr=str(birthdayField)
                            try:
                                birthday=[int(birthdayStr[0:2],16),int(birthdayStr[2:4],16),int(birthdayStr[5:7],16),int(birthdayStr[8:10],16)]
                            except:
                                print "[!] Failed to get the birthday. SKIP"
                        dev_write(dev,[0x41,ord(clang[7]),ord(clang[8]),ord(clang[9]),birthday[0],birthday[1],birthday[2]])
                        dev_write(dev,[0x03,birthday[3],get_gender(contact[7]),0x05,0x00,0x00,0x00])
                        qwerty=0;
                    elif qwerty==7:
                        if DEBUG:
                            print "[i] Answer contact detail home phone"
                        # numTotalContacts,  index,chandle,cname,cstat,language,birthday,gender,home,cell,office,address,timezone, indexb,chandleb,cnameb,statb,...
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00])
                        if len(contact)>1:
                            dev_write(dev,[0xc6,0x33,0x01,0x43,0x25,0x9a,0x4c])
                            cname=format_phone_output(contact[3],13)
                            dev_write(dev,[0x45,0x00,0x02,0x00,0x21,ord(cname[0]),ord(cname[1])]) # 0x21 AMOUNT of contacts? =>AA nothing (in else)?
                            dev_write(dev,[0x44,ord(cname[2]),ord(cname[3]),ord(cname[4]),ord(cname[5]),ord(cname[6]),ord(cname[7])])
                            dev_write(dev,[0x43,ord(cname[8]),ord(cname[9]),ord(cname[10]),ord(cname[11]),ord(cname[12]),ord(cname[13])])
                            chandle=format_phone_output(contact[2],16)
                            dev_write(dev,[0x42,ord(chandle[0]),ord(chandle[1]),ord(chandle[2]),ord(chandle[3]),ord(chandle[4]),ord(chandle[5])])
                            dev_write(dev,[0x41,ord(chandle[6]),ord(chandle[7]),ord(chandle[8]),ord(chandle[9]),ord(chandle[10]),ord(chandle[11])])
                            dev_write(dev,[0x05,ord(chandle[12]),ord(chandle[13]),ord(chandle[14]),ord(chandle[15]),ord(chandle[16]),0x00])
                        else:
                            dev_write(dev,[0xc1,0x33,0x01,0x43,0x06,0x9a,0x4c])
                            dev_write(dev,[0x04,0x00,0x00,0x00,0x00,0x00,0x00])
                        qwerty=0
                    elif qwerty==13:
                        # numTotalContacts,  index,chandle,cname,cstat,language,birthday,gender,home,cell,office,address,timezone, indexb,chandleb,cnameb,statb,...
                        if DEBUG:
                            print "[i] Answer contact detail office, home, cell phone"
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00])
                        if len(contact)>1:
                            dev_write(dev,[0xc6,0x33,0x01,0x43,0x23,0x9a,0x4d])
                            tel_office=format_phone_tel(contact[10],9)
                            dev_write(dev,[0x45,0x00,0x01,0x01,tel_office[0],tel_office[1],tel_office[2]])
                            dev_write(dev,[0x44,tel_office[3],tel_office[4],tel_office[5],tel_office[6],tel_office[7],tel_office[8]])
                            tel_home=format_phone_tel(contact[8],9)
                            dev_write(dev,[0x43,tel_office[9],tel_office[0],tel_home[1],tel_home[2],tel_home[3],tel_home[4]])
                            tel_mobile=format_phone_tel(contact[9],9)
                            dev_write(dev,[0x42,tel_home[5],tel_home[6],tel_home[7],tel_home[8],tel_home[9],tel_mobile[0]])
                            dev_write(dev,[0x41,tel_mobile[1],tel_mobile[2],tel_mobile[3],tel_mobile[4],tel_mobile[5],tel_mobile[6]])
                            dev_write(dev,[0x03,tel_mobile[7],tel_mobile[8],tel_mobile[9],0x00,0x00,0x00])
                        else:
                            dev_write(dev,[0xc6,0x33,0x01,0x43,0x05,0x9a,0x4d])
                            dev_write(dev,[0x03,0x00,0x00,0x00,0x00,0x00,0x00])
                        qwerty=0
                    elif qwerty==14:
                        if DEBUG:
                            print "[i] Answer contact detail address, local time"
                        # numTotalContacts,  index,chandle,cname,cstat,language,birthday,gender,home,cell,office,address,timezone, indexb,chandleb,cnameb,statb,...
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00])
                        if len(contact)>11:
                            dev_write(dev,[0xc8,0x33,0x01,0x43,0x2f,0x9a,0x4d]) 
                            address=format_phone_output(contact[11],38,'\x00')
                            dev_write(dev,[0x47,0x00,0x01,0x02,ord(address[0]),ord(address[1]),ord(address[2])])
                            dev_write(dev,[0x46,ord(address[3]),ord(address[4]),ord(address[5]),ord(address[6]),ord(address[7]),ord(address[8])])
                            dev_write(dev,[0x45,ord(address[9]),ord(address[10]),ord(address[11]),ord(address[12]),ord(address[13]),ord(address[14])])
                            dev_write(dev,[0x44,ord(address[15]),ord(address[16]),ord(address[17]),ord(address[18]),ord(address[19]),ord(address[20])])
                            dev_write(dev,[0x43,ord(address[21]),ord(address[22]),ord(address[23]),ord(address[24]),ord(address[25]),ord(address[26])])
                            dev_write(dev,[0x42,ord(address[27]),ord(address[28]),ord(address[29]),ord(address[30]),ord(address[31]),ord(address[32])])
                            dev_write(dev,[0x41,ord(address[33]),ord(address[34]),ord(address[35]),ord(address[36]),ord(address[37]),ord(address[38])])
                            users_time=get_users_localtime(contact[12])
                            dev_write(dev,[0x03,0x00,users_time[0],users_time[1],0x00,0x00,0x00])
                        else:
                            dev_write(dev,[0xc1,0x33,0x01,0x43,0x05,0x9a,0x4d]) 
                            dev_write(dev,[0x03,0x00,0x00,0x00,0x00,0x00,0x00]) 
                        qwerty=0
                    elif qwerty==15:
                        #print "[i] View Voicemail"
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00])
                        dev_write(dev,[0xc1,0x33,0x01,0x43,0x06,0x9a,0x48])
                        dev_write(dev,[0x04,0x00,0x00,0x00,len(skype.Voicemails),0x00,0x00]) # TODO
                        qwerty=0
                    elif qwerty==16:
                        #print "[i] Delete Voicemail"
                        dev_write(dev,[0x83,0x32,0x01,0x43,0x00,0x00,0x00])
                        dev_write(dev,[0xc2,0x33,0x01,0x43,0x0a,0x9a,0x49]) # confirm deletion
                        dev_write(dev,[0x41,0x00,0x00,0x00,0x00,0x00,0x00])
                        dev_write(dev,[0x02,0x08,0x00,0x00,0x00,0x00,0x00])
                        qwerty=0
                    elif qwerty==17:
                        #print "[i] Outgoing call accepted"
                        dev_write(dev,[0x83,0x32,0xff,0x43,0x00,0x00,0x00])
                        qwerty=0
                    elif qwerty==19:
                        #print "[i] Initiate Call with %s"%callee
                        dev_write(dev,[0x83,0x32,0x11,0x35,0x00,0x00,0x00])
                        placecall(callee)
                        qwerty=0
                    elif qwerty==20:
                        # if DEBUG:
                        #     print "[i] Ending call from handset"
                        dev_write(dev,[0x82,0x52,0x11,0x00,0x00,0x00,0x00])
                        endcall()
                        qwerty=0
                    elif qwerty==24:
                        # if DEBUG:
                        #     print "[i] Ending call from PC"
                        # we get a busy sound output! (s.t. we know that the PC or the other side (could be caller or callee) has stopped this call
                        dev_write(dev,[0x84,0x53,0x11,0x01,0x00,0x00,0x00]) 
                        qwerty=0
                    elif qwerty==21:
                        # if DEBUG:
                        #     print "[i] Incoming call, notify handset"
                        dev_write(dev,[0x84,0x23,0x00,0x01,0x80,0x00,0x00])
                        qwerty=0
                    elif qwerty==22:
                        if incomingCall is not None and len(incomingCall)>1 and incomingCall[1]is not None and len(incomingCall[1])>0:
                            callerDisplay=format_phone_output(incomingCall[1],21,'\x00')
                            print "[i] Incoming call from %s"%callerDisplay # maybe its better to hide this in output?
                            dev_write(dev,[0x82,0x12,0x00,0x00,0x00,0x00,0x00])
                            dev_write(dev,[0xc5,0x33,0xff,0x43,0x1f,0x9a,0x00])
                            localtime=time.localtime(time.time())
                            dev_write(dev,[0x44,0x03,0x04,localtime[1],localtime[2],localtime[3],localtime[4]]) # maybe here the info is month dayOfMonth hour seconds
                            dev_write(dev,[0x43,0x0b,ord(callerDisplay[0]),ord(callerDisplay[1]),ord(callerDisplay[2]),ord(callerDisplay[3]),ord(callerDisplay[4])])
                            dev_write(dev,[0x42,ord(callerDisplay[5]),ord(callerDisplay[6]),ord(callerDisplay[7]),ord(callerDisplay[8]),ord(callerDisplay[9]),ord(callerDisplay[10])])
                            dev_write(dev,[0x41,ord(callerDisplay[11]),ord(callerDisplay[12]),ord(callerDisplay[13]),ord(callerDisplay[14]),ord(callerDisplay[15]),ord(callerDisplay[16])])
                            dev_write(dev,[0x05,ord(callerDisplay[17]),ord(callerDisplay[18]),ord(callerDisplay[19]),ord(callerDisplay[20]),ord(callerDisplay[21]),0x00])
                        qwerty=0
                    elif qwerty==23:
                        if DEBUG:
                            print "[i] Incoming call was answered"
                        dev_write(dev,[0x85,0x33,0x11,0x68,0x01,0x01,0x00])
                        dev_write(dev,[0x82,0x43,0x11,0x00,0x00,0x00,0x00])
                        if incomingCall is not None and len(incomingCall)>0 and incomingCall[0] is not None:
                            incomingCall[0].Answer()
                        qwerty=0
                    elif qwerty==25:
                        # print "[i] Holding/Resuming call"
                        dev_write(dev,[0x83,0x32,0x11,0x35,0x00,0x00,0x00])
                        holdcall()
                        qwerty=0
                    elif qwerty==26:
                        print "[i] Handset has rejected this call"
                        dev_write(dev,[0x83,0x32,0x11,0x43,0x00,0x00,0x00]) # reject it!
                        dev_write(dev,[0x84,0x53,0x00,0x01,0x00,0x00,0x00])
                        if incomingCall is not None and len(incomingCall)>0 and incomingCall[0] is not None:
                            incomingCall[0].Finish()
                        qwerty=0

            else: # wait a little bit longer s.t. the user can e.g. login to skype
                time.sleep(1.5)
            if c<8 or qwerty!=0: # here we need if NOT 0: we could get a mess w/ pending messages (in between we could have a ping,dangerous!)
                c+=1;
            else:
                c=1;
            time.sleep(0.2)
    except KeyboardInterrupt:
        # tell the phone that we are going to stop the communication (and this application)
        dev_write(dev,[0xc1,0x33,0x00,0x43,0x07,0x9a,0x4f]) # DISCONNECT?
        dev_write(dev,[0x05,0x0a,0x01,0x00,0x00,0x00,0x00])
        time.sleep(1)
        usb.util.release_interface(dev,USB_IF)
        dev.attach_kernel_driver(USB_IF)

def holdcall():
    global skype
    for c in skype.ActiveCalls:   # do we really want to receive all of them?
        if c.Status==Skype4Py.clsInProgress:
            try:
                print "[i] Call was put on hold"
                c.Hold()
            except:
                print "[!] Failed to put call on hold"
            break
        else:
          if c.Status==Skype4Py.clsLocalHold or c.Status=="LOCALHOLD":
            try:
                print "[i] Call was resumed"
                c.Resume()
            except:
                print "[!] Failed to resume call"
            break

def placecall(callee):
    if callee is not None:
        skypeCallee=""
        for i in callee:
            skypeCallee+=chr(i)
        print "[i] Calling %s"%skypeCallee # we may need/want to hide that in the output (security reasons?)
        try:
            skype.PlaceCall(skypeCallee)
        except:
            print "[i] Error while placing the call %s"

def endcall():
    # we here end ALL active calls (be aware)
    for call in skype.ActiveCalls:
        skype.Call(call.Id).Finish()

def get_users_localtime(offset):
    # return list with [hours] and [minutes]
    # of course we could do some calculation w/ datetime, but do we need that,
    # it's funnier to do it without
    ret=[0xaa,0xaa]
    if offset is not None:
        localtime=time.localtime(time.time())
        hours=localtime[3]
        minute=localtime[4]
        diffHours=int(offset/3600)
        diffMinute=int((offset-diffHours*3600)/60)
        minute+=diffMinute
        minuteOverflow=int(minute/60)
        minute-=minuteOverflow*60
        if minute<0:
            minute=60-minute
            hours-=1
        hours+=minuteOverflow
        hours+=diffHours
        hourOverflow=int(hours/24)
        hours-=hourOverflow*24
        if hours<0:
            hours=24-hours
        ret=[int(str(hours)),int(str(minute))]
    return ret

def format_phone_address(city,province,country):
    ret=""
    ret+=city
    if len(ret):
        ret+=","
    ret+=province
    if len(ret):
        ret+=" ("+country+")"
    else:
        ret+=country
    return ret 

def format_phone_output(target,length,suffix='\x20'):
    if target is None:
        target=""
    if len(target)>length:
        tmp=list(target)
        tmp[len(target)-1]=suffix
        target="".join(tmp)
    while (len(target)<=length):
        target+=suffix
    return target

def format_phone_tel(target,length):
    # what we need to do here: just get the numbers,fill it to length,check the number string, 2 by 2
    # e.g. string "1456" will result in the 0x14 0x56, fill and skip non-numeric characters
    # AA means finished (or A skip?)
    converted=format_phone_output(target,length*2).replace(" ","").replace("+","")
    ret=[]
    i=0
    totalLength=len(converted)
    while i<totalLength:
        if converted[i].isnumeric() and i+1<totalLength and converted[i+1].isnumeric():
            ret.append(int(converted[i:i+2],16))
            i+=2
        elif converted[i].isnumeric() and i+1>=totalLength:
            ret.append(int(converted[i:i+1],16)*16+0x0a)   #  take only first one,shift it to 16^1 and add an A afterwards  => xA
            i+=2
        elif converted[i].isnumeric() and i+1<totalLength:
            j=2
            found=False
            while i+j<totalLength:
                if converted[i+j].isnumeric():
                    ret.append(int(converted[i]+converted[i+j],16)) 
                    i=i+j
                    break
                j+=1
            if found is False:
                ret.append(0xaa)
                i+=2
        elif not converted[i].isnumeric() and converted[i]!='A' and converted[i]!='a':
            # skip one position (and continue)
            i+=1
        else:
            ret.append(0xaa)
            i+=2
    while len(ret)<=length:
        ret.append(0xaa)
    return ret 

def get_gender(genderStr):
    ret=0
    if genderStr is not None:
        try:
            if genderStr=="MALE":
                ret=1
            elif genderStr=="FEMALE":
                ret=2   # whis order was NOT imposed by me (but Linksys),I instead of course would but YOU,
                # lady, on the first position (=> ret==1)
        except:
            ret=0
    return ret

def get_status():
    try:
        return skypeStates.index(skype.CurrentUser.OnlineStatus)
    except:
        print "[-] Getting the user status failed. Maybe you need to login?"
        return None

def dev_write(dev,buf):
    i=0
    shiftSize=7
    length=len(buf)
    while i<length:
        l=shiftSize
        if i+shiftSize>length:
            l=length-i
        try:
            msg='\x04'
            for x in buf[i:i+l]:
                try:
                    msg+=chr(x)
                except:
                    print "[!] Failed to get Ascii code for '%d'. Maybe unicode character"%x
                    msg+=' '
            msg+='\x68'
            a=dev.ctrl_transfer(33,0x09,0x304,USB_IF,msg,9)
            if DEBUG:
                print "W: ",
                for j in buf[i:i+l]:
                    print "%02x"%j,
                print ""
            if a==None or a<1:
                print "[!] Write was not sucessful (bytes sent: %d)"%a
        except usb.core.USBError as e:
            if e.args!=None and len(e.args)>0 and e.args!=(110,'Operation timed out'):
                print "[!] An error occurred while writing to %s: %s"%(PHONE_NAME,e)
        i+=shiftSize

def dev_read(dev):
    data=[]
    try:
        data=dev.read(USB_EP,8,USB_IF,2000);
    except usb.core.USBError as e:
        if e.args!=(110,'Operation timed out'):
            print "[!] An error occurred while reading from %s: %s"%(PHONE_NAME,e)
    if data!=None and len(data)>0:
        global qwerty 
        global callee
        if data[1]==0x84 and data[2]==0x51 and data[3]==0x11 and data[4]==0x01 and data[5]==0x00 and data[6]==0x00 and data[7]==0x00:
            print "[i] End call"
            qwerty=20
        elif data[1]==0x83 and data[2]==0x34 and data[4]==0x43 and data[5]==0x00 and data[6]==0x00 and data[7]==0x00 or \
             data[1]==0xc1 and data[2]==0x31 and data[3]==0xff and data[4]==0x43 and data[5]==0x04 and data[6]==0x9a and data[7]==0x50:
            if DEBUG:
                print "[i] Ping"
        elif qwerty==8:
            if DEBUG:
                print "[i] Contact details opened"
            if len(data)>2:
                get_contact(data[3])
                moreIndex=int(data[4])
                if moreIndex==0x00:
                    qwerty=4
                elif moreIndex>0x00:
                    qwerty=moreIndex+12  # => starting w/ 13 (since 12+(1+x)=(13+x)
            else:
                qwerty=0
        elif qwerty==6:
            if DEBUG:
                print "[i] Contacts menu opened"
            get_contact(data[3])
            qwerty=2
        elif data[1]==0xc1 and data[2]==0x31 and data[3]==0x01 and data[4]==0x43 and data[5]==0x05 and data[6]==0x9a and data[7]==0x4c:
            if DEBUG:
                print "[i] Skype Button pressed"
            qwerty=6
        elif data[1]==0x86 and data[2]==0x31 and data[3]==0x01 and data[4]==0x43 and data[5]==0x02 and data[6]==0x9a and data[7]==0x42:
            if DEBUG:
                print "[i] User status menu selected"
            qwerty=3
        elif data[1]==0xc1 and data[2]==0x31 and data[3]==0x01 and data[4]==0x43 and data[5]==0x05 and data[6]==0x9a and data[7]==0x4d:
            if DEBUG:
                print "[i] Details requested"
            qwerty=8
        elif qwerty==5:
            # print "[i] Set User status to %s"%skypeStates[data[2]] # skipped print since there are other 2 indication for the actual change
            set_status(data[2])
            qwerty=12
        elif data[1]==0xc1 and data[2]==0x31 and data[3]==0x01 and data[4]==0x43 and data[5]==0x03 and data[6]==0x9a and data[7]==0x43:
            if DEBUG:
                print "[i] Status change requested"
            qwerty=5
        elif data[1]==0xc1 and data[2]==0x21 and data[3]==0x11 and data[4]==0x04 and data[5]==0x80 and data[6]==0x9a and data[7]==0x60:
            #print "[i] Call"
            qwerty=9
        elif data[1]==0xc1 and data[2]==0x31 and data[3]==0x01 and data[4]==0x43 and data[5]==0x05 and data[6]==0x9a and data[7]==0x48:
            print "[i] Voicemail view selected"
            qwerty=15
        elif data[1]==0xc2 and data[2]==0x31 and data[3]==0x01 and data[4]==0x43 and data[5]==0x09 and data[6]==0x9a and data[7]==0x49:
            print "[i] Voicemail delete all"
            for v in skype.Voicemails:
                v.Delete()
            qwerty=16
        elif (data[1]==0xc1 or data[1]==0xc2 or data[1]==0xc3 or data[1]==0xc4 or data[1]==0xc5 or data[1]==0xc6) and data[2]==0x31 and data[3]==0x11 and data[4]==0x35:
            # calleeLength=data[5] such that qwerty18 will NOT "loop" forever, needed? NOT really,but could be used to be on the safe site
            callee=data[6:8] 
            qwerty=18
        elif qwerty==18:
            if data[1]>0x06 and data[1]<0x46:
                callee+=data[2:8]
                # qwerty=18 # NOTHING CHANGES
            elif data[1]>0x00 and data[1]<0x07:
                # print "[i] placecall"
                callee+=data[2:2+data[1]]
                qwerty=19
            else:
                print "[!] Could NOT understand call information"
                qwerty=0
        elif data[1]==0x86 and data[2]==0x31 and data[3]==0x11 and data[4]==0x43 and data[5]==0x02 and data[6]==0x9a:
            #print "[i] Call was rejected"
            # 86 31 11 43 02 9a
            qwerty=26
        elif data[1]==0x82 and data[2]==0x11 and data[3]==0x00 and data[4]==0x00 and data[5]==0x00 and data[6]==0x00:
            #print "[i] Incoming call handset accept call 1"
            qwerty=22
        elif data[1]==0x82 and data[2]==0x24 and data[3]==0x11 and data[4]==0x00 and data[5]==0x00 and data[6]==0x00:
            #print "[i] Incoming call handset accept call 2 (respond)"
            qwerty=23
        elif data[1]==0x85 and data[2]==0x31 and data[3]==0x11 and data[4]==0x35 and data[5]==0x01 and data[6]==0x15:
            #print "[i] Send R"
            qwerty=25
        if DEBUG:
            print "R: ",
            for b in data:
                print "%02x"%b,
            print ""
        if data[1]==0xc1:
            dev_read(dev);

def set_status(s):
    global skype
    if s>=0x00 and s<len(skypeStates):
        print "[i] %s Phone changed status from %s into %s"%(PHONE_NAME,skype.CurrentUserStatus,skypeStates[s])
        skype.CurrentUserStatus=skypeStates[s]

def multi_sort_friend(items,columns):
    comparers=[((col[1:].strip(),-1) if col.startswith('-') else (col.strip(),1)) for col in columns]
    def comparer(left,right):
        for fn,order in comparers:
            cmp1=getattr(left,fn)
            cmp2=getattr(right,fn)
            # put OFFLINE states at the very END of the list
            if fn=="OnlineStatus":
                cmp1=skypeStates.index(cmp1)
                cmp2=skypeStates.index(cmp2)
                if cmp1==skypeStates.index("OFFLINE"):
                    cmp1=10
                if cmp2==skypeStates.index("OFFLINE"):
                    cmp2=10
            # if FullName is NOT present use its Handle!
            if fn=="FullName":
                if cmp1==None or len(cmp1)<1:
                    cmp1=getattr(left,"Handle")
                if cmp2==None or len(cmp2)<1:
                    cmp2=getattr(right,"Handle")
            if (type(cmp1)==str or type(cmp1)==unicode) and (type(cmp2)==str or type(cmp2)==unicode):
                cmp1=cmp1.lower()
                cmp2=cmp2.lower()
            result=cmp(cmp1,cmp2)
            if result:
                return order*result
        else:
            return 0
    return sorted(items,cmp=comparer)

def get_contact(arg):
    global contact
    friends=multi_sort_friend(skype.Friends,['OnlineStatus','FullName'])
    contact=[len(friends)]
    if friends is not None and len(friends)>arg:
        contact.append(arg) # the index
        contact.append(friends[arg].Handle)
        contact.append(friends[arg].FullName)
        contact.append(friends[arg].OnlineStatus)
        contact.append(friends[arg].Language)
        contact.append(friends[arg].Birthday)
        contact.append(friends[arg].Sex)
        contact.append(friends[arg].PhoneHome)
        contact.append(friends[arg].PhoneMobile)
        contact.append(friends[arg].PhoneOffice)
        address=format_phone_address(friends[arg].City,friends[arg].Province,friends[arg].Country)
        contact.append(address)
        contact.append(friends[arg].Timezone)
        if arg==0 and len(friends)>1: # when first one send two contacts at once, otherwise we need to scroll only one contact (=>we are done)
            contact.append(1) # index
            contact.append(friends[1].Handle)  # == arg+1 (0+1)
            contact.append(friends[1].FullName)
            contact.append(friends[1].OnlineStatus)
            contact.append(friends[1].Language)
            contact.append(friends[1].Birthday)
            contact.append(friends[1].Sex)
            contact.append(friends[1].PhoneHome)
            contact.append(friends[1].PhoneMobile)
            contact.append(friends[1].PhoneOffice)
            address=format_phone_address(friends[1].City,friends[1].Province,friends[1].Country)
            contact.append(address)
            contact.append(friends[1].Timezone)

def OnAttach(s):
    if s==Skype4Py.apiAttachSuccess:
        print '[+] Successfully attached to skype process'

def OnCallStatus(call,status):
    global qwerty
    global skype
    global incomingCall
    global lastCall
    # print "[i] Skype changed call status to ",status, " for peer: ",call.PartnerHandle    # ," Name is: ",call.PartnerDisplayName
    caller=""
    if call.PartnerHandle is None or len(call.PartnerHandle)<1:
        # print "[i] Call from PSTN (Public switched telephone network), number is %s"%call.PstnNumber
        caller=call.PstnNumber
    else:
        caller=call.PartnerHandle+" "+call.PartnerDisplayName
    inprogress=False
    if status==Skype4Py.clsRinging and (call.Type==Skype4Py.cltIncomingP2P or call.Type==Skype4Py.cltIncomingPSTN):
        for c in skype.ActiveCalls:
            # print "Call status is ",c.Type," status is ",c.Status
            if c.Status==Skype4Py.clsInProgress:
                inprogress=True
        if not inprogress:
            incomingCall=[call,caller]
            qwerty=21
    elif status==Skype4Py.clsFinished or status==Skype4Py.clsRefused or status==Skype4Py.clsCancelled or status==Skype4Py.clsFailed or status==Skype4Py.clsMissed:
        qwerty=24 # end call from PC, therefore NO need to call endcall(), see qwerty==20

def OnUserStatus(s):
    print '[i] User status was changed to '+s

if __name__=='__main__':
    main()
