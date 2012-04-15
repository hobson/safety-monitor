import os
import glob

dist_dir = 'dist'

files = ['C:/Python25/lib/site-packages/wx-2.8-msw-ansi/wx/MSVCP71.dll',
         'C:/Python25/lib/site-packages/wx-2.8-msw-ansi/wx/gdiplus.dll',
         './rev20.log',
         'images']

for f in files:
  os.system("cp -r "+f+" "+dist_dir+"/")
  
os.system("rm -r "+dist_dir+"/images/.svn")
os.system("rm -r "+dist_dir+"/images/Thumbs.db")
#os.system("gzip -r -S .zip -9 "+dist_dir)
os.system("7z a -tzip -mx=9 "+dist_dir+".zip "+dist_dir)