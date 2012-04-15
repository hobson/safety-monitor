#!C:\Python25\python.exe
DEFAULT_RSSI_BIAS = 64  # 5-bit rssi value maxes out at 2^6 for zero range
DEFAULT_RSSI_GAIN = -.05 # 5 cm closer for each step up in RSSI 
DEFAULT_RSSI_GAIN2 = 0 # increasing RSSI means decreasing distance
DEFAULT_LQI_BIAS = 256  # 8-bit LQI value maxes out at 2^6 for zero range
DEFAULT_LQI_GAIN = -.02 # 1 cm closer for each step up in LQI
DEFAULT_LQI_GAIN2 = 0 # increasing RSSI means decreasing distance

class Edge(object): # (object) inheritance is critical to getting the type() function to work
  def __str__(s):
    return (str(s.srcAdd)+"->"+str(s.dstAdd)+" RSSI:"+str(s.RSSI)+" LQI:"+str(s.LQI))

  """Object to contain eeverything about an edge, its RSSI, LQI, start node and end node"""  
  # create an Edge from a packet
  def __init__(self, p=None):
    self.srcAdd = None
    self.dstAdd = None
    self.RSSI = None
    self.LQI = None
    self.distance = None  
    self.distances = None  
    self.positions = None
    # each edte should have its own unique bias and gain that are incrementally adjusted
    self.bias  = DEFAULT_RSSI_BIAS
    self.gain  = DEFAULT_RSSI_GAIN # meters per RSSI
    self.gain2 = DEFAULT_RSSI_GAIN2 # meters per RSSI**2 
    self.lqi_bias  = DEFAULT_LQI_BIAS
    self.lqi_gain  = DEFAULT_LQI_GAIN # meters per RSSI
    self.lqi_gain2 = DEFAULT_LQI_GAIN2 # meters per RSSI**2 
    if ((p)  and  (type(p) == list)  and  (len(p) == 4)):
      self.srcAdd = long(p[0]) # may need to make these longs to hold 16-bit unsigned integer network addresses
      self.dstAdd = long(p[1])
      self.RSSI = long(p[2])
      self.LQI = long(p[3])
      self.distance = self.gain*(self.RSSI-self.bias)+self.gain2*(self.RSSI-self.bias)**2+self.lqi_gain*(self.LQI-self.lqi_bias)+self.lqi_gain2*(self.LQI-self.lqi_bias)**2
      #print self.RSSI,",",self.LQI,"-->",self.distance

  def setBias(self,b):
    self.bias = b
  
  def setGain(self,g):
    self.gain = g
