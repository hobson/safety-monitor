#import math # surprisingly this isn't required for min() and max() functions
import re
import binascii
import string
#from array import array # is this required
import pickle #serialization of objects


class Packet(object):
  def __str__(s):
    if s and s.t:
      text  = "%(srcAdd)05d ->%(dstAdd)05d\t" % {'srcAdd': s.srcAdd, 'dstAdd': s.dstAdd}
      for i in range(s.TT_MAX_NEIGHBORS):
        text += str(s.neighbors[i][0])+"=\t"+str(s.neighbors[i][1])+"\t"+str(s.neighbors[i][2])+"\t| "
    else:
      #log.debug("Unusual Packet: probably a comment at the beginning or end of the log file")
      text = "----------"
    #ActionHL: really need to delay the display of this packet until a display timer goes off and when it does trigger the read of the next packet
    #ActionHL: otherwise the simulation of the real timing of packets isn't realistic and code may break on real packets and not during simulation
    #text+="\n"
    text = ''.join([(c >= '\x09') and c or '<%d>' % ord(c)  for c in text]) # replace characers with ascii less than 9 with their ASCI decimal value surrounded by <> brackets
    return text

  def __init__(s, text):
    s.TT_MAX_NEIGHBORS = 3 # including self
    s.TT_PACKET_BYTES = 43
    s.TT_PAYLOAD_BYTES = 16
    s.TT_BYTES_PER_NEIGHBOR = 4
    s.TT_MAX_NWK_ADD = 3
    s.MAC_TYPES = ["Beacon", "Data", "Acknowledgement", "Command"]
    s.MAX_MAC_TYPE = 3
    s.MAC_COMMANDS = ["Undefined", "Association Request", "Association Response",\
                    "Disassociation Notification", "Data Request",            \
                    "PAN ID Conflict Notification", "Orphan Notification",    \
                    "Beacon Request", "Coordinator Realignment", "GTS Request",\
                    "Reserved"]
    s.MAX_MAC_COMMAND = int(10)
    s.SECURITY_KEY_ID_BYTES = [0, 1,  5,  9] # total security header lengths can be [0, 5, 6, 10, 14]
    s.translation_table = ''.join(chr(i) for i in xrange(256))
    s.t = None; # time the packet was received (relative to the previous packet received)
    s.seq = None; # sequence number transmitted by the sender (relative to the other packets it has sent)
    s.N = None; # number of bytes in the entire MAC packet, including FCF header and CRC footer
    s.FCF = None; # 2 byte frame control field
    s.pTime = re.compile(r"^\s*(\d*\.\d*)mS\s+([0123456789ABCDEF ]+)\s*") # pattern for pulling the time value off
    s.h = None # string array of hexadecimal characters without spaces (2 characters for each byte)
    s.b = None #[""] #array('B',"") # array of bytes directly representing the values in the packet
    s.srcAdd = 0L # network address of the source
    s.dstAdd = 0L # network address of the destination
    s.mac_type = 0 # MAC frame type (0=Beacon, 1=Data, 2=Acknowledgement, 3=Command)
    s.mac_type_name = ""
    s.mac_command = 0 # 0=Undefined, 1=Association Request, ..., 9=GTS Request, 10<=Reserved
    s.mac_command_name = ""
    s.srcAddMode = 0 # this integer is redundant with the bit counts below
    s.dstAddMode = 0 # this integer is redundant with the bit counts below
    s.srcAddBytes = 0 # 0, 16, or 64 bit network address used for the source address
    s.dstAddBytes = 0 # 0, 16, or 64 bit network address used for the destination address
    s.srcPANBytes = 0 # 0, 16, or 64 bit network address used for the source address
    s.srcPANBytes = 0 # 0, 16, or 64 bit network address used for the source address
    s.dstPAN = 0L
    s.srcPAN = 0L
    s.PANIDCompressed = False
    s.reqACK = False
    s.secEnabled = False
    s.pendPacket = False
    s.invalidResBits = 0
    s.secKeyIDBytes = 0
    s.SCF = 0
    s.secLevel = 0
    s.secKeyIDMode = 0
    s.secInvalidResBits = 0
    s.secFrameCounter = 0L # need 8-bit unsigne int
    s.secKeyIDBytes = 0
    s.secKeyID = 0L # need 64-bit unsigned ing
    s.CRC = None # need 16-bit unsigned int
    s.mac_header_bytes = None
    s.mac_footer_bytes = None
    s.nwk_header_bytes = None
    s.packet_bytes = None
    #actHL: make this a numpy matrix for easier processing and sizing
    s.neighbors = [[int(0) for i in range(s.TT_BYTES_PER_NEIGHBOR)] for i in range(s.TT_MAX_NEIGHBORS+1)]

    m = re.match(s.pTime,text)
    if m and len(m.groups())==2:
      #print m.groups()
      s.t = m.group(1)
      s.h = m.group(2)
      #print s.h
      s.h = s.h.translate(s.translation_table, " \t")
      s.b = binascii.unhexlify(s.h) # should also look into array.byteswap for the portions of the array that contian multi-byte elements misordered
      #print "Hex digits:" + str(len(s.h))
    else:
      return None
      #print "Not a standard hexadecimal packet line."
    s.packet_bytes = len(s.b)
    nextByte = 0
    # for TT packets this is bytes 0 & 1 from left (0 offset, 0 = first byte received)
    s.FCF = long(ord(s.b[nextByte+1]))*256 + long(ord(s.b[nextByte]))
    nextByte += 2
    # bytes swapped and bits read from LSB to MSB to match 802.15.4 spec
    s.mac_type        =  int((s.FCF & (0x03 <<  0))>>0 )
    s.invalidResBits  = long((s.FCF & (0x01 <<  2))>>2 ) #2 bit (#0= LSB) should always be zero
    s.secEnabled      = bool((s.FCF & (0x01 <<  3))>>3 )
    s.pendPacket      = bool((s.FCF & (0x01 <<  4))>>4 )
    s.reqACK          = bool((s.FCF & (0x01 <<  5))>>5 )
    s.PANIDCompressed = bool((s.FCF & (0x01 <<  6))>>6 )
    s.invalidResBits += long((s.FCF & (0x07 <<  7))>>7 ) #7,8&9 bits (#0=LSB) should always be zero
    s.dstAddMode      =  int((s.FCF & (0x03 << 10))>>10)
    s.invalidResBits += long((s.FCF & (0x03 << 12))>>12) #12&13 bits (#0=LSB) should always be zero
    s.srcAddMode      =  int((s.FCF & (0x03 << 14))>>14)
    s.mac_type_name = s.MAC_TYPES[ min( max(s.mac_type, 0) , s.MAX_MAC_TYPE) ]
    s.dstAddBytes = int((4**s.dstAddMode)/8) if s.dstAddMode>0 else 0
    s.srcAddBytes = int((4**s.srcAddMode)/8) if s.srcAddMode>0 else 0
    #print "srcAddbytes=" + str(s.srcAddBytes)
    s.srcPANBytes = 2 if s.srcAddMode and not s.PANIDCompressed else 0
    s.dstPANBytes = 2 if s.dstAddMode else 0
    # for TT packets this is byte 2 from left (0 offset, 0 = first byte received)
    s.seq = ord(s.b[nextByte])
    # for TT packets this is bytes 3 & 4 from left (0 offset, 0 = first byte received)
    nextByte += 1 # position of next unprocessed byte in the array s.b[]
    if s.dstPANBytes > 0:
      s.dstPAN = 0L
      for i in range(s.dstPANBytes):
        s.dstPAN += long(ord(s.b[nextByte+i]))<<(i*8)
    nextByte += s.dstPANBytes
    # for TT packets this is bytes 5 & 6 from left (0 offset, 0 = first byte received)
    s.dstAdd = 0L
    for i in range(s.dstAddBytes): 
      s.dstAdd   += long(ord(s.b[nextByte+i]))<<(i*8)
    nextByte += s.dstAddBytes
    # for TT packets PANIDCompressed is always true, so no bytes used for srcPAN
    if s.PANIDCompressed:
      s.srcPAN = s.dstPAN
    else:
      s.srcPAN = 0L
      for i in range(s.srcPANBytes):  
        s.srcPAN += long(ord(s.b[nextByte+i]))<<(i*8)
    nextByte += s.srcPANBytes
    # for TT packets this is bytes 7 & 8 from left (0 offset, 0 = first byte received)
    s.srcAdd = 0L
    for i in range(s.srcAddBytes): 
      s.srcAdd += long(ord(s.b[nextByte+i] ))<<(i*8)
    #print "srcAdd=" + str(s.srcAdd) + "@ byte" + str(nextByte)
    nextByte += s.srcAddBytes
    # Security Control Field, Frame Counter, and KeyIDMode
    # HL: need to check that I'm doing the correct byte order/swapping here
    if s.secEnabled:
      s.SCF = s.b[nextByte] 
      s.secLevel           = int((s.SCF & (0x07 <<  0))>>0 )
      s.secKeyIDMode       = int((s.SCF & (0x03 <<  3))>>3 )
      s.secInvalidResBits  = int((s.SCF & (0x07 <<  5))>>5 ) # reserved bits for which nonzero is invalid
      nextByte += 1
      s.secFrameCounter = long(s.b[nextByte]) # need long to capture the unsigned char as a signed integer
      nextByte += 1
      # HL: key index is shown on the right in a multi-octet field so it is the MSbyte and RXed last
      s.secKeyIDBytes = s.SECURITY_KEY_ID_BYTES[s.secKeyIDMode]
      s.secKeyID = 0
      if s.secKeyIDMode > 0:
        for i in range(s.secKeyIDBytes):
          s.secKeyID += long(ord(s.b[nextByte+i]))<<(i*8)
      nextByte += s.secKeyIDBytes
    if s.mac_type_name == "Command":
      s.mac_command = int(ord(s.b[nextByte]))
      s.mac_command_name = s.MAC_COMMANDS[ min(max(s.mac_command, 0), s.MAX_MAC_COMMAND) ]
    else:
      s.mac_command = None
      s.mac_command_name = None 
    s.mac_header_bytes = nextByte
    s.CRC = long(ord(s.b[s.packet_bytes-1]))*256 + long(ord(s.b[s.packet_bytes-2]))
    s.mac_footer_bytes = 2 # 2-byte CRC
    # unfortunately this only gets us through the MAC header (1st 10 bytes), the NWK header is another 15 bytes
    # HL: may need to implement NWK header/footer parsing
    s.nwk_header_bytes = 16
    if s.mac_header_bytes > s.packet_bytes - s.mac_footer_bytes:
      return None
    #print nextByte
    #print s.mac_header_bytes
    #print s.mac_header_bytes + s.nwk_header_bytes + s.mac_footer_bytes + s.TT_PAYLOAD_BYTES
    #print s.packet_bytes
    # this may ignore packets that are good if NWK header length is not consitently 15 bytes for good packets
    if s.mac_header_bytes + s.nwk_header_bytes + s.mac_footer_bytes + s.TT_PAYLOAD_BYTES != s.packet_bytes:
      return None      
    i0 = s.packet_bytes - s.TT_PAYLOAD_BYTES - s.mac_footer_bytes + s.TT_BYTES_PER_NEIGHBOR # (skip the first neighbor entry, it's a self info entry)
    for i in range( s.TT_MAX_NEIGHBORS ):
      #print "processing neighbor" + str(i) + "with" + str(( ord(s.b[i0+i*4 ])<=s.TT_MAX_NWK_ADD)) + str((i-1) <= ord( s.b[i0+i+3]))
      nAdd = int(ord(s.b[i0+i*4]))
      #print "  neighbor address" + str(nAdd)
      # this additional check doesn't work: (ord(s.b[i0+i*4+3]) <= s.TT_MAX_NEIGHBORS) nor this (i-1) <= ord( s.b[i0+i+3]))
      # for some reason the numneighbors value reported by each device is different and usually much larger than 3
      if (nAdd <= s.TT_MAX_NWK_ADD) :          
        #             NWK_ID               CRC valid,                    RSSI,              LQI,   num_neighbors
        s.neighbors[ i ][0] = nAdd #int((ord(s.b[i*4+1]) & (0x01 << 7))>>7 ) # CRC
        #print "rssi = " + str(ord(s.b[i0+i*4+1])) + " " + str(ord(s.b[i0+i*4+2]))
        s.neighbors[ i ][1] = int( ord(s.b[i0+i*4+1]) & 0x1F            ) #RSSI
        s.neighbors[ i ][2] = int( ord(s.b[i0+i*4+2])                   ) #LQI
        s.neighbors[ i ][3] = int( ord(s.b[i0+i*4+3])                   ) #numneighbors (doesn't seem right)                
  # end of __init_
  
  def Describes(s):
    s.description = ""
    s.description += s.t + " ms " 
    s.description += s.secLevel if s.secLevel > 0 else ""
    return s.description
    
  
  def Describe(s):  
    print s.Describes()
         
if __name__ == "__main__":
  p = Packet(  "        753.231990mS  61 88 3D 3B 0C 01 00 00 00 48 00 01 "+\
             "00 00 00 03 5C 40 01 01 00 00 30 01 0A 00 00 00 00 03 B7 90 "+\
             "18 02 B1 7A 18 01 BF C7 18 F2 54")
  #print p.h
  print pickle.dumps(p)
  p = Packet(  "       1506.816000mS  03 08 01 FF FF FF FF 07 13 2D") 
  print pickle.dumps(p)
