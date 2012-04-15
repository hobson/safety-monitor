#!C:\Python25\python.exe
"""A function that scans for serial ports and tests them for the presence of a TT ZigBee device"""
import serial
import glob
import time

def serialPortsAvailable(OperatingSystem="Win32"):
  port_num_name = []
  challenge =  "\x14\x0D\x0A"
  response = "\x0D\x0ARES>"
  if OperatingSystem=="Linux":
    # just return the serial port names/paths based on what's in the dev directory
    port_name = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') # actHL: are there more serial ports?
    for i in range(len(port_names)):
      port_num_name.append((None,port_name[i]))
  elif OperatingSystem=="OSX":
    port_num_name = None
  else: #elif (OperatingSystem=="Win32") or (OperatingSystem==None):
    for i in range(256):
      try:
        ser = serial.Serial(i)
        # 56K baud?
        ser.baudrate = 115200 #ser.BAUDRATES[11] #actHL: get this right for 115200 bps or 57600
        # 8N1 no handshake, serial port settings
        ser.bytesize = 8
        ser.setParity('N')
        ser.setStopbits(1)
        ser.setTimeout(0.02) # timeout is in seconds and even 0.001 seems to be enough for the RZUSB stick, but 20 ms seems to be the most reliable
        ser.write(challenge)
        time.sleep(0.003) # wait an arbitrary 3 milliseconds for the uart on the zigbee to respond, probably unnecessary, usually works without it
        text = ser.read(1) # wiat for the timeout and try to read one byte
        if text:  # see if anything came back in the first byte
          n = ser.inWaiting()   #look if there is more to read
          if n:
            text = text + ser.read(n) #get it
          if len(text)>6:
            if text[-len(response):] == response:
              port_num_name.append( (i, ser.portstr) )
              if halt_on_success:
                break
        ser.close() 
      except serial.SerialException:
        pass # keep complaints to yourself
  return port_num_name
  
if __name__ == "__main__":
  print "Scanning serial ports..."
  port_num_name = serialPortsAvailable()
  if len(port_num_name)>0:
    print "Found",len(port_num_name),"ports with Transceive Technology products attached:"
    for num,name in port_num_name:
      print " port",num+1," is called '"+str(name)+"' by your OS."
  else:
    print "None of the serial ports had a Transceive Technology product attached."