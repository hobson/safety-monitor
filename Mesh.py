#!/usr/bin/env python
from Packet import Packet
import numpy as np
import pickle
import optimize as optim
from log import log
from wx.lib.pubsub import Publisher as pub
import Edge

# A global place to store the matrix of measured distances between radios for comparison 
# to the distances computed from the estimated locations of the radios, allowing optimization 
# (minimization) of the error between these two matrices of NxN values (diagonals should hold only bias information)
global global_distances
global_distances = np.zeros((0,0),dtype=float)
#global_distances = DistanceMatrix((0,0),dtype=float) 

# this probably doesn't need to be a global functions, but this certainly works
# the optimizer expects to be able to send a single vector argument rather than including a "self" object along with it
def Positions2Distances(x):
  """Measure of the error in the radio position solution for use in optimizing solvers."""
  Ndim = 2 # 2D or 3D position data vectors to do distance math on
  Nlen = len(x)
  if (Nlen % Ndim) != 0:
    print "Error in CostFun(): number of elements ("+str(Nlen)+"in input array is not divisible by the length ("+str(Ndim)+") of the position vectors."
    return -1
  Npos = Nlen/Ndim
  # passed array will be 1-D from optimization function so have to deal with it
  x1 = np.array(x, dtype=float, copy=True, order='C', subok=False, ndmin=1) # 1-D array containing positions
  x2 = np.reshape(x1, (Nlen/Ndim, Ndim), order='C') # 2-D array containing posiiton vectors
  d1 = np.zeros((0)) #HL: only way I know how ot iterate through elements of a matrix without two indexes is to append an array and reshape
  for p1 in x2: # for each position vector in 2-D matrix
    for p2 in x2: # for each position vector in 2-D matrix again
      d1=np.append( d1, np.linalg.norm(p2-p1) ) # because this isn't a normal 2-D list have to use np.append syntax
  return ( np.reshape(d1, (Npos,Npos)) )

# this probably doesn't need to be a global functions, but this brute force method certainly works
# optimizer expects to be able to send a single vector argument rather than including a "self" object along with it
def CostFun(x):
  """Measure of the error in the radio position solution for use in optimizing solvers."""
  return np.sqrt(np.sum( ( Positions2Distances(x) - global_distances )**2 ) )
 
