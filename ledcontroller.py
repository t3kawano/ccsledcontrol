# -*- coding: utf-8 -*-
"""
Created on Mon May  1 11:22:02 2017

@author: taizo kawano
Copyright (c) 2018, Taizo kawano

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

###########################################################################
221202 repeat schedular can be set 0.1 sec on time. not so precise. 
#10 or more msec error should exist.

170414 Blue LED light power measured by thorlab S175C
CCS LDR2-90BL2 24V 14W max 470 nm
put detector on the olympus stage and put led ring just under the objective
about 5cm away

light value  mW     mW/cm2
50           29     11.5
100          58     23
200          116    46
255          152    60
50           40     15
50           24

worm dead by 2 W/cm2

"""

import sys
import tkinter
import datetime
import time
import socket
import threading


##########################################
#communication 
class Communicator:

    def __init__(self, app):
        #stand alone for develping on the computer not connected to the ccs server
        self.standalone = False
        self.ccsaddress = "192.168.000.2"
        self.port = 40001
        socket.setdefaulttimeout(5)
        #socket.getdefaulttimeout()       
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.app = app

    def connect(self):
        try:
            self.client.connect((self.ccsaddress, self.port))
        except Exception as e:
            #self.app.writeinlog(e)
            print(type(e))
            print(e.args)
            if type(e) == socket.timeout:
                self.standalone = True
                print("run as stand alone")
                self.app.writeinlog("run as stand alone")
        #sys.exit()
        
    #tcp/ip connection part
    def sendorder(self, _string):
        #print(_string)
        #add checksum
        #ascii 16bit sum. take last 2 digit
        #hex(ord("@")) 0x40
        #16bit add take 2 digit is same as 10bit add convert 16bit take 2digit?
        #seems same
        sumofchr = 0
        for achr in _string:
            sumofchr = sumofchr + ord(achr)
         
        #hexstring = hex(ord("@")+ord("0")+ord("0")+ord("F")+ord("0")+ord("5")+ord("0"))
        hexstring = hex(sumofchr)
        #hex uses small letter? not capital
        #returnvalue = hexstring[-2:]
    
        sendstr = "".join([_string,hexstring[-2:],"\r","\n"])
        print(sendstr.strip())
        if not self.standalone:
            #writeinlog("not standalone?")
        
            try:
                self.client.send(sendstr.encode('utf-8')) 
                response = self.client.recv(4096)
            except Exception as e:
                self.app.writeinlog(str(type(e)))
                self.app.writeinlog(e.args)
                return 
            self.app.writeinlog("send "+sendstr.strip())
            #cant get response, and cause problem?
            #self.app.writeinlog("response "+response)
            #self.app.writeinlog("response problem?")

            #print(response)
        else:
            #writeinlog("standalone mode")
            self.app.writeinlog("send "+sendstr.strip())
    
#just caprue image and store it 
class CaptureImage(threading.Thread):
    """docstring for CaptureImage"""

    def __init__(self, count, total):
        super(CaptureImage, self).__init__()
        self.count=count
        self.total=total
        self.returnval = None
        
    def run(self):
        #print("CaptureImage thread (sub class) : " + str(datetime.datetime.today()))
        r, img= cvcapt.read()
        gray=cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        #need tocopy because in laterstep, put test on it
        self.returnval = gray.copy()
        #cv2.imshow('image', img)
        #cv2.imwrite("".join([datetime.datetime.now().strftime('%Y%m%d%H%M%S'),'.jpg']), img)
        #default jpg quality 95 85? 80?
        filename="".join([datetime.datetime.now().strftime('%Y%m%d%H%M%S'),'.jpg'])
        cv2.imwrite(dirname+os.sep+filename, gray, [int(cv2.IMWRITE_JPEG_QUALITY),80])

        #tif format saving seems not work in this way. need fix. it is saved as binary (black/white)image?
        #cv2.imwrite("".join([datetime.datetime.now().strftime('%Y%m%d%H%M%S'),'.tif']), gray,[cv2.IMWRITE_TIF_BINARY,0])
        font = cv2.FONT_HERSHEY_SIMPLEX
        #(img, text, (position), font, size, color, linewidth,)
        cv2.putText(gray, str(self.count)+"/"+str(self.total), (50,50), font, 1, 255,2)
        cv2.imshow('image', gray)
        print("===captured==="+str(datetime.datetime.now()))   
    
    #pass image to other thread
    def getimg(self):
        return self.returnval        


