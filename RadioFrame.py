#!/usr/bin/env python
"""Frame to display radios as circles and allow user to drag them around"""
import wxversion
wxversion.select('2.8')
import wx
import sys
sys.path.append("..")
from floatcanvas import NavCanvas as NC
import Resources
#from floatcanvas import Resources
from floatcanvas import FloatCanvas as FC
from floatcanvas.Utilities import BBox
import numpy as np
import time # sleep()
#import math # can use numpy.sin and numpy.sqrt etc instead of math...
from log import log # logging module and some minor customizations
from wx.lib.pubsub import Publisher as pub

class RadioFrameError(Exception):
    pass
    
class MovingObjectMixin:
  """Methods required for a Moving object"""
  def GetOutlinePoints(self): # turns 2 corner points into 4 corner points for drawing a box
    BB = self.BoundingBox
    OutlinePoints = np.array( ( (BB[0,0], BB[0,1]),(BB[0,0], BB[1,1]),
                                (BB[1,0], BB[1,1]),(BB[1,0], BB[0,1]),) )
    return OutlinePoints
class ConnectorObjectMixin:
  """Mixin class for DrawObjects that can be connected with lines"""
  def GetConnectPoint(self):
    return self.XY
class MovingBitmap(FC.ScaledBitmap, MovingObjectMixin, ConnectorObjectMixin):
  """ScaledBitmap Object that can be moved """
  pass
class MovingCircle(FC.Circle, MovingObjectMixin, ConnectorObjectMixin):
  """Circle Object that can be moved"""
  def GetOutlinePoints(self): # turns 2 corners into 4 corners for drawing a box
    CIRC_POINTS = 32
    BB = self.BoundingBox
    r = abs(BB[1][0]-BB[0][0])/2    # circle radius
    OutlinePoints = np.zeros((CIRC_POINTS,2))
    for i,j in enumerate(OutlinePoints):
      theta = np.pi*i*2/CIRC_POINTS
      OutlinePoints[i] = self.XY + (r*np.sin(theta),r*np.cos(theta))
    return OutlinePoints
    
class MovingGroup(FC.Group, MovingObjectMixin, ConnectorObjectMixin):
  """A group that has a bounding box and connection point"""
  def GetConnectPoint(self):
    return self.BoundingBox.Center
  def Move(self,dXY):
    FC.Group.Move(self,dXY)
    self._Canvas.BoundingBoxDirty = True
    
class RadioObject(MovingGroup):
  """A moving object consisting of an ellipse (or circle) with text."""
  def __init__(self, LabelText="A", XY=[0.0,0.0], WH=[2.0,2.0], Family=wx.SWISS, Weight=wx.BOLD, FillColor="Green", TextColor="Black",
               LineColor="Black", LineWidth=2, LineStyle="Solid", InForeground=False, IsVisible = True):
    log.debug("New Radio initialized with position "+str(XY)+".")
    #self.XY = np.asarray(XY, np.float).reshape(2,) # not sure if I should create this local variable at all
    #self.WH = np.asarray(WH, np.float).reshape(2,)
    self.local_label = FC.ScaledText(LabelText, XY=XY, Size=WH[1]/1.8, Family=Family, Weight=Weight, Color=TextColor, Position='cc')
    self.local_ellipse = FC.Ellipse( (XY[0]-WH[0]/2.,XY[1]-WH[1]/2.), WH, FillColor=FillColor, LineStyle=LineStyle, LineWidth=LineWidth)
    log.debug("New Ellipse initialized with position "+str(self.local_ellipse.XY)+"and WH dimensions " + str(self.local_ellipse.WH) + ".")  
    MovingGroup.__init__(self, (self.local_ellipse, self.local_label), InForeground, IsVisible)
    log.debug("Finished RadioObject.__init__")
  def SetPosition(self,newXY=[0.,0.]):
    """XYObject mixin only provides Move() for relative shifts due to possiblity of Groups"""
    # do I need to move the internal Label and Ellipse objects?
    MovingGroup.Move(self,np.asarray(newXY, np.float).reshape(2,)-self.BoundingBox.Center)
    #self.local_label.Move( self,np.asarray(newXY, np.float).reshape(2,)-self.BoundingBox.Center)
    #self.local_ellipse.Move(self,np.asarray(newXY, np.float).reshape(2,)-self.BoundingBox.Center)
    self._Canvas.BoundingBoxDirty = True
  def Set2DPosition(self,newXY=[0.,0.]):
    """Not in original XYObject mixin which only has Move() (relative shifts) due to possiblity of Groups"""
    self.SetPosition(newXY)
  def Set3DPosition(self,newXY=[0.,0.,0.]):
    """Not in original XYObject mixin which only has Move() (relative shifts) due to possiblity of Groups"""
    self.SetPosition(newXY[0:2])
  def Get3DPosition(self):
    p = self.BoundingBox.Center
    position = np.append(p,0.)
    return self.p #return a 3-D position even if XY is only 2D
  def Get2DPosition(self):
    return self.BoundingBox.Center #return a 3-D position even if XY is only 2D
  def GetPosition(self):
    return self.BoundingBox.Center #return a 3-D position even if XY is only 2D