class Mesh(object): # don't put empty parentheses here or you will regret it!
  def __str__(self):
    if self and self.N!=None:
      text  = "Addresses = "+str(self.addresses)+"\nPositions = "+str(self.positions)+"\nDistances = "+str(self.distances)+"\nDistancesFromPositions = "+str(self.p2d)+"\n"
    else:
      text = "Invalid object of type "+str(type(self))
    return text

  """Database and optimizer of distance and position data for network of radio nodes."""
  def __init__(self,objects=[]):
    self.N = 0 # unfortunately can't use len(objects) because objects passed can include 0,1,2,3 or more new nodes for the mesh to keep up with
    log.debug("Mesh__init__ with zero radios")
    self.MAX_NODES = 10 # 32 would be a 32x32 distances matrix with 1000 elements, probably the limit of what'self practical for this brute force record keeping method
    self.addresses = np.empty((self.N),dtype=int) # Nx1 empty 1-D python array for network addresses of the radios/nodes
    self.positions = np.empty((self.N, 3),dtype=float) # Nx3 empy numpy array for 3-D radio node positions
    self.p2d = np.empty((self.N, self.N),dtype=float)# empty NxN numpy matrix of distances implied by the positions
    self.distances = np.empty((self.N, self.N)) # empty NxN numpy array for measured distances between nodes
    #self.distances = DistanceMatrix((self.N, self.N),dtype=float) # empty NxN numpy array for measured distances between nodes
    self.alpha = .8 # portion of the previous range information to retain when adding in new range info, smaller = higher bandwidth and faster/noisier/jumpier tracking
    self.beta = 1-self.alpha # portion of new range info to add in
    self.e = None
    #print "New Mesh"
    for o in objects:
      Add(o) # type checking and sorting within Add() attribute function
    log.debug("Mesh__init__ completed with "+str(self.N)+" radios")
  
  # could be combined with AddPacket() by checking the type of the input, e
  def AddEdge(self,e):
    """If the supplied edge object contains new radio address(es), expand the list of addresses, radio positons, & radio-to-radio distances."""
    log.debug("AddEdge received an argument of type "+str(type(e))+".")
    if (type(e)!=Edge.Edge) or (e.srcAdd==e.dstAdd): # this is not the src and dst addresses of the packet, but the edge or radio link measured by the meta data within the payload of the packet
      return
    if ((e.srcAdd not in self.addresses) and (self.N<self.MAX_NODES)):
      log.debug("Growing the address list to append source address "+str(e.srcAdd)+".")
      self.addresses=np.append(self.addresses,e.srcAdd)
    if ((e.dstAdd not in self.addresses) and (self.N<self.MAX_NODES)):    
      log.debug("Growing the address list to append destination address "+str(e.dstAdd)+".")
      self.addresses=np.append(self.addresses,e.dstAdd)
    deltaN = len(self.addresses) - self.N 
    log.debug("The change in number of nodes is "+str(deltaN)+".")
    if deltaN>0:
      if self.N+deltaN<=self.MAX_NODES: # 1 or 2 new radio nodes have been added, and we have room for them
        log.debug("There's still 'room in the Inn'")
        #WARNING: np.resize doesn't preserve the original matrix data! It doesn't resort the data in the underlying linear array, so a 2-D matrix width change means the 2nd row will start at a new location in the underlying data
        self.positions = np.append(self.positions,[[0.0, 0.0, 0.0]]*deltaN,0)
        #WARNING: Be careful with numpy.append(), it can behave unexpectedly if you increase the length of the 2nd dimension (width of a matrix)
        self.distances = np.append(self.distances,[[0.0]*self.N   ]*deltaN, 0) #add 1 or 2 rows for the 1 or 2 new radio(self) at the source of the link
        self.N += deltaN # going to use the new size in the next line, so go ahead and compute it
        self.distances = np.append(self.distances,[[0.0]*deltaN]*self.N   , 1) #add 1 or 2 columns for the 1 or 2 new radio(self) at the destination of the link
        log.debug("New node supplied so growing the distance matrix to "+str(self.N)+"x"+str(self.N)+" to accomidate it.")
        self.InitializePositions()
