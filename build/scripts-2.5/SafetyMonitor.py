#!C:\Python25\python.exe
"""A Model-View-Controller version of the Mommy Station software for"""
import wx
from wx.lib.pubsub import Publisher as pub
import Mesh # this is the model
import RadioFrame # this is one of the Views
from log import log
import numpy as np
import thread
import time # sleep()
import DataSource
import Packet
import Queue
import HomeSketch

# the whol point of a queue is to gatekeep access to data where conflicts might exist
# It's not right to proliferate Queues like this that edit the same object (view)
positions2view = Queue.Queue() 
positions2model = Queue.Queue()
distances2view = Queue.Queue() # 4view denoting that distances are passed as the message argument

class Controller(object):
  def __init__(self, app):
    global _docList
    _docList = []
    self.pause = False
    self.done = False
    self.data  = DataSource.DataSource()
    self.model = Mesh.Mesh() #WARNING a simple typo of self.model=Mesh , i.e. without the "()" at the end, from Mesh import Mesh, caused me a lot of grief, compiles and doesn't run __init__
    #self.view = RadioFrame.RadioFrame(parent=None, id=wx.ID_ANY, title="Radio Location Display Screen", pos=wx.DefaultPosition, size=(680,500) ) # standard map view of Mesh data, None = no parent window
    self.view = RadioFrame.RadioFrame(name="Safety Monitor") # standard map view of Mesh data, None = no parent window
    self.sketcher = HomeSketch.DrawingFrame(None, -1, "Untitled")
    _docList.append(self.sketcher)
    self.sketcher.Centre()
    self.sketcher.Show(True)
    pub.subscribe(self.OnPubMessage)        
    thread.start_new_thread(self.processPackets, ()) # () is an empty tuple to hold any arguments required for the processPackets() member function
    self.view.Show()
    app.SetTopWindow(self.view)
   # No file name was specified on the command line -> start with a
    # blank document.
    #return True
         
  def processPackets(self):
    log.debug("Starting processPackets()")
    i=0
    while self and not self.done: #alive: # what about isRunning() member function for apps?
      #log.debug("Sleeping for half a second "+str(i))
      for j in range(10): # don't process more than one packet a second and keep checking self.done while waiting
        if self.done:
          return
        time.sleep(0.05) 
      if not self.pause and not self.done:
        log.debug("processing packet "+str(i))
        i += 1
        p = self.data.getPacket()
        if p != None and p.t>0 and p.neighbors[0][1]>0 and self and not self.done:
          self.model.Add(p) # so model is updated directly
          # now need to update view
          pos = self.model.GetPositions()
          while self.view.panel1.Moving and not self.done:
            time.sleep(0.01) # wait 10 milliseconds for user to stop dragging objects around
            #pass
          self.view.panel1.Moving = True # so mouse tasks cant move 
          pub.sendMessage("REFRESH")  
          #self.view.SetPositions(pos)
          #log.debug("Mesh object:\n"+str(self.model))
          pub.sendMessage("DISTANCE")  
          #d = self.model.GetDistances()
          #log.debug("Distances retrieved from Mesh:\n"+str(d))
          #self.view.SetDistances(d)    # nothing prevents this from interfering with other tasks
          self.view.panel1.Moving = False # resume allowing user to drag objects around

  # this is the wrong way to do it, the Mesh, View, and DataSource objects need to be queued otherwise get/set conflicts are still possible
  def OnPubMessage(self, msg):
      if self.done:
        return
      log.debug("Controller received message from pubsub module for topic "+str(msg.topic)+" and data:\n"+str(msg.data)+".")
      if "POSITION" in msg.topic:
        log.debug("Controller telling model to SetPositions to "+str(self.view.GetPositions())+".")
        positions2model.put(self.view.GetPositions())
      if "REFRESH" in msg.topic:
        log.debug("Controller telling view to SetPositions to "+str(self.model.GetPositions())+".")
        positions2view.put(self.model.GetPositions())
        #distances2view.put(self.model.GetDistances())
     # can't figure out how to pass differenct data to different attributs in the same object going through the same queue
      if "DISTANCE" in msg.topic:
        log.debug("Controller telling view1 to SetDistances to "+str(self.model.GetDistances())+".")
        distances2view.put(self.model.GetDistances())
      if "OPTIMIZE" in msg.topic:
        log.debug("Controller telling model to OptimizePositions().")
        self.view.panel1.Moving = True # stop responding to user click/drags on objects
        self.pause = True # stop processing packets
        self.model.OptimizePositions()
        self.view.panel1.Moving = False # resume responding to user click/drags on objects
        self.pause = False # resume processing packets
        log.debug("Finished optimization so setting view positions")
        positions2view.put(self.model.GetPositions())
      if "DONE" in msg.topic:
        log.debug("Controller stopping packet processing.")
        self.done = True
        time.sleep(0.2)
        return
      if "PAUSE" in msg.topic:
        log.debug("Controller paused or started packet processing.")
        self.pause = not self.pause
      # would probably be better to just trigger normal mouse click and drag events to move the objects to avoid synchronizing cue use
      p2m=[]
      try:
        p2m = positions2model.get_nowait()# don't do any pausing or anything because this will often except
        positions2model.task_done()
      except Queue.Empty: pass
      if len(p2m):
        self.model.SetPositions(p2m)
      if self.done:
        return
      p2v=[]
      try:
        p2v=positions2view.get_nowait() # don't do any pausing or anything because this will often except
        positions2view.task_done()
      except Queue.Empty: pass
      if len(p2v):
        self.view.panel1.Moving = True # stop responding to user click/drags on objects
        self.pause = True # stop processing packets  
        self.view.SetPositions(p2v)
        self.view.panel1.Moving = False # stop responding to user click/drags on objects
        self.pause = False # stop processing packets
      d=[]
      if self.done:
        return
      try:
        d = distances2view.get_nowait()
        distances2view.task_done()
      except Queue.Empty: pass
      if len(d):
        log.debug("Calling view.SetDistances")
        self.view.panel1.Moving = True # stop responding to user click/drags on objects
        self.pause = True
        self.view.SetDistances(d)
        self.view.panel1.Moving = False # resume allowing user to drag objects around
        self.pause = False
      
      

if __name__ == "__main__":
  app = wx.App(False)
  Controller(app)
  app.MainLoop()