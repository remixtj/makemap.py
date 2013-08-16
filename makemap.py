#!/usr/bin/python
from __future__ import division
import gpxpy
import argparse
import sys
import os
import datetime
import matplotlib.pyplot as plt
from shutil import copyfile
from urlparse import urlparse
from ftplib import FTP,FTP_TLS

def put_to_ftp(conn,name,remotedir,fgpx):
    conn.cwd(remotedir)
    d = os.path.dirname(name) if os.path.dirname(name) != '' else (name.split('/')[-2] if len(name.split('/'))>1 else name)
    conn.mkd(d)
    conn.cwd(remotedir+'/'+d)
    conn.storbinary('STOR index.html',open(name+'/index.html','rb'))
    conn.storbinary('STOR data.js',open(name+'/data.js','rb'))
    conn.storbinary('STOR profilo.png',open(name+'/profilo.png','rb'))
    conn.storbinary('STOR '+os.path.basename(fgpx),open(name+'/'+os.path.basename(fgpx),'rb'))
    conn.quit()
    conn.close()


TEMPLATE = "/home/remixtj/scripts/mappina/index.html"

parser = argparse.ArgumentParser(description='Starting from a gpx, creates an html file with map, elevation profile and timings')

parser.add_argument('gpxfile',metavar='GPX',type=str,help="Name of the GPX File")
parser.add_argument('-n','--name',type=str,help="Name of the output directory")
parser.add_argument('-d', '--desc', nargs = '+', help = 'Description of Track',required=True)
#parser.add_argument('--ftp',help="Publish to ftp",action="store_true")
parser.add_argument('--ftp',help="ftp url where to publish in the form ftp://user:password@domain:/path (use ftps for FTP_TLS)",type=str)
args = parser.parse_args()


try:
    gpx = gpxpy.parse(open(args.gpxfile))
except IOError:
    print "Invalid file name"
    sys.exit(-1)
except gpxpy.gpx.GPXXMLSyntaxException:
    print "Invalid gpx file format"
    sys.exit(-1)

q = urlparse(args.ftp)
to_ftp = False
if (q.scheme == 'ftp' or q.scheme=='ftps') and q.hostname:
    to_ftp = True
    

lon = []
lat = []
elevation = []
pts = []

for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            lat.append(point.latitude)
            lon.append(point.longitude)
            elevation.append(point.elevation)
            pts.append(point)
centroid = (sum(lat) / len(lat), sum(lon) / len(lon))
moving_time, stopped_time, moving_distance, stopped_distance, max_speed = gpx.get_moving_data()
in_moto = str(datetime.timedelta(seconds=moving_time))
in_sosta = str(datetime.timedelta(seconds=stopped_time))
totale = str(datetime.timedelta(seconds=(moving_time+stopped_time)))

pdsts = [ pts[i].distance_3d(pts[i-1]) if i != 0 else 0 for i in range(0,len(pts))]
dsts = [ sum(pdsts[0:i]) for i in range(0,len(pdsts)) ]
plt.plot(dsts,elevation)
plt.plot(dsts,[ max(elevation) for i in range(0,len(elevation))],label="Max elevation: {}".format(max(elevation)))
plt.legend()
x1,x2,y1,y2 = plt.axis()
plt.axis((x1,x2,y1,y1+((y2-y1)*1.15)))
plt.ylabel('Elevation (m)')
plt.xlabel('Distance (m)')

if args.name:
    dirn = args.name
else:
    dirn = os.path.basename(args.gpxfile)[:-4]

if not os.path.exists(dirn):
    os.mkdir(dirn)
    copyfile(TEMPLATE,dirn+"/index.html")
    copyfile(args.gpxfile,dirn+"/"+os.path.basename(args.gpxfile))
    datajs = open(dirn+"/data.js","w")
    datajs.write("var lat={}\nvar lon={}\nvar zoom=13\nvar fgpx=\"{}\"\nvar trackname=\"{}\"\nvar inmoto=\"{}\"\nvar insosta=\"{}\"\nvar totale=\"{}\"".format(centroid[0],centroid[1],os.path.basename(args.gpxfile)," ".join(args.desc),in_moto,in_sosta,totale))
    datajs.close()
    plt.savefig(dirn+"/profilo.png")
    if to_ftp:
        print("Uploading to ftp...\n\n")
        if q.scheme == 'ftps':
            f = FTP_TLS(q.hostname)
            f.prot_p()
        else:
            f = FTP(q.hostname)

        f.login(q.username,q.password)
        put_to_ftp(f,dirn,q.path,args.gpxfile)

        #os.system("/usr/bin/lftp -u remix@remixtj.net -e \"set ftp:ssl-allow no; mirror -R {}/ /htdocs/alpine/;exit\" dancetj.net".format(dirn))

else:
    print "Error creating {}/: directory exists".format(dirn)