#            pub.sendMessage("POSITIONS", self.positions)
#            pub.sendMessage("DISTANCES", self.distances)
        try:
          i,j = self.addresses.tolist().index(e.srcAdd),self.addresses.tolist().index(e.dstAdd)
        except:
          log.error("When new radios were added, couldn't find the addresses "+str(e.srcAdd)+" and "+str(e.dstAdd)+" in "+str(self.addresses))
        try:
          self.distances[i][j] = e.distance # only 1-way distance is available, and it'self the first one, so don't alpha-beta filter it
        except:
          log.error("Unable to expand the connections matrix. Unable to find an approriate src or dst address in the list of addresses")
          log.error("  Distance from address["+str(self.addresses.tolist().index(e.srcAdd))+"]="+str(e.srcAdd)+" to address["+str(self.addresses.tolist().index(e.dstAdd))+"]="+str(e.dstAdd)+" within:\n"+str(self.distances))
      else: # if self.N+deltaN<=self.MAX_NODES else
        log.error("Mesh object has exceeded the maximum number of radio nodes allowed. Unable to incorporate radio link information from"+str(e.srcAdd)+"to"+str(e.dstAdd)+"into the position solution.")
    else:  # if deltaN>0 else (so we're just adding some distance info and no new addresses or radios
      try:
        i,j = self.addresses.tolist().index(e.srcAdd),self.addresses.tolist().index(e.dstAdd)
        self.distances[i][j] = self.alpha*e.distance + self.beta*self.distances[i][j] # only 1-way distance is available in a single edge object
      except ValueError:
        log.error("When updating distances, couldn't find the addresses "+str(e.srcAdd)+" and "+str(e.dstAdd)+" in "+str(self.addresses))
      
  def AddPacket(self,p):
    """Processes a ZigBee packet adding information from it to a list of edge objects holding key parameters like source and destination address."""
    log.debug("Mesh is adding an "+str(type(p))+" object")
    #actHL: should sort and average corresponding values over time with an exponential filter"""
    if type(p)==str:
      p = Packet(p) # convert a string (line of text from a log file) into a processed packet of data
    if (type(p)==Packet and p.t>0): # make sure time is valid so that we know it's probably a valid packet
      for n in p.neighbors:
        log.debug("Processing a Neighbor: " + str(n[0]) + " " + str(n[1]) + " "+ str(n[2]))
        if n[1]>0 and n[2]>0: # depends on nonzero RSSI and LQI
          self.e = Edge.Edge([n[0],p.srcAdd,n[1],n[2]]) # packet source address is edge destination address
          log.debug("Mesh is incorporation data from an "+str(type(self.e))+"="+str(self.e))
          self.AddEdge(self.e) 
          
  def Add(self,o):
    if type(o)==str:
      self.AddPacket(Packet(o))
    elif type(o)==Packet:
      self.AddPacket(o)
    elif type(o)==Edge.Edge:
      self.AddEdge(o)
    else:
      log.error("Mesh.Add() called with an unkown argument object type (not a Packet, Edge or str)")

  #actHL: just a MVC testing placeholder, don't do it this way!!!
  def setNumRadios(self,newNumRadios):
    self.InitializePositions(newNumRadios) #this seems overkill
    self.InitializeDistances()

  #actHL: just a MVC testing placeholder, don't do it this way!!!
  def addRadio(self,newAddress=None):
    if newAddress==None:
      if len(self.addresses)>0:
        newAddress=self.addresses[-1]+1
      else:
        newAddress=0
    self.addresses=np.append(self.addresses,newAddress) # if newAddress is a list or array of addresses then multiple radios are added
    self.InitializePositions(len(self.addresses))
    self.InitializeDistances()
    log.debug("Number of radios in Mesh is now "+str(self.N)+".")

  #actHL: just a MVC testing placeholder, don't do it this way!!!
  #actHL: need to search for the right address and delete it!!!
  def removeRadio(self,oldAddress=None):
    if oldAddress==None:
      self.InitializePositions(np.max((self.N-1,0)))
      self.addresses=np.resize(self.addresses,(self.N))
      self.InitializeDistances()

  def Positions2Vto3M(self,p):
    """Unpacks a 2Nx1 vector into an Nx3 matrix, inserting a zero for the 3rd element in each vector (z-axis)."""
    x3 = []
    p2 = np.reshape(p,(np.size(p),))
    n = np.size(p2)
    if n % 2:
      print "Error in Positions2Vto3M, input vector is length",n,"which is not divisible by 2."
      return None
    n = n/2
    #print p2
    i = 0
    for x1 in p2:
      #print i,"=",x1
      x3.append(x1) # because this is a regular built-in list object, append() works
      if i % 2:  
        #print "filler"
        x3.append(0.0)
      i = i+1
    p3 = np.reshape(x3,(n,3))
    return p3

  def Positions3Mto2V(self,p):
    """Packs an Nx3 matrix into a 2Nx1 vector, eliminating the 3rd element in each vector (z-axis)."""
    x2 = []
    p3 = np.reshape(p,(np.size(p),))
    i = 0
    for x1 in p3:
      if (i+1) % 3:  
        x2.append(x1)
      i = i+1
    return x2

  def Positions2Distances(self):
    """Compute the theoretical distange values for every possible 2-way radio link and return the values in an NxN matrix."""
    # needs to have 2-way bias/gain values to make this redundant 2-way computation redundancy worthwhile
    #print self.N
    #print self.positions
    self.p2d = np.zeros((self.N,self.N))
    i,j = 0,0
    # lots of duplication here that can be eliminated for efficiency
    for p1 in self.positions:
      for p2 in self.positions:
        #print i,",",j
        self.p2d[i][j] = np.linalg.norm(p2-p1)  
        j = j+1
      i,j = i+1,0
    return self.p2d
    
  def CirclePositions(self,numpos=None,radius=None,numdim=None):
    if not (numpos):
      numpos = self.N
    if not (numdim):
      numdim = 3
    if not (radius):
      radius = 1.0
    # this fails to create unique arrays, just references within the array to itself, so must use numpy
    #pos = [[0.0]*numdim]*numpos # avoid using numpy so function is portable 
    pos = np.zeros((numpos,numdim))
    for i in range(numpos): # reset the positions of all radio nodes
      a = i*np.pi*2/numpos # angle around a circle for distributing the nodes
      #print "angle=",a
      pos[i][0]=radius*np.cos(a)
      #print "pos[",i,"][",0,"]=",pos[i][0]
      if numdim>1:
        pos[i][1]=radius*np.sin(a)
      #print "pos[",i,"][",1,"]=",pos[i][1]
    #print pos
    return pos

  # It is not possible to pass a class member as a default value to any function or attribute, e.g. "numpos=self.N" or "numpos=N" below
  # In fact, no default value for function or object arguments may ever be anything that might change at runtime, it must be a constant defined at compile time
  # Fortunately math.pi and other constants are indeed compile-time constants and are fair game for argument default values
  def InitializePositions(self,numpos=None,radius=1.1,numdim=3):    
    """To facilitate optimization of positions, set all positions to nonzero values. Random or circle patterns are usually best. This version uses a circle."""
    log.debug(str(type(self))+".InitializePositions(numpos="+str(numpos)+",radius="+str(radius)+"...)")
    if (numpos!=None):
      self.N = numpos     
    if self.N>0:
      self.positions = self.CirclePositions(self.N,radius,numdim)+0.1*radius*np.random.rand(self.N,numdim)
    log.debug("Reinitialized the radio positions to "+str(self.N)+" positions around a circle.")
