from distutils.core import setup
import py2exe
import glob
extensions = ['py'] # png files can't be loaded, but img2img.convert may be ablet to deal with them. img2png can certainly save them
directories = ['./']
files=[]
for e in extensions:
  for d in directories:
    files.extend(glob.glob(d+"*."+e)) # .extend is the same as old_list[len(old_list):]=added_list, actHL: find uses for extend() in Mesh where np.concatenate and np.append are used inneficiently

setup(name="Safety Monitor",
  scripts=files, #['SafetyMonitor.py'],
  version = "0.3",
  company_name = "Transceive Technology Corporation",
  copyright = "(c) 2009-2010 All Right Reserved", # doesn't show up in egg-data
  Summary = "Child safety monitoring and home layout drawing applications", # doesn't show up in egg-data
  homepage = "http://transceivetechnology.com", # doesn't show up in egg-data
  author = "Hobson Lane",
  author_email = "hobson@transceivetechnology.com",
  license = "(c) 2009-2010 All Rights Reserved, Supplied As-Is, Use at your own risk",
  descriptions = "Connects to Transceive Technology hardware to determine the location and safety of children or adults wearing them", # doesn't show up in egg-data
  platform = "Windows XP,Vista,7", #doesn't show up
  #windows = ["SafetyMonitor.py"],
  console = ["SafetyMonitor.py"],
  ) 