#schedular thread just for one period
class SingleSchedular(threading.Thread):
    """docstring for SingleSchedular"""

    #repeat n times, t delay. in this case n =1
    #def __init__(self, n, t, lcg):
    def __init__(self, t, lcg):
        super(SingleSchedular, self).__init__()
        #self.n = n
        self.t = t
        self.currentimg = None
        self.previousimg = None
        self.lcg = lcg
        self._running = True

    def run(self):
        starttime = time.time()
        #self.lcg.writeinlog(" === start SingleSchedular thread (sub class) at "+str(starttime))
        print(" === start SingleSchedular thread (sub class) at "
              +str(starttime))
        self.lcg.turnon1()
        while (time.time()-starttime) < self.t and self._running:
            #wait
            #without no process, cpu works 100% so wait 10msec
            #time.sleep(0.01)
            #100msec? not bad for timing but not much change cpu usage
            time.sleep(0.01)
            pass
        #self.lcg.turnoff1("")
        self.lcg.turnoff1()
        #self.lcg.writeinlog("off "+str(time.time()))
        #print(" === end SingleSchedular thread  ===")

    def shutdown(self):
        self.lcg.writeinlog("ss shutdown")
        self._running = False

#schedular thread to repeat 
class RepeatSchedular(threading.Thread):
    """docstring for RepeatSchedularr"""

    #repeat n times, t delay
    def __init__(self, n, t, lcg):
        super(RepeatSchedular, self).__init__()
        self.n = n
        self.t = t
        self.currentimg = None
        self.previousimg = None
        self.stop_event = threading.Event()
        self._running = True
        
        self.lcg = lcg

    def run(self):
        starttime = time.time()
        print(" === start RepeatSchedularr thread (sub class) at "+str(starttime))
        for i in range(self.n):
            if self._running:
            #if not self.stop_event.is_set():
                
                #ss = SingleSchedular(1, int(self.lcg.ontime), self.lcg)
                #ss = SingleSchedular(int(self.lcg.ontime), self.lcg)
                ss = SingleSchedular(float(self.lcg.ontime), self.lcg)#221202 changed to float
                ss.setDaemon(True)
                ss.start()
                while (time.time()-starttime) < self.t*(i+1):
                    #if not self.stop_event.is_set():
                    if self._running:                    
                        #wait
                        #without no process, cpu works 100% so wait 10msec
                        #time.sleep(0.01)
                        #100msec? not bad for timing but not much change cpu usage
                        time.sleep(0.01)
                        pass
                    else:
                        ss.shutdown()
                        ss = None
                        break
            else:             
                break
        self.lcg.writeinlog(" === end RepeatSchedularr thread  === repeated " + str(i+1)+" times")   
        print(" === end RepeatSchedularr thread  === repeated " + str(i+1)+" times")
    
    def stop(self):
        self.stop_event.set()
        
    def shutdown(self):
        self.lcg.writeinlog("rs shutdown")
        self._running = False

