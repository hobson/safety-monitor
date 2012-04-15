#!C:\Python25\python.exe
#import wx
from wx.lib.pubsub import Publisher as pub
import serialPortsAvailable
import serial
import threading
import time #sleep
import re #regular expressions
import Packet
from log import log # logging module and some minor customizations


#from RadioFrame import RadioFrame
#import math # min and max


#HL: the order of these list elements must match the GUI radio button order

class DataSource(object):

  def __init__(self, *args, **kwds):
    self.fileName = "rev20.log"

    self.serial_newline = '\r' # not necessary
    self.serial = serial.Serial()
    self.serial_challenge =  "\x14\x0D\x0A"
    self.serial_response = "\x0D\x0ARES>"
    self.serial_start_listener = "n\x0D\x0A" # sniff command for Atmel RZUSB Stick
    self.serial_portnum = None
    numname = serialPortsAvailable.serialPortsAvailable()
    if len(numname)==1:
      log.debug("Found a serial port that responds as if a Transceive Technology product is attached")
      self.serial_portnum = numname[0][0]
      self.serialStartListen(self.serial_portnum)
      
    if self.serial_portnum == None:
      log.debug("No serial port was found, so trying the '"+self.fileName+"' file.")
      try:
        # To ensure timely file.close(), Python25 documentation recommends: 
        #   with open("myfile.txt") as f: 
        #     for line in f:
        #       print line
        self.fileHandle = open(self.fileName, "r")
      except IOError, (errno, errstr):
        log.error("Unable to find & open input file named '"+self.fileName+"' due to I/O error({0}): {1}".format(errno, errstr))
        self.fileHandle = False
        #actHL: add additional searches within parent directories, sub directories and for any *.log text files
      except OSError, (errno,errstr):
        log.error("Unable to find & open input file named '"+self.fileName+"' due to OS error({0}): {1}".format(errno, errstr))
        self.fileHandle = False
    
  def getPacket(self):
    log.debug("GetData...")
    if(self.fileHandle):
      text=self.fileHandle.readline()
      if (len(text)<1):
        self.fileHandle.close() # file is empty so close it
        return None
      #pub.sendMessage("PACKET",p) #actHL: Use global Queue object instead of pubsub, e.g. import queue_stuff.py
    elif(self.serial):
      text = self.serial.read(1)      #read one, with timeout
      if text:              #check if not timeout
        n = self.serial.inWaiting()   #look if there is more to read
        if n:
          text = text + self.serial.read(n) #get whatever's available
    if text:
      text = text.replace(self.serial_newline, '\n')  #actHL: not necessary?
      return(Packet.Packet(text))
    return None
    #pub.sendMessage("PACKET",p)

  def serialStartListen(self, portnum=None):
    if portnum==None:
      portnum = self.serial_portnum  
    self.serial = serial.Serial(portnum)
    # 56K baud?
    self.serial.baudrate = 115200 #ser.BAUDRATES[11] #actHL: get this right for 115200 bps or 57600
    # 8N1 no handshake, serial port settings
    self.serial.bytesize = 8
    self.serial.setParity('N')
    self.serial.setStopbits(1)
    self.serial.setTimeout(0.02) # timeout is in seconds and even 0.001 seems to be enough for the RZUSB stick, but 20 ms seems to be the most reliable
    self.serial.write(challenge)
    time.sleep(0.003) # wait an arbitrary 3 milliseconds for the uart on the zigbee to respond, probably unnecessary, usually works without it
    text = ser.read(1) # wiat for the timeout and try to read one byte
    if text:  # see if anything came back in the first byte
      n = ser.inWaiting()   #look if there is more to read
      if n:
        text = text + ser.read(n) #get it
      if len(text)>=len(self.serial_response):
        if text[-len(self.serial_response):] == self.serial_response:
          self.serial.write(self.serial_start_listener)

    """Menu point StartMonitor. """
    log.debug("Reading from %s [%s, %s%s%s%s%s]" % (self.serial.portstr,
                  self.serial.baudrate,self.serial.bytesize,self.serial.parity,self.serial.stopbits,self.serial.rtscts and ' RTS/CTS' or '',
                  self.serial.xonxoff and ' Xon/Xoff' or '',))
    self.serial.write("\x14") #HL: 0x14 = 20 = Ctrl-T = DC4 or DCL
    #time.sleep(.05)
    self.serial.write("n" + self.newline)

  def stopPacketMonitor(self, event=None):
    self.SetTitle("Reading from %s [%s, %s%s%s%s%s] paused..." % (self.serial.portstr,
                  self.serial.baudrate,self.serial.bytesize,self.serial.parity,self.serial.stopbits,self.serial.rtscts and ' RTS/CTS' or '',
                  self.serial.xonxoff and ' Xon/Xoff' or '',))
                  

if __name__ == "__main__":
  ds = DataSource()
  for i in range(10):
    log.debug(str(ds.getPacket()))
    