def DCM(angle=np.pi/6, is3d=False, axis=2, dtype=float, order='C'):  
  """Direction cosine matrix"""
  s = np.sin(angle)
  c = np.sin(angle)
  a = np.ndarray.__new__(matrix, (2+int(is3d),2+int(is3d)), dtype, order=order)
  if is3d:
    if axis==2:
      a = matrix('c s 0; -s c 0; 0 0 1',dtype,order=order)
    elif axis==1:
      a = matrix('1 0 0; 0 c s; 0 -s c',dtype,order=order)
    else:
      a = matrix('c 0 -s; 0 1 0; s 0 c',dtype,order=order)
  else:
    a = matrix('c s;-s c')
    
class ConnectorLine(FC.LineOnlyMixin, FC.DrawObject,):
  """A Line that connects two objects -- it uses the objects to get its coordinates"""
  def __init__(self, Object1, Object2, LineColor = "Black", LineStyle = "Solid", LineWidth=1, InForeground=False):
    FC.DrawObject.__init__(self, InForeground)
    self.Object1 =  Object1       
    self.Object2 =  Object2       
    self.LineColor = LineColor
    self.LineStyle = LineStyle
    self.LineWidth = LineWidth
    self.CalcBoundingBox()
    #self.LengthPen = wx.Pen('GRAY', 1, wx.SHORT_DASH)
    #self.Pen = wx.TRANSPARENT_PEN
    self.SetPen(LineColor,LineStyle,LineWidth)
    self.HitLineWidth = max(LineWidth,self.MinHitLineWidth)
  def CalcBoundingBox(self):
    self.BoundingBox = BBox.fromPoints((self.Object1.GetConnectPoint(),
                                        self.Object2.GetConnectPoint()) ) # a tuply containing 2 numpy 2-element arrays
    if self._Canvas:
      self._Canvas.BoundingBoxDirty = True
  def _Draw(self, dc , WorldToPixel, ScaleWorldToPixel, HTdc=None):
    Points = np.array( (self.Object1.GetConnectPoint(),
                       self.Object2.GetConnectPoint()) )
    Points = WorldToPixel(Points)
    dc.SetPen(self.Pen)
    dc.DrawLines(Points)
    if HTdc and self.HitAble:
      HTdc.SetPen(self.HitPen)
      HTdc.DrawLines(Points)