#20170804
#schedular thread to run complex order
#the format is [[on time, off time, intensity, repeat times],[]]
#eg. [[15,45,50,5],[15,45,100,5],[15,45,150,5]]
#in futrue, RepeatSchedular class funciton will be done wiht this class
class ProgramableSchedular(threading.Thread):
    #orderarg [[15,45,50,5],[15,45,100,5],[15,45,150,5]]
    def __init__(self, orderarg, lcg):
        super(ProgramableSchedular, self).__init__()
        self.orderarg = orderarg
        self.n = len(orderarg)
        #self.t = t
        self.currentimg = None
        self.previousimg = None
        self._running = True
        
        self.lcg = lcg
        
    def run(self):
        starttime = time.time()
        print(" === start ProgramableSchedular thread (sub class) at "+str(starttime))
        for i in range(self.n):
            starttime = time.time()
            if self._running:
                valforaset = self.orderarg[i]
                times = valforaset[3]
                delay = int(valforaset[0]+valforaset[1])
                self.lcg.setintensity(0, int(valforaset[2]))
                self.lcg.writeinlog("i "+str(i)+" valforaset "+str(valforaset)+
                " times "+str(times)+" delay "+str(delay)+
                " intensity "+str(valforaset[2]))
                for j in range(times):
                    if self._running:
                    #if not self.stop_event.is_set():
                        #ss = SingleSchedular(1, int(self.lcg.ontime), self.lcg)
                        ss = SingleSchedular(int(valforaset[0]), self.lcg)
                        ss.setDaemon(True)
                        ss.start()
                        while (time.time()-starttime) < delay*(j+1):
                            #if not self.stop_event.is_set():
                            if self._running:                    
                                #wait
                                #without no process, cpu works 100% so wait 10msec
                                #time.sleep(0.01)
                                #100msec? not bad for timing but not much change cpu usage
                                time.sleep(0.01)
                                pass
                            else:
                                ss.shutdown()
                                ss = None
                                break
                    else:
                        break
        self.lcg.writeinlog(" === end ProgramableSchedular thread  ===")   
        print(" === end ProgramableSchedular thread  === ")
        self.lcg.ps = None
        
    def shutdown(self):
        self.lcg.writeinlog("ps shutdown")
        self._running = False


