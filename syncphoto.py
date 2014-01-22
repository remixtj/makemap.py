import datetime
import exifread
import gpxpy
import gpxpy.gpx
import argparse
import os

from PIL import Image
from os import listdir
from os.path import isfile, join



def exif_time(pto,path,offset):
    print pto
    DT_TAGS = ["Image DateTime", "EXIF DateTimeOriginal", "DateTime"]
    f = open(path+pto, 'rb')
    tml = False
    try:
        tags = exifread.process_file(f,details=False)
        for dt_tag in DT_TAGS:
            try:
                dt_value = "%s" % tags[dt_tag]
                break
            except:
                continue
        if dt_value:
            tpl = datetime.datetime.strptime(dt_value, '%Y:%m:%d %H:%M:%S')
            # Offset
            tpl = tpl - datetime.timedelta(hours=offset)

    finally:
        f.close()

    return tpl


parser = argparse.ArgumentParser(description='Takes a directory of images and a gpx as input and creates a file containing coordinates for each photo. The file can be then used to show photos on ')
parser.add_argument('-g','--gpx',type=str,help="Name of the GPX File",required=True)
parser.add_argument('-n','--name',type=str,help="Name of the output file",default='photos.txt')
parser.add_argument('-d', '--dir',type=str,help = 'Directory containing photos',required=True)
parser.add_argument('-o', '--offset', type=float,help = 'Offset of time between gpx time and exif photo time',default=0)
args = parser.parse_args()



try:
    gpx = gpxpy.parse(open(args.gpx))
except IOError:
    print "Invalid file name"
    sys.exit(-1)
except gpxpy.gpx.GPXXMLSyntaxException:
    print "Invalid gpx file format"
    sys.exit(-1)

timepoints = []
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            timepoints.append([point.time,point.latitude, point.longitude])


if (os.path.isdir(args.dir)):
    mypath = args.dir
else:
    print "Invalid photo directory"
    sys.exit(-1)

onlyfiles = [ f for f in listdir(mypath) if isfile(join(mypath,f)) ]

output = [['lat','lon','title','description'],]

for f in onlyfiles:
    ptime = exif_time(f,mypath,args.offset)
    idx = timepoints.index(min(timepoints,key=lambda x:abs(x[0]-ptime)))
    output.append([str(timepoints[idx][1]),str(timepoints[idx][2]),f,'<img src="photos/{}" />'.format(f)])



with open(args.name, 'w') as file:
    file.writelines('\t'.join(i) + '\n' for i in output)