class ExtendedConnectorLine(ConnectorLine):
  def __init__(self, Object1, Object2, Lengths=[0,0], LineColor = "Black",LineStyle = "Solid",
               LineWidth    = 1, InForeground = False):
    self.Lengths = Lengths
    self.LengthPoints = None
    ConnectorLine.__init__(self, Object1, Object2, LineColor = LineColor,LineStyle = LineStyle,
                           LineWidth    = LineWidth, InForeground = InForeground)
    FC.DrawObject.__init__(self, InForeground)
    self.LengthPen = wx.Pen(wx.LIGHT_GREY,LineWidth/2,wx.SHORT_DASH)
    self.SetPen(LineColor,LineStyle,LineWidth)
    self.CalcBoundingBox()
    
  def CalcLengthPoints(self):
    c0 = self.Object1.GetConnectPoint()
    c1 = self.Object2.GetConnectPoint()
    delta = c1-c0  #vector from ConnectPoint on Object1 to connectPoint on Object2
    length = np.linalg.norm(delta)
    if (length>0) & (self.Lengths[0]>0) & (self.Lengths[1]>0):
      # the ratio of the distance between points and the measured length from another source
      # length divided by 2 since each node can move half as much to reach required distance
      ratios = (self.Lengths/length-1.0)*0.5+1.0 # 2-element array due to bidirectional length measurements from some measurement sources
      # find the position of a point beyond the endpoint of this vector based on the length values
      p0 = c1-ratios[1]*delta  # take the reverse length ratio and push a new startpoint out that distance along the reverse direction vector
      p1 = c0+ratios[0]*delta # take the forward length ratio and push a new endpoint out that distance along the forward direction vector
      #2x4 matrix with each row hold the pairs of points for the endpoints of a line the radio positions at each end of a connection to the extrapolated positions based on measured distance between them
      self.LengthPoints = (np.row_stack( (np.concatenate((WorldToPixel(c0),WorldToPixel(p0)),axis=1) ,np.concatenate((WorldToPixel(c1),WorldToPixel(p1)),axis=1)) ))
    else:
      self.LengthPoints = (np.row_stack( (np.concatenate((WorldToPixel(c0),WorldToPixel(c0)),axis=1) ,np.concatenate((WorldToPixel(c1),WorldToPixel(c1)),axis=1)) )) # nowhere lines

  def CalcBoundingBox(self):
    log.debug("self.LengthPoints = "+str(self.LengthPoints))
    if self.LengthPoints:
      self.BoundingBox = BBox.fromPoints(LengthPoints) # contains 4 points, the locations of the radios and the locations where they are extrapolated to be based on measured signal strength (range)
      
      log.debug("list of points:"+str((self.Object1.GetConnectPoint(),
                                            self.Object2.GetConnectPoint(),
                                            self.LengthPoints[0],
                                            self.LengthPoints[1]) ) )
    else:
      self.BoundingBox = BBox.fromPoints((self.Object1.GetConnectPoint(),
                                           self.Object2.GetConnectPoint()) ) # a tuply containing 2 numpy 2-element arrays
    if self._Canvas:
      self._Canvas.BoundingBoxDirty = True

  def _Draw(self, dc , WorldToPixel, ScaleWorldToPixel, HTdc=None):
    ConnectorLine._Draw(self, dc , WorldToPixel, ScaleWorldToPixel, HTdc=None)
    #actHL: don't reconstruct this, store it in ConnectorLine.Points 
    #the position vectors for each end of the connector 
    c0 = self.Object1.GetConnectPoint()
    c1 = self.Object2.GetConnectPoint()
    #vector from start point to end point
    delta = c1-c0
    #log.debug(str(delta))
    length = np.linalg.norm(delta)
    if (length>0) & (self.Lengths[0]>0) & (self.Lengths[1]>0):
      # the ratio of the distance between points and the measured length from another source
      # length divided by 2 since each node can move half as much to reach required distance
      ratios = (self.Lengths/length-1.0)*0.5+1.0 # 2-element array due to bidirectional length measurements from some measurement sources
      # find the position of a point beyond the endpoint of this vector based on the length values
      p1 = c0+ratios[0]*delta # take the forward length ratio and push a new endpoint out that distance along the forward direction vector
      # find the position of a point beyond the endpoint of this vector based on the length values
      p0 = c1-ratios[1]*delta  # take the reverse length ratio and push a new startpoint out that distance along the reverse direction vector
      #log.debug(str(p0))
      #2x4 matrix with pairs of vectors from the nodes at each end of a connection to the extrapolated position based on measured distance between them
      self.LengthPoints = (np.row_stack( (np.concatenate((WorldToPixel(c0),WorldToPixel(p0)),axis=1) ,np.concatenate((WorldToPixel(c1),WorldToPixel(p1)),axis=1)) ))
      #log.debug(str(LengthPoints))
      #if ScaleWorldToPixel:
      #  LengthPoints = WorldToPixel(LengthPoints)
      dc.SetPen(self.LengthPen)
      dc.DrawLineList(self.LengthPoints)

  def SetLengths(self,lengths=(0,0)):
    self.Lengths = lengths
    #actHL: should trigger a redraw here, but I don't have a dc handle, etc

