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
import math
from shutil import copyfile, copytree
from urlparse import urlparse
from threading import Thread
from config import TEMPLATE
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(os.path.dirname(TEMPLATE)))
page = env.get_template(os.path.basename(TEMPLATE))


server_stop = False
do_later = False


def webserver(directory, server_class=BaseHTTPServer.HTTPServer, handler_class=SimpleHTTPServer.SimpleHTTPRequestHandler):
    PORT = 6655
    os.chdir(directory)
    server_address = ('localhost', PORT)
    httpd = server_class(server_address, handler_class)
    count = 0
    nfiles = 0
    for d, p, f in os.walk('.'):
        nfiles += len(f)
    while count < nfiles + 1:
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


def haversine(lat1, lon1, lat2, lon2):
    R = 6372797.560856
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lonh = math.sin(dlon * 0.5)
    lonh *= lonh
    lath = math.sin(dlat * 0.5)
    lath *= lath
    tmp = math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
    return 2 * R * math.asin(math.sqrt(lath + tmp * lonh))


def calcola_minzoom(lat, lon):
    zoom_to_mpx = [156412, 78206, 39103, 19551, 9776, 4888, 2444, 1222, 610.984, 305.492, 152.746, 76.373, 38.187, 19.093, 9.547, 4.773, 2.387, 1.193, 0.596, 0.298]
    dw = haversine(min(lat), min(lon), min(lat), max(lon))
    dh = haversine(min(lat), min(lon), max(lat), max(lon))
    dw2 = haversine(max(lat), min(lon), max(lat), max(lon))
    dh2 = haversine(min(lat), max(lon), max(lat), max(lon))
    haver_width = (dw + dw2) / 2
    haver_height = (dh + dh2) / 2
    wmpx = haver_width / 600
    hmpx = haver_height / 600
    zw = min(x for x in zoom_to_mpx if x > wmpx)
    zh = min(x for x in zoom_to_mpx if x > hmpx)
    return zoom_to_mpx.index(max(zw, zh))


def syncphoto(tracks, directory, offset=0):
    timepoints = []
    for track in tracks:
        for segment in track.segments:
            for point in segment.points:
                timepoints.append([point.time, point.latitude, point.longitude])
    imgfiles = [f for f in os.listdir(mypath) if os.path.isfile(join(mypath, f))]
    output = [['lat', 'lon', 'title', 'description'], ]
    for f in imgfiles:
        ptime = exif_time(f, mypath, offset)
        idx = timepoints.index(min(timepoints, key=lambda x: abs(x[0] - ptime)))
        output.append([str(timepoints[idx][1]), str(timepoints[idx][2]), f, '<a data-lightbox="{0}" href="photos/{0}"><img width="200px" src="photos/{0}" /></a>'.format(f)])
    return ''.join(['\t'.join(i) + '\n' for i in output])


parser = argparse.ArgumentParser(description='Starting from a gpx, creates an html file with map, elevation profile and timings')

parser.add_argument('gpxfile', metavar='GPX', type=str, help="Name of the GPX File")
parser.add_argument('-n', '--name', type=str, help="Name of the output directory")
parser.add_argument('-d', '--desc', nargs='+', help='Description of Track', required=True)
parser.add_argument('--show', help="Shows in local browser", action="store_true")
parser.add_argument('-p', '--photofile', help="path of the file output of the syncphoto.py script", type=str)
parser.add_argument('-i', '--imgdir', help="path of directory containing the photos referenced by the file passed with paramenter -p/--photofile", type=str)
args = parser.parse_args()


try:
    gpx = gpxpy.parse(open(args.gpxfile))
except IOError:
    print "Invalid file name"
    sys.exit(-1)
except gpxpy.gpx.GPXXMLSyntaxException:
    print "Invalid gpx file format"
    sys.exit(-1)


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
totale = str(datetime.timedelta(seconds=(moving_time + stopped_time)))
qminima = min(elevation)
qmassima = max(elevation)
distanza = "{0:.2f}".format(gpx.length_3d())
uphill = "{0:.0f}".format(round(gpx.get_uphill_downhill()[0], 0))
downhill = "{0:.0f}".format(round(gpx.get_uphill_downhill()[1], 0))
dislivello = round(qmassima - qminima, 1)
tipo = get_tipo()

minzoom = calcola_minzoom(lat, lon)

start_date, end_date = gpx.get_time_bounds()
if start_date.date() == end_date.date():
    data = start_date.date()
else:
    data = "{} - {}".format(start_date.date(), end_date.date())

pdsts = [pts[i].distance_3d(pts[i - 1]) if i != 0 else 0 for i in range(0, len(pts))]
dsts = [sum(pdsts[0:i]) for i in range(0, len(pdsts))]
plt.plot(dsts, elevation)
plt.plot(dsts, [max(elevation) for i in range(0, len(elevation))], label="Max elevation: {}".format(max(elevation)))
plt.legend()
x1, x2, y1, y2 = plt.axis()
plt.axis((x1, x2, y1, y1 + ((y2 - y1) * 1.15)))
plt.ylabel('Elevation (m)')
plt.xlabel('Distance (m)')

if args.name:
    dirn = args.name
else:
    dirn = os.path.basename(args.gpxfile)[:-4]

if not os.path.exists(dirn):
    os.mkdir(dirn)
    copyfile(args.gpxfile, dirn + "/" + os.path.basename(args.gpxfile))
    copyfile(os.path.dirname(TEMPLATE) + "/compass.png", dirn + "/compass.png")
    copyfile(os.path.dirname(TEMPLATE) + "/my.css", dirn + "/my.css")
    copyfile(os.path.dirname(TEMPLATE) + "/pure-min.css", dirn + "/pure-min.css")
    copytree(os.path.dirname(TEMPLATE) + "/leaflet/", "{}/leaflet/".format(dirn))
    if args.imgdir and os.path.isdir(args.imgdir):
        copytree(os.path.dirname(TEMPLATE) + "/js/", "{}/js/".format(dirn))
        copytree(os.path.dirname(TEMPLATE) + "/css/", "{}/css/".format(dirn))
        copytree(os.path.dirname(TEMPLATE) + "/img/", "{}/img/".format(dirn))
        os.mkdir('{}/photos/'.format(dirn))
        copyfile(args.photofile, dirn + "/" + args.photofile)
        with open(dirn + '/photos.txt', 'w') as f:
            f.write(syncphoto(gpx.tracks, args.imgdir))
        for dp, df, fn in os.walk(args.imgdir):
            for f in fn:
                copyfile('{}/{}'.format(dp, f), '{}/photos/{}'.format(dirn, f))
    with open(dirn + "/data.ini", "w") as dataini:
        dataini.write("title={} {}\n".format(os.path.basename(args.gpxfile)[:-4], " ".join(args.desc)))
    plt.savefig(dirn + "/profilo.png", transparent=True)
    with open(dirn + "/index.html", "w") as indexf:
        indexf.write(page.render(inmoto=in_moto, insosta=in_sosta, totale=totale, qminima=qminima, qmassima=qmassima, distanza=distanza, uphill=uphill, downhill=downhill, dislivello=dislivello, fgpx=os.path.basename(args.gpxfile), trackname=" ".join(args.desc), data=data, tipo=tipo, minzoom=minzoom - 1, maxzoom=min(19, minzoom + 3), photofile=args.photofile))

    if args.show:
        Thread(target=webserver, args=(dirn, )).start()
        browser()

else:
    print "Error creating {}/: directory exists".format(dirn)
