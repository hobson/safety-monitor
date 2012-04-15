#!/usr/bin/env python
import wx.tools.img2py as i2p
import glob
import string

resource_file = "NewResourcesToAdd.py"
print "-"*78
print "Looking for BMP and PNG files in this directory and one level down. Then converting them into a Python resource file called",resource_file,"in the current working directory."
print "."*78
extensions = ['bmp','gif'] # png files can't be loaded, but img2img.convert may be ablet to deal with them. img2png can certainly save them
directories = ['./','./*/']
files=[]
for e in extensions:
  for d in directories:
    files.extend(glob.glob(d+"*."+e)) # .extend is the same as old_list[len(old_list):]=added_list, actHL: find uses for extend() in Mesh where np.concatenate and np.append are used inneficiently
for k,f in enumerate(files):
  n = string.rfind(f, '.') # no need to check for success since *dot pattern used to create list of filenames so they will all contain at least one dot
  i2p.img2py(f, resource_file, append=bool(k), compressed=True, maskClr=None, imgName=f[0:n])#, icon=False, catalog=False, functionCompatible=True, functionCompatibile=-1)
  