# so this isn't actually a panel, it's a window with 2 panels, one for toolbar other for drawing!
class RadioPanel(NC.NavCanvas):
                  # parent=parent,id = wx.ID_ANY,size = wx.DefaultSize
  def __init__(self, parent, id = wx.ID_ANY, size = wx.DefaultSize, style=wx.SUNKEN_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE): 
    NC.NavCanvas.__init__(self, parent, id=id, size=size, ProjectionFun=None,Debug=0,BackgroundColor = "WHITE")
    #self.Canvas = NC.NavCanvas
    self.RadioObjectArray = []
    self.EdgeObjectArray = []
    self.PixelPerMeter = 100
    self.buffer = None
    self.selection = [] # an array to hold all the objects currently selected by the user using a rubber band, and/or shift-clicking, and/or ctrl-clicking
    log.info("Init RadioPanel")
    # Add the Canvas
    #self.Canvas = NC.NavCanvas(self, parent=parent, id=id, size=size,ProjectionFun=None,Debug=0,BackgroundColor = "WHITE",**kwargs).Canvas
    # initialize a double-buffer memory block
    #self._initBuffer()
    self.SetThemeEnabled(True)
    tb = self.ToolBar
    OptimizeButton = wx.Button(tb, label="Optimize Positions")
    tb.AddSeparator()
    tb.AddControl(OptimizeButton)
    OptimizeButton.Bind(wx.EVT_BUTTON, self.OnOptimizePositions)
    PauseButton = wx.Button(tb, label="Pause Packets")
    tb.AddSeparator()
    tb.AddControl(PauseButton)
    PauseButton.Bind(wx.EVT_BUTTON, self.OnPausePackets)
    tb.Realize()
    #self.Bind(wx.EVT_PAINT, self.OnPaint)

    #self.Bind(FC.EVT_MOTION, self.OnMove )  # shouldn't spawn double OnMove events for panel adn frame
    self.Bind(FC.EVT_LEFT_UP, self.OnLeftUp ) 
    self.N = 0
    #self.InitializeRadios()
    #self.NewEdges()
    self.GhostPoints = None
    self.MovingGhostPoints = None
    self.Moving = False
    self.AutoMoving = False
    # if this panel is derived from a NavCanvas object then the self.Canvas local variable won't be available until __init__ is done
    
  # not normally called  
  def InitializeRadios(self):
    self.RadioObjectArray=[] #.clear()
    #self.Canvas.clear()
    #self.Canvas.AddObject(FC.ScaledBitmap(self.BGBitmap,XY=(0,0),Height=1,Position = 'cc',InForeground = True))
    for i in range(self.N):
      a = i*np.pi*2/self.N
      r = RadioObject( str(i), (np.cos(a),np.sin(a)), WH=(.25,.25), FillColor="Green", LineStyle="Solid", LineWidth=3)
      log.debug("Outside RadioObject instantiation")
      self.RadioObjectArray.append(r)
      log.debug("After RadioObjectArray.append(r)")
      self.Canvas.AddObject(self.RadioObjectArray[i])
      log.debug("After Canvas.AddObject")
      self.RadioObjectArray[i].Bind(FC.EVT_FC_LEFT_DOWN, self.ObjectHit) 
      log.debug("After self.RadioObjectArray[i].Bind...")
      
  def _initBuffer(self):
    """Initialize the bitmap used for buffering the display."""
    size = self.GetSize()
    self.buffer = wx.EmptyBitmap(max(1,size.width),max(1,size.height))
    dc = wx.BufferedDC(None, self.buffer)
    dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
    dc.Clear()
    #dc.DrawBitmap(Resources.get__images_backgroundHomeLayoutBitmap(),x=0,y=0,useMask = True) # useMask means to use transparency mask if it exists in the bitmap
    self.drawContents(dc) # in case objectg have been loaded from a file
    del dc  # commits all drawing to the buffer
    #self.saved_offset = self.CalcUnscrolledPosition(0,0)
    self._reInitBuffer = False
      
  def OnPaint(self,event):
    pass
    dc = wx.PaintDC(self)
    #dc = wx.BufferedDC(self, self.buffer) # wx.PaintDC(self)
    dc.BeginDrawing()
    # Get the update rects and subtract off the part that self.buffer has correct already
    region = self.GetUpdateRegion()
    panelRect = self.GetClientRect()
    #offset = list(self.CalcUnscrolledPosition(0,0))
    #offset[0] -= self.saved_offset[0]
    #offset[1] -= self.saved_offset[1]
    region.Subtract(0,0,panelRect.Width, panelRect.Height)   
    # Now iterate over the remaining region rects and fill in with a pattern
    rgn_iter = wx.RegionIterator(region)

    #dc.DrawBitmap(Resources.get__images_backgroundHomeLayoutBitmap(),x=-1,y=-10,useMask = False) # useMask means to use transparency mask if it exists in the bitmap
    #self.img = self.Canvas.AddScaledBitmap( self.BGImage,(0,0),Height=self.BGImage.GetHeight(),Position = 'tl')
    """
    if rgn_iter.HaveRects():
      self.setBackgroundMissingFillStyle(dc)
      offset = self.drawPanel.CalcUnscrolledPosition(0,0)
    while rgn_iter:
      r = rgn_iter.GetRect()
      if r.Size != self.drawPanel.ClientSize:
          dc.DrawRectangleRect(r)
      rgn_iter.Next()
    """
    dc.EndDrawing()
 
  def drawContents(self, dc):
    print self.RadioObjectArray
    """Draws of all objects using the specified dc"""
    # PrepareDC sets the device origin according to current scrolling
    self.PrepareDC(dc) # actHL: not necessary with NavCanvas which doesn't have a scroll bar?
    #   gdc = self.wrapDC(dc) # so a high resolution or low resolution device context is created each time a drawContents is called
    # First pass draws objects
    ordered_selection = []
    for obj in self.RadioObjectArray[::-1]: #actHL: can we unify the RadioObjectArray and EdgeobjectArray without complicating the AddRadio and AddEdge functions?
      if obj in self.selection:
        obj.draw(dc, True)
        ordered_selection.append(obj)
      else:
        obj.draw(dc, False)
    for obj in self.EdgeObjectArray[::-1]:
      if obj in self.selection:
        obj.draw(dc, True)
        ordered_selection.append(obj)
      else:
        obj.draw(dc, False)

    # First pass draws the object
    #if self.curTool is not None:
    #  self.curTool.draw(dc)

    # Second pass draws the selection handles so they're always on top
    for obj in ordered_selection:
      obj.drawHandles(dc)

  def NewEdges(self):
    k=0;
    for i in range(self.N):
      for j in range(i+1,self.N):
        self.EdgeObjectArray.append(ExtendedConnectorLine(self.RadioObjectArray[i],self.RadioObjectArray[j], Lengths=distances, LineWidth=3, LineColor="Red"))
        self.Canvas.AddObject(self.EdgeObjectArray[k])
        k += 1
    
  def ObjectHit(self, object): # mouse left button down event near an object 
    if not self.Moving:
      self.Moving = True
      self.StartPoint = object.HitCoordsPixel
      # is this a bounding rectangle for redraws or the dotted line rectange for ghosting moving objects
      # create a rectangle of 4 points that bounds each step of motion of the object
      self.GhostPoints = self.Canvas.WorldToPixel(object.GetOutlinePoints())
      # this will hold the endpoint in a step of motion once it starts to move
      self.MovingGhostPoints = None
      self.MovingObject = object
  
  def OnOptimizePositions(self, event):
    pub.sendMessage("OPTIMIZE")  
    
  def OnPausePackets(self, event):
    pub.sendMessage("PAUSE")  
    
  def OnMove(self, event): # mouse moving event
    """Updates the status bar with coordinates & moves object previously clicked on"""
    #self.SetStatusText("%.4f, %.4f"%tuple(event.Coords)) # can't mess with the status bar unless this object is a Frame
    #log.debug("self.GhostPoints="+str(self.GhostPoints))
    if self.Moving and self.GhostPoints is not None:
      dxy = event.GetPosition() - self.StartPoint
      # Draw the Moving Object:
      dc = wx.ClientDC(self.Canvas)
      dc.SetPen(wx.Pen('GRAY', 2, wx.SHORT_DASH))
      dc.SetBrush(wx.TRANSPARENT_BRUSH)
      dc.SetLogicalFunction(wx.XOR)
      if self.MovingGhostPoints is not None: 
        dc.DrawPolygon(self.MovingGhostPoints) #why is the ghost drawn twice?
      # so this is where the object is going to end up to move the outline to there
      self.MovingGhostPoints = self.GhostPoints + dxy
      dc.DrawPolygon(self.MovingGhostPoints) # uses the dotted line pen and brush set up above to draw a ghost object outline/rectangle

  def AddImage(self,img):
    self.Canvas.AddScaledBitmap( img, (-0.25,0), Height=img.GetHeight()/self.PixelPerMeter, Position = 'cc', InForeground=False )

  def AddRadio(self,position=None):
    if (position==None or (len(position)!=2 and len(position)!=3)):
      position = np.random.rand(2,1)
    log.debug(str(type(self))+"RadioPanel.AddRadio with position "+str(position)+" and "+str(self.N)+" existing radios.")
    r = RadioObject( str(self.N+1), (position[0],position[1]), WH=(.25,.25), FillColor="Green", LineStyle="Solid", LineWidth=2, InForeground=True)
    self.RadioObjectArray.append(r)
    #self.Canvas.clear()
    # self.N is still # of RadioObjects in RadioObjectArray - 1, & this won't loop until self.N > 0
    # RadioObjectArray has self.N + 1 elements, so we can make edges from all the others to this new object by...
    for i in range(self.N):
      self.EdgeObjectArray.append(ExtendedConnectorLine(self.RadioObjectArray[i],self.RadioObjectArray[self.N], Lengths=(0,0), LineWidth=2, LineColor="Red", InForeground=False))
      self.Canvas.AddObject(self.EdgeObjectArray[-1])
    # Now we can add the radio object to the canvas so it will appear in front of the edges
    self.Canvas.AddObject(self.RadioObjectArray[-1])
    log.debug("Finished adding the radio object to the Canvas")
    #dbgHL: commented to stop Fatal IO error 11 (X server)\
    #dbgHL: tried replacing with r. rather than self.RadioObjectArray[-1] without any change in behavior
    #dbgHL: what about using Canvas.GetObject() as the binding object?
    try:
      self.RadioObjectArray[-1].Bind(FC.EVT_FC_LEFT_DOWN, self.ObjectHit) # interesting way to detect hits, better it seems than the standard wx/demos technique of redrawing bitmap in background and checking to see if pixel is black
    except:
      log.debug("Bind error")
      raise RadioFrameError("Unable to Bind RadioObject FC.EVT_FC_LEFT_DOWN event to ObjectHit function")
    log.debug("Finished binding the RadioObject to an ObjectHit event")
    self.N += 1
    #self.Canvas.ZoomToBB()
    self.Canvas.Draw(True) # HL: unnecessary?

  def RemoveRadio(self,i=None):
    log.debug(str(type(self))+"RadioPanel.RemoveRadio with index "+str(i)+".")
    if not i:
      i = self.N-1 # if not object selected then delete the last one added (LIFO buffer)
    if i>=0 and self.N>0:
      ro = self.RadioObjectArray[i]
      log.debug(str(type(self))+"RadioPanel.RemoveRadio with "+str(len(self.EdgeObjectArray))+" edges to sort through.")
      deletionList = []
      for j,eo in enumerate(self.EdgeObjectArray):
        # look for any connector line (ExtendedConnectorLine) objects that include this Radio as one of it's endpoints
        # actHL: alternatively you can just delete the ones that you know are connected based on the order of the array creation
        # e.g. EdgeObjectArray[k-i+1:k] where k=(sum(range(i))+i-1)
        if eo.Object1==ro or eo.Object2==ro:
          self.Canvas.RemoveObject(eo) # delete that ConnectorLine object from the canvas
          deletionList.append(j)
      deletionList.reverse() # to avoid deleting one in front of another and messing up the indexes to the remainder
      for k in deletionList:  
        del self.EdgeObjectArray[k] # delete that ConnectorLine from the internal array of objects
      self.Canvas.RemoveObject(ro)
      del self.RadioObjectArray[i]   # See Also: built-in mutable sequence type operations s[i] = [] or s[i:j] = [] or s.pop(i)
      self.N = np.max(self.N-1,0) #
      self.Canvas.ZoomToBB()
      self.Canvas.Draw(True) # unnecessary?

  def SetPositions(self,p):
    log.debug(str(type(self))+"RadioPanel.SetPositions "+str(np.shape(p))+", with values:\n"+str(p)+" and "+str(self.N)+" existing radios and "+str(np.size(p,0))+" radios in the new positions array.")
    for i in range(np.size(p,0)):
      if i<self.N:
        self.RadioObjectArray[i].Set2DPosition((p[i][0],p[i][1]))
      else:
        self.AddRadio((p[i][0],p[i][1]))       
    #self.CalcBoundingBox()
    self.Canvas.BoundingBoxDirty = True
    #self.Canvas.ZoomToBB()
    self.Canvas.Draw(True) # unnecessary?

  def GetPositions(self,i=None):
    log.debug(str(type(self))+".GetPositions("+str(i)+")")
    self.positions = np.zeros((self.N,3))
    if i==None:
      for j in range(self.N):
        self.positions[j][0:2]=self.RadioObjectArray[j].GetPosition()[0:2]
        #self.positions[j][0:2]=x[0:2]       
        log.debug(str(type(self))+" position["+str(j)+"]="+str(self.positions[j]))
    log.debug(str(type(self))+" positions="+str(self.positions))
    return self.positions # will this get passed by reference or value?
    
  def SetNumRadios(self,newN):
    log.debug("Changing number of radios from "+str(s.N)+" to "+str(N)+".")
    s.N = N
    self.InitializeRadios(newN)

  def SetDistances(self,d):
    log.debug(str(type(self))+".SetDistances argument size is "+str(np.shape(d)))
    k=0;
    for i in range(self.N):
      for j in range(i+1,self.N):
        self.EdgeObjectArray[k].Lengths = (d[i][j],d[j][i])
        k += 1
    #self.CalcBoundingBox()
    self.Canvas.BoundingBoxDirty = True
    #self.Canvas.ZoomToBB()
    self.Canvas.Draw(True) # unnecessary?

  def OnLeftUp(self, event): # left mouse button released
    if self.Moving and self.GhostPoints is not None:
      if self.MovingGhostPoints is not None: # only do the move if a shadow object has been created (user can let go without dragging and nothing happens)
        dxy = event.GetPosition() - self.StartPoint
        dxy = self.Canvas.ScalePixelToWorld(dxy)
        self.MovingObject.Move(dxy)
        pub.sendMessage("POSITION")
      self.Canvas.Draw(True)
      self.Moving = False # let other tasks do some moving
      self.GhostPoints = None # let the mouse dragging events resume moving the object
      self.MovingGhostPoints = None # let the mouse dragging events resume moving the object

