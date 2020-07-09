#!/usr/bin/python
from __future__ import division
import gpxpy
import argparse
import sys
import os
import datetime
import pytz
import exifread
from PIL import Image
import matplotlib.pyplot as plt
import webbrowser
import SimpleHTTPServer
import BaseHTTPServer
import time
import math
from shutil import copyfile, copytree
from threading import Thread
from jinja2 import Environment, FileSystemLoader

TEMPLATE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'mappina/template.html')
env = Environment(loader=FileSystemLoader(os.path.dirname(TEMPLATE)))
page = env.get_template(os.path.basename(TEMPLATE))


server_stop = False
do_later = False


def show(directory, server_class=BaseHTTPServer.HTTPServer, handler_class=SimpleHTTPServer.SimpleHTTPRequestHandler):
    PORT = 6655
    os.chdir(directory)
    server_address = ('localhost', PORT)
    httpd = server_class(server_address, handler_class)
    count = 0
    nfiles = 0
    browser()
    for d, p, f in os.walk('.'):
        nfiles += len(f)
    while count < nfiles + 1:
        count += 1
        httpd.handle_request()


def browser():
    try:
        webbrowser.open('http://127.0.0.1.nip.io:6655')
    except Exception:
        print('Problem opening web browser. Point your browser to http://127.0.0.1.nip.io:6655')


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


def exif_time(pto, path):
    DT_TAGS = ["Image DateTime", "EXIF DateTimeOriginal", "DateTime"]
    photo_time = datetime.datetime.now()
    with open(os.path.join(path, pto), 'rb') as f:
        tags = exifread.process_file(f, details=False)
        for dt_tag in DT_TAGS:
            try:
                dt_value = "{}".format(tags[dt_tag])
                break
            except Exception:
                dt_value = False
                continue
        if dt_value:
            photo_time = datetime.datetime.strptime(dt_value, '%Y:%m:%d %H:%M:%S')
            localtz = pytz.timezone('Europe/Rome')
            local_dt = localtz.localize(photo_time)
            photo_time = local_dt.astimezone(pytz.utc)
    print(photo_time)
    return photo_time.replace(tzinfo=None)


def syncphoto(tracks, directory):
    timepoints = []
    for track in tracks:
        for segment in track.segments:
            for point in segment.points:
                timepoints.append([point.time, point.latitude, point.longitude])
    imgfiles = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    output = [['lat', 'lon', 'title', 'description'], ]
    for f in imgfiles:
        print(f)
        ptime = exif_time(f, directory)
        print(ptime.replace(tzinfo=None))
        idx = timepoints.index(min(timepoints, key=lambda x: abs(x[0].replace(tzinfo=None) - ptime)))
        output.append([str(timepoints[idx][1]), str(timepoints[idx][2]), f, '<a data-lightbox="{0}" href="photos/{0}"><img width="200px" src="photos/{0}" /></a>'.format(f)])
    return ''.join(['\t'.join(i) + '\n' for i in output])


def resize(img_in, img_out, basewidth):
    img = Image.open(img_in)
    wpercent = basewidth / img.size[0]
    hsize = int(img.size[1] * wpercent)
    print('resizing {} to {} with size ({},{})'.format(img_in, img_out, basewidth, hsize))
    img.resize((basewidth, hsize), Image.ANTIALIAS)
    img.save(img_out)


def main():
    parser = argparse.ArgumentParser(description='Starting from a gpx, creates an html file with map, elevation profile and timings')

    parser.add_argument('gpxfile', metavar='GPX', type=str, help="Name of the GPX File")
    parser.add_argument('-n', '--name', type=str, help="Name of the output directory")
    parser.add_argument('-d', '--desc', nargs='+', help='Description of Track', required=True)
    parser.add_argument('--show', help="Shows in local browser", action="store_true")
    parser.add_argument('-i', '--imgdir', help="path of directory containing photos to be placed on map", type=str)
    args = parser.parse_args()

    try:
        gpx = gpxpy.parse(open(args.gpxfile))
    except IOError:
        print("IO Error: invalid file name {}".format(args.gpxfile))
        sys.exit(-1)
    except gpxpy.gpx.GPXXMLSyntaxException:
        print("Invalid gpx file format")
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

    if os.path.exists(dirn):
        print("Error creating {}/: directory exists. Remove or rename it".format(dirn))
        if not args.show:
            sys.exit(1)
    else:
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
            with open(dirn + '/photos.txt', 'w') as f:
                f.write(syncphoto(gpx.tracks, args.imgdir))
            for dp, df, fn in os.walk(args.imgdir):
                for f in fn:
                    resize('{}/{}'.format(dp, f), '{}/photos/{}'.format(dirn, f), 1024)
        with open(dirn + "/data.ini", "w") as dataini:
            dataini.write("title={} {}\n".format(os.path.basename(args.gpxfile)[:-4], " ".join(args.desc)))
        plt.savefig(dirn + "/profilo.png", transparent=True)
        with open(dirn + "/index.html", "w") as indexf:
            indexf.write(page.render(inmoto=in_moto, insosta=in_sosta, totale=totale, qminima=qminima, qmassima=qmassima, distanza=distanza, uphill=uphill, downhill=downhill, dislivello=dislivello, fgpx=os.path.basename(args.gpxfile), trackname=" ".join(args.desc), data=data, tipo=tipo, minzoom=minzoom - 1, maxzoom=min(19, minzoom + 3), photofile='photos.txt'))

    if args.show:
        t = Thread(target=show, args=(dirn, ))
        t.daemon = True
        t.start()
        try:
            time.sleep(100)
        except KeyboardInterrupt:
            print('Closing webserver...')
        else:
            print('Automatically closing webserver after 100secs of availability...')
        sys.exit(0)


if __name__ == '__main__':
    main()