#    pub.sendMessage("POSITIONS", self.positions)
    
  def InitializeDistances(self):
    self.distances = np.zeros((self.N, self.N)) # make room in the NxN numpy array for more measured distances between nodes, can't save the old data using numpy objects easily

  def OptimizePositions(self):
    
    self.ComputePositions()
    
  def ComputePositions(self):
    """Optimize the estimated radio positions to match the measured distances between radios."""
    global global_distances #HL: without this global statement the global variable is masked by a local one
    global_distances = self.distances
    log.debug("global_distances="+str(global_distances))
    if np.all( (self.positions==np.zeros( (self.N*2) ) ) ):
      self.InitializePositions()
    p = np.array(self.Positions3Mto2V(self.positions))    
    log.debug("positions sent to optimizer="+str(p))
    x1 = optim.fmin(CostFun, p, xtol=1e-4,ftol=1e-5,maxiter=100,maxfun=100)
    self.positions = self.Positions2Vto3M(x1)
    
  def GetPositions(self):
    """Return the Nx3 matrix of position vectors, one 3-D vector for each radio location."""
    return self.positions
    
  def GetDistances(self):
    """Return the NxN matrix of distances between radios, one distance for each direction of travel between the nodes and diagonals all zero (self-distances)."""
    return self.distances

  def GetPositions2D(self):
    """Return the Nx2 matrix of position vectors, one 2-D vector for each radio location (ignoring z-axis position)."""
    return np.resize(self.positions,(4,2))
    
  def Set(self,p=None):
    log.debug("Mesh.Set("+str(p)+") called with argument type '"+str(type(p))+"'.")
    # distances and positions are indistiguishable for 3 radio meshes, so this is useless

  def SetPositions(self,p=None):
    """Change the matrix of position vectors to those provided."""
    #print "setting positions to ",p
    if self.N == 2*np.size(self.positions,):
      self.positions = Positions2Vto3M(self,p)
    elif self.N == np.size(self.positions,0):
      self.positions = np.resize(p,(self.N,3)) # make sure it'self the right shape before storing in local position matrix
    elif self.N == 3*np.size(self.positions,):
      self.positions = np.reshape(p,(self.N,3)) # make sure it'self the right shape before storing in local position matrix
    else:
      return None
    self.p2d = np.zeros((self.N, self.N))# clear the NxN numpy matrix of distances implied by the positions
    self.distances = np.resize(self.distances,(self.N, self.N)) # make room in the NxN numpy array for more measured distances between nodes