class RadioFrame(wx.Frame):
  """Frame/Window for holding the RadioPanel Object"""
  def __init__(self, parent=None, title="Radio Location Display Screen", pos= wx.DefaultPosition, size=(680,500), *args, **kwargs):
    wx.Frame.__init__(self, parent, title="Radio Location Display Screen", pos= wx.DefaultPosition, size=(680,500), *args, **kwargs)
    #    def __init__(self, parent=None, id=wx.ID_ANY, title="Radio Location Display Screen", pos=wx.DefaultPosition, size=(680,500),  **kwargs):
    #wx.Frame.__init__(self, parent, id=id, title=title, pos=pos, size=size,**kwargs) #actHL: need to see whether * and ** are required in front of arguments passed up to parent classes
    self.CreateStatusBar()
    self.panel1 = RadioPanel(self, style=wx.SUNKEN_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE) # can't pass args or kwargs through because they are for the Frame and not the Panel (i.e. title won't make it through)
    self.panel1.Bind(FC.EVT_MOTION, self.OnMove ) 
    self.Bind(wx.EVT_CLOSE, self.OnClose)
    self.BGImage = Resources.get__images_backgroundHomeLayoutImage() 
    self.panel1.AddImage(self.BGImage) # have to add the background image first so that radios show on top
    self.done = False
    self.Show() # must show the entire frame before zooming the Canvas within the frame
    self.panel1.Canvas.ZoomToBB()

  def OnClose(self, event):
    pub.sendMessage("DONE")
    self.done = True
    time.sleep(0.1)
    self.Destroy()

  #actHL: If not instantiating more than one panel within the same frame, then obviously need to do inheritance rather than inclusion from wx.Panel object RadioPanel
  def OnMove(self, event): # mouse moving event at frame level
    """Updates the status bar with coordinates & moves object previously clicked on"""
    self.SetStatusText("%.4f, %.4f"%tuple(event.Coords)) # can't mess with the status bar unless this object is a Frame
    self.panel1.OnMove(event)

  def GetPositions(self,i=None):
    log.debug("RadioFrame.GetPositions("+str(i)+") called.")
    return(self.panel1.GetPositions(i))

  def SetPositions(self,p):
    log.debug("RadioFrame.SetPositions("+str(p)+") called.")
    self.panel1.SetPositions(p)
    
  def Set(self,p):
    log.debug("RadioFrame.Set("+str(p)+") called with argument type '"+str(type(p))+"'.")
    #self.panel1.SetPositions(p)

  def AddRadio(self,p=None):
    log.debug("RadioFrame.AddRadio("+str(p)+") called.")
    self.panel1.AddRadio(p)

  def RemoveRadio(self,p=None):
    log.debug("RadioFrame.RemoveRadio("+str(p)+") called.")
    self.panel1.RemoveRadio(p)

  def SetDistances(self,p):
    log.debug("RadioFrame.SetDistances("+str(p)+") called.")
    self.panel1.SetDistances(p)

  def SetNumRadios(self,newN):
    log.debug("RadioFrame.SetNumRadios("+str(newN)+") called.")
    self.panel1.SetNumRadios(newN)

  def SetDistances(self,newDistances):
    log.debug("RadioFrame.SetDistances("+str(newDistances)+") called.")
    self.panel1.SetDistances(newDistances)

  def OnChooseQuality(self, event):
    if event.GetId() == menu_DC: #user chose low quality
      self.wrapDC = lambda dc: dc
    else: # lambda is like an inline, runtime substitution, so whenever dc object is called, wx.GCDC object is created based on dc and used instead
      self.wrapDC = lambda dc: wx.GCDC(dc) #user chose high quality
    self._adjustMenus()
    self.requestRedraw()
    
  def doShowAbout(self, event):
      """ Respond to the "AboutChildSafetyMonitor" menu command."""
      dialog = wx.Dialog(self, -1, "About SafetyMonitor") # ,
                        #style=wx.DIALOG_MODAL | wx.STAY_ON_TOP)
      dialog.SetBackgroundColour(wx.WHITE)

      panel = wx.Panel(dialog, -1)
      panel.SetBackgroundColour(wx.WHITE)

      panelSizer = wx.BoxSizer(wx.VERTICAL)

      boldFont = wx.Font(panel.GetFont().GetPointSize(),
                        panel.GetFont().GetFamily(),
                        wx.NORMAL, wx.BOLD)

      logo = wx.StaticBitmap(panel, -1, wx.Bitmap("images/logo.bmp",
                                                wx.BITMAP_TYPE_BMP))

      lab1 = wx.StaticText(panel, -1, "Child Safety Monitor")
      lab1.SetFont(wx.Font(36, boldFont.GetFamily(), wx.ITALIC, wx.BOLD))
      lab1.SetSize(lab1.GetBestSize())

      imageSizer = wx.BoxSizer(wx.HORIZONTAL)
      imageSizer.Add(logo, 0, wx.ALL | wx.ALIGN_CENTRE_VERTICAL, 5)
      imageSizer.Add(lab1, 0, wx.ALL | wx.ALIGN_CENTRE_VERTICAL, 5)

      lab2 = wx.StaticText(panel, -1, "An applicaiton for monitoring the locaiton and saftey of anything or anyone carrying a Transceive Technology product.")
      lab2b = wx.StaticText(panel, -1, "(C) 2010, All Rights Reserved.")
      lab2.SetFont(boldFont)
      lab2.SetSize(lab2.GetBestSize())

      lab3 = wx.StaticText(panel, -1, "Child Safety Monitor is proprietary software by Transceive Technology")
      lab4 = wx.StaticText(panel, -1, "However, it is adapted from free source code supplied with wxPython,\nif you want to tinker with something similar.")
      lab3.SetFont(boldFont)
      lab3.SetSize(lab3.GetBestSize())

      lab5 = wx.StaticText(panel, -1,"Author: Hobson Lane (hobson@transceivetechnology.com),\nbased on free software by ErikWestra (ewestra@wave.co.nz)\nand Bill Baxter (wbaxter@gmail.com)")

      lab5.SetFont(boldFont)
      lab5.SetSize(lab5.GetBestSize())

      btnOK = wx.Button(panel, wx.ID_OK, "OK")

      panelSizer.Add(imageSizer, 0, wx.ALIGN_CENTRE)
      panelSizer.Add((10, 10)) # Spacer.
      panelSizer.Add(lab2, 0, wx.ALIGN_CENTRE)
      panelSizer.Add(lab2b, 0, wx.ALIGN_CENTRE)
      panelSizer.Add((10, 10)) # Spacer.
      panelSizer.Add(lab3, 0, wx.ALIGN_CENTRE)
      panelSizer.Add(lab4, 0, wx.ALIGN_CENTRE)
      panelSizer.Add((10, 10)) # Spacer.
      panelSizer.Add(lab5, 0, wx.ALIGN_CENTRE)
      panelSizer.Add((10, 10)) # Spacer.
      panelSizer.Add(btnOK, 0, wx.ALL | wx.ALIGN_CENTRE, 5)

      panel.SetAutoLayout(True)
      panel.SetSizer(panelSizer)
      panelSizer.Fit(panel)

      topSizer = wx.BoxSizer(wx.HORIZONTAL)
      topSizer.Add(panel, 0, wx.ALL, 10)

      dialog.SetAutoLayout(True)
      dialog.SetSizer(topSizer)
      topSizer.Fit(dialog)

      dialog.Centre()

      btn = dialog.ShowModal()
      dialog.Destroy()

    
if __name__ == "__main__":
  app = wx.App(False) 
  # parent=None, id=wx.ID_ANY, title="Radio Location Display Screen", pos=wx.DefaultPosition, size=(680,500),
  rf = RadioFrame(None)
  N=10
  for i in range(N):
    rf.AddRadio()
  for r in rf.panel1.RadioObjectArray:
    r.Move(2*np.random.rand(2))
  rf.panel1.RadioObjectArray[-1].Move((3,5))  
  d = np.random.rand(N,N)
  rf.panel1.SetDistances(4*d*d.transpose())
  rf.panel1.Canvas.ZoomToBB()

  log.debug("BB="+str(rf.panel1.RadioObjectArray[2].BoundingBox))
  print("done")
  args = sys.argv[1:]   
  app.MainLoop()
