#!/usr/bin/python
from __future__ import division
import gpxpy
import argparse
import sys
import os
import datetime
import matplotlib.pyplot as plt
import webbrowser
import SocketServer
import SimpleHTTPServer
import BaseHTTPServer
import time
from shutil import copyfile
from urlparse import urlparse
from ftplib import FTP,FTP_TLS
from threading import Thread

from config import TEMPLATE
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(os.path.dirname(TEMPLATE)))
page = env.get_template(os.path.basename(TEMPLATE))



server_stop = False
do_later = False

def put_to_ftp(conn,name,remotedir):
    conn.cwd(remotedir)
    d = os.path.dirname(name) if os.path.dirname(name) != '' else (name.split('/')[-2] if len(name.split('/'))>1 else name)
    conn.mkd(d)
    conn.cwd(remotedir)
    for dp, dn, fn in os.walk(name):
        sys.stdout.write('CWD {} ....'.format(dp))
        try:
            conn.cwd(dp)
        except:
            conn.mkd(dp.split('/')[-1])
            conn.cwd(dp.split('/')[-1])

        print(' OK')
        for f in fn:
            sys.stdout.write('{} ....'.format(f))
            conn.storbinary('STOR {}'.format(f),open(dp+'/'+f,'rb'))
            print(' OK')
        for dr in dn:
            sys.stdout.write('{} ....'.format(dr))
            conn.mkd(d)
            print(' OK') 
    
    print ('Upload complete')
    conn.quit()
    conn.close()

def webserver(directory,server_class=BaseHTTPServer.HTTPServer,
                   handler_class=SimpleHTTPServer.SimpleHTTPRequestHandler):
    PORT = 6655
    os.chdir(directory)
    server_address = ('localhost', PORT)
    httpd = server_class(server_address, handler_class)
    count = 0
    nfiles = 0
    for d,p,f in os.walk('.'):
        nfiles += len(f)
    while count < nfiles+1:
        count += 1
        httpd.handle_request()

def browser():
    try:
        webbrowser.open('http://localhost:6655')
    except:
        print 'Problem opening web browser. Point your browser to http://localhost:6655'

    sys.exit(0)


def get_tipo():
    return "Escursione"

parser = argparse.ArgumentParser(description='Starting from a gpx, creates an html file with map, elevation profile and timings')

parser.add_argument('gpxfile',metavar='GPX',type=str,help="Name of the GPX File")
parser.add_argument('-n','--name',type=str,help="Name of the output directory")
parser.add_argument('-d', '--desc', nargs = '+', help = 'Description of Track',required=True)
parser.add_argument('--show',help="Shows in local browser",action="store_true")
parser.add_argument('--ftp',help="ftp url where to publish in the form ftp://user:password@domain:/path (use ftps for FTP_TLS)",type=str)
parser.add_argument('-p','--photofile',help="path of the file output of the syncphoto.py script",type=str)
parser.add_argument('-i','--imgdir',help="path of directory containing the photos referenced by the file passed with paramenter -p/--photofile",type=str)
args = parser.parse_args()


try:
    gpx = gpxpy.parse(open(args.gpxfile))
except IOError:
    print "Invalid file name"
    sys.exit(-1)
except gpxpy.gpx.GPXXMLSyntaxException:
    print "Invalid gpx file format"
    sys.exit(-1)

to_ftp = False
try:
    q = urlparse(args.ftp)
    if (q.scheme == 'ftp' or q.scheme=='ftps') and q.hostname:
        to_ftp = True
except:
    pass


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

moving_time, stopped_time, moving_distance, stopped_distance, max_speed = gpx.get_moving_data()
in_moto = str(datetime.timedelta(seconds=moving_time))
in_sosta = str(datetime.timedelta(seconds=stopped_time))
totale = str(datetime.timedelta(seconds=(moving_time+stopped_time)))
qminima = min(elevation)
qmassima = max(elevation)
distanza = "{0:.2f}".format(gpx.length_3d())
uphill = "{0:.0f}".format(round(gpx.get_uphill_downhill()[0],0))
downhill = "{0:.0f}".format(round(gpx.get_uphill_downhill()[1],0))
dislivello = round(qmassima-qminima,1)
tipo = get_tipo()

start_date, end_date = gpx.get_time_bounds()
if start_date.date() == end_date.date():
    data = start_date.date()
else:
    data = "{} - {}".format(start_date.date(),end_date.date())

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
    copyfile(args.gpxfile,dirn+"/"+os.path.basename(args.gpxfile))
    copyfile(os.path.dirname(TEMPLATE)+"/compass.png",dirn+"/compass.png")
    copyfile(os.path.dirname(TEMPLATE)+"/my.css",dirn+"/my.css")
    copyfile(os.path.dirname(TEMPLATE)+"/pure-min.css",dirn+"/pure-min.css")
    if args.photofile:
        copyfile(os.path.dirname(TEMPLATE)+"/venobox.css",dirn+"/venobox.css")
        copyfile(os.path.dirname(TEMPLATE)+"/venobox.min.js",dirn+"/venobox.min.js")
        copyfile(os.path.dirname(TEMPLATE)+"/jquery.js",dirn+"/jquery.js")
        os.mkdir('{}/photos/'.format(dirn))
        copyfile(args.photofile,dirn+"/"+args.photofile)
        if not args.imgdir:
            print("Warning: no imgdir (-i parameter) specified, you should copy by hand photos listed in {} to {}/photos/".format(args.photofile,args.name))
        else:
            for dp, df, fn in os.walk(args.imgdir):
                for f in fn:
                    copyfile('{}/{}'.format(dp,f),'{}/photos/{}'.format(dirn,f))
            
    open(dirn+"/data.ini","w").write("title={} {}\n".format(os.path.basename(args.gpxfile)[:-4]," ".join(args.desc)))
    plt.savefig(dirn+"/profilo.png",transparent=True)
    with open(dirn+"/index.html","w") as indexf:
        indexf.write(page.render(inmoto=in_moto,insosta=in_sosta,totale=totale,qminima=qminima,qmassima=qmassima,distanza=distanza,uphill=uphill,downhill=downhill,dislivello=dislivello,fgpx=os.path.basename(args.gpxfile),trackname=" ".join(args.desc),data=data,tipo=tipo,photofile=args.photofile))

    if to_ftp:
        print("Uploading to ftp:")
        if q.scheme == 'ftps':
            f = FTP_TLS(q.hostname)
            #f.set_debuglevel(2)
            f.auth()
        else:
            f = FTP(q.hostname)

        f.login(q.username,q.password)
        if q.scheme == 'ftps':
            f.prot_p()
        put_to_ftp(f,dirn,q.path)
    if args.show:
        Thread(target=webserver,args=(dirn,)).start()
        browser()

else:
    print "Error creating {}/: directory exists".format(dirn)