#    pub.sendMessage("POSITIONS", self.positions)
    return self.Positions2Distances()    
    
  #end of Mesh class

if __name__ == "__main__":
# breaks between                                                                                             |           |           |           |           |
  lines = [ "        753.231990mS  61 88 3D 3B 0C 01 00 00 00 48 00 01 00 00 00 03 5C 40 01 01 00 00 30 01 0A 00 00 00 00 03 B7 90 18 02 B1 7A 18 01 BF C7 18 F2 54",\
            "        307.776000mS  61 88 20 3B 0C 00 00 03 00 48 00 00 00 03 00 03 41 40 01 01 00 00 30 01 0C 00 00 00 00 00 B7 8D 80 02 B7 AD 80 01 AD A2 80 3A 73", \
            "        849.807980mS  61 88 1D 3B 0C 00 00 01 00 48 00 00 00 01 00 03 9E 40 01 01 00 00 30 01 0B 00 00 00 00 02 B7 9C 64 03 AE 95 64 00 BF CD 64 A4 2B", \
            "        299.168000mS  61 88 22 3B 0C 00 00 02 00 48 00 00 00 02 00 03 9C 40 01 01 00 00 30 01 0C 00 00 00 00 03 B7 B6 04 01 B6 9C 04 00 B2 80 04 2F 5C", \
            "        254.000000mS  61 88 1B 3B 0C 00 00 02 00 48 00 00 00 02 00 03 95 40 01 01 00 00 30 01 07 00 00 00 00 03 C0 D1 04 01 B6 A5 04 00 BB 9A 04 EF 8C", \
            "       3528.304000mS  61 88 2B 3B 0C 01 00 00 00 48 00 01 00 00 00 03 4A 40 01 01 00 00 30 01 06 00 00 00 00 03 BA B4 18 02 B4 9C 18 01 BE CA 18 64 D9", \
            "        424.287990mS  61 88 1A 3B 0C 00 00 03 00 48 00 00 00 03 00 03 3B 40 01 01 00 00 30 01 08 00 00 00 00 00 BA A7 80 02 BA C0 80 01 A9 C5 80 FB 72", \
            "        797.200010mS  61 88 14 3B 0C 00 00 01 00 48 00 00 00 01 00 03 95 40 01 01 00 00 30 01 07 00 00 00 00 02 BA A8 64 03 B1 D5 64 00 C0 D1 64 DE E8", \
            "        259.952000mS  61 88 1C 3B 0C 00 00 02 00 48 00 00 00 02 00 03 96 40 01 01 00 00 30 01 08 00 00 00 00 03 C0 D1 04 01 B6 A5 04 00 B4 90 04 1B 3B", \
            "       3558.528100mS  61 88 41 3B 0C 01 00 00 00 48 00 01 00 00 00 03 60 40 01 01 00 00 30 01 0B 00 00 00 00 03 B7 8F 18 02 B1 72 18 01 BF C7 18 7B 35"]
  m = Mesh()
  for line in lines:
    m.AddPacket(line)
  m.ComputePositions()
  #print m.positions
    
def test_optimize():
  m = Mesh()
  x = 10*np.random.rand(8)
  print x
  global_distances = Positions2Distances(x)
  print global_distances
  x3 = m.Positions2Vto3M(x)
  print x3
  print np.size(x3)
  global_distances2 = m.SetPositions(np.reshape(x3,(4,3)))
  print m.positions
  print global_distances2
  
  x2 = x+np.random.rand(8)
  print x2
  y = CostFun(x2)
  print y
    
  x0 = optim.fmin(CostFun,np.random.rand(8))
  print x0
  print CostFun(x0)