###############################################
class Ledcontrollergui(tkinter.Frame):
    
    #ui
    defaultontime = 15
    defaultofftime = 45
    defaultintensity = 50
    defaultcheckboxvale = True
    defaultprogram = "[15,45,50,10],[15,45,100,10]"
    #defaultprogram = "[[5,5,50,3],[2,3,100,2]]"
    
    def __init__(self, master=None):
        tkinter.Frame.__init__(self, master)
        #self.pack()
        
        #in the future these value had better saved in file,
        # and use next session.
        self.ontime = Ledcontrollergui.defaultontime
        self.offtime = Ledcontrollergui.defaultofftime
        self.intensity = Ledcontrollergui.defaultintensity
        self.checkboxvale = Ledcontrollergui.defaultcheckboxvale
        
        self.onofftoggle1 = True
        
        #repeat schedular
        self.rs = None
        #programable schedular
        self.ps = None
        
        ######################gui prep
        #slider
        self.sliderintensity = tkinter.IntVar()
        self.sliderintensity.set(50)
        #scale
        s1 = tkinter.Scale(root, label = 'intensity', orient = 'h',\
                           length = 250, from_ = 0, to = 255,\
                           variable = self.sliderintensity,\
                           command = self.changeintensity)
        s1.place(x = 10, y = 10)
        
        
        #button
        self.button1 = tkinter.Button(text = u"ON", width = 10, height = 2)
        self.button1.place(x =10, y = 100)
        self.orignalbottoncolor = self.button1.cget("background")
        self.button1.bind("<Button-1>", self.toggle1)#turnon1)
        
        """
        #button
        button2 = tkinter.Button(text = u"OFF", width = 10, height = 2)
        button2.place(x =100, y = 100)
        button2.bind("<Button-1>", turnoff1)
        """
         
        #label
        label1 = tkinter.Label(text = u"on time (sec)")
        label1.place(x=300, y = 10)
        
        
        # box
        self.box3 = tkinter.Entry(width = 3 )
        self.box3.insert(tkinter.END, str(Ledcontrollergui.defaultontime))
        self.box3.place(x=400, y = 10)
        
        # get the value
        self.ontimestr = self.box3.get() 
        
        
        
        #label
        label2 = tkinter.Label(text = u"off time (sec)")
        label2.place(x=300, y = 30)
        
        # box
        self.box4 = tkinter.Entry(width = 3)
        self.box4.insert(tkinter.END, str(Ledcontrollergui.defaultofftime))
        self.box4.place(x=400, y = 30)
        
        # get the value
        self.offtimestr = self.box4.get()
        
        
        
        #label
        label3 = tkinter.Label(text = u"intensity (<255)")
        label3.place(x=300, y = 50)
        
        # box
        self.box5 = tkinter.Entry(width = 3)
        self.box5.insert(tkinter.END, str(Ledcontrollergui.defaultintensity))
        self.box5.place(x=400, y = 50)
        
        # get the value
        self.intensitystr = self.box5.get()
        
        
        
        
        #checkbox
        self.booleanvar1 = tkinter.BooleanVar()
        self.booleanvar1.set(Ledcontrollergui.defaultcheckboxvale)
        
        self.checkbox1 = tkinter.Checkbutton(text = u"repeat",\
                                        variable = self.booleanvar1)
        self.checkbox1.place(x=400, y = 70)
        
        
        
        
        #button
        self.button3 = tkinter.Button(text = u"run", width = 5)
        self.button3.place(x =300, y = 100)
        self.button3.bind("<Button-1>",  self.runtheprogram)
        
        
        #button
        self.button4 = tkinter.Button(text = u"stop", width = 5)
        self.button4.place(x =400, y = 100)
        self.button4.bind("<Button-1>", self.stoptheprogram)
        
        
        #text field. for illumination program
        self.programtextfield = tkinter.Text(width = 80, height = 2)
        self.programtextfield.insert(tkinter.END, str(Ledcontrollergui.defaultprogram))
        self.programtextfield.place(x = 10, y = 150)
        
        #button
        self.button5 = tkinter.Button(text = u"run", width = 5)
        self.button5.place(x =10, y = 180)
        self.button5.bind("<Button-1>", self.runuserdefindprogram)
        #button
        self.button6 = tkinter.Button(text = u"stop", width = 5)
        self.button6.place(x =50, y = 180)
        self.button6.bind("<Button-1>", self.stopuserdefindprogram)
        
        #text field. mainly used for debug and log
        self.textfield = tkinter.Text(width = 80, height = 10)
        self.textfield.place(x = 10, y = 220)
        

        ###################### communicator prep        
        self.comm = Communicator(self)
        self.comm.connect()
        
    
    ##########################
    #button action
    def runtheprogram(self, event):
        #ontime type is str
        #print(type(ontime))
        parametersets = self.getvalues()
        print(str(parametersets))
        outputstr = " ".join(["ontime", self.ontimestr, \
                              "offtime" , self.offtimestr,\
                              "intensity",self.intensitystr,\
                              "checkboxvale", str(self.checkboxvale)])
        #outputstr = " ".join(parametersets)
        print(outputstr)
        self.writeinlog(outputstr)
        if self.checkboxvale:
            #repeat on off siginal. period length is on+off 
            #to repeat longtime, put large number for now 259200 is 3days
            if self.rs is None:
                self.rs = RepeatSchedular(259200, self.ontime+self.offtime, self)
                self.rs.start()
            else:
                outputstr = "There is running program"
                print(outputstr)
                self.writeinlog(outputstr)
                    
        else:
            #just one time wave with ontime length
            ss = SingleSchedular(1, self.ontime, self)
            ss.start()
            #ss.join()
        self.testmethod()
        

    def stoptheprogram(self, event):
        outputstr = "lcg "+ "stop"
        print(outputstr)
        self.writeinlog(outputstr)
        if self.rs is None:
            print("not exist rs")
        else:
            #self.rs.stop()
            self.rs.shutdown()
            self.rs = None
            
    def runuserdefindprogram(self, event):
        orderstr = self.programtextfield.get("1.0",tkinter.END) 
        print(orderstr)
        #return 
        #be careful. no check of the str
        orderlist = eval("["+orderstr+"]")
        #orderlist = [[5,5,50,3],[2,3,100,2]]
        self.writeinlog(str(orderlist))
        if self.ps is None:
            self.ps = ProgramableSchedular(orderlist, self)
            self.ps.start()
        else:
            outputstr = "There is running program"
            print(outputstr)
            self.writeinlog(outputstr)
        
    def stopuserdefindprogram(self, event):
        outputstr = "lcg "+ "usr defined stop"
        print(outputstr)
        self.writeinlog(outputstr)
        if self.ps is None:
            print("not exist ps")
        else:
            #self.rs.stop()
            self.ps.shutdown()
            self.ps = None
        
        
    
    def getvalues(self):
        #these are local variables
        #strings
        self.ontimestr = self.box3.get() 
        #self.ontime = int(self.ontimestr)
        self.ontime = float(self.ontimestr)#221202 changed to float
        self.offtimestr = self.box4.get()
        #self.offtime = int(self.offtimestr)
        self.offtime = float(self.offtimestr)#221202 changed to float
        self.intensitystr = self.box5.get()
        self.intensity = int(self.intensitystr)
        #boolean
        self.checkboxvale = self.booleanvar1.get()
        return [self.ontimestr, self.offtimestr, \
                self.intensitystr, self.checkboxvale]
    
    
    def check(self):
        outputstr = str(self.booleanvar1.get())
        print(outputstr)
        self.writeinlog(outputstr)
        
    #add \n end of the string
    def writeinlog(self, string):
        thetime = datetime.datetime.today().strftime("%Y%m%d %H:%M:%S.%f")
        #print(str(datetime.datetime.today()))
        self.textfield.insert(1.0,"".join([thetime," ", string+"\n"]))
    
    
    def testmethod(self):
        print("test")
    
    
    ##########################################################
    #control part
    
    def changeintensity(self, event):
        value = self.sliderintensity.get()
        #print(value)
        self.box5.delete(0, tkinter.END)
        self.box5.insert(tkinter.END,str(value))
        self.setintensity(0, value)
    
    def setintensity(self, channel, value):
        zfilledvaluestr = str(value).zfill(3)
        orderstr = "".join(["@",str(channel).zfill(2),"F",zfilledvaluestr])
        #parameters = getvalues()
        #self.writeinlog("setintensity "+str(self.getvalues()))
        self.writeinlog("set "+ "channel " + str(channel) + " intensity "+str(value))
        self.comm.sendorder(orderstr)        
        
    def toggle1(self, event):
        #self.writeinlog("toggle1")
        #global cause error only made a exe with cx_freeze?
        #global onofftoggle1
        #self.writeinlog(str(self.onofftoggle1))
        if self.onofftoggle1:
            self.button1.config(text=u"OFF", bg="red")
            self.onofftoggle1 = False
            #self.turnon1(event)
            self.turnon1()
        else:
            self.button1.config(text=u"ON", bg=self.orignalbottoncolor)
            self.onofftoggle1 = True
            #self.turnoff1(event)
            self.turnoff1()
                
    #def turnon(event, channel):
    #def turnon1(self, event):
    def turnon1(self):
        #orderstr = "".join(["@",str(channel).zfill(2), "L1"])
        orderstr = "".join(["@00", "L1"])
        #self.writeinlog("lcg "+"ON "+str(self.getvalues()))
        self.writeinlog("lcg "+"ON ")
        self.comm.sendorder(orderstr)
        #self.writeinlog("turnon1 check " )

    
    #def turnoff1(self, event):
    def turnoff1(self):
        #orderstr = "".join(["@",str(channel).zfill(2), "L0"])
        orderstr = "".join(["@00", "L0"])
        #self.writeinlog("lcg "+"OFF "+str(self.getvalues()))
        self.writeinlog("lcg "+"OFF ")
        self.comm.sendorder(orderstr)
    
    



##########################################################
#run the controller
root = tkinter.Tk()
root.title(u"led controller")
root.geometry("600x400")

app = Ledcontrollergui(master = root)
app.mainloop()















