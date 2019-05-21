# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 17 May 2019
#
#  @author: rhamilton

"""Main loop for GOES-16 reprojection and animation service.
"""

from __future__ import division, print_function, absolute_import

import os
import time
import glob
import subprocess as subp
import configparser as conf
from shutil import copyfile
from datetime import datetime as dt

from ligmos.utils import logs

import nexrad_aws as naws
import plotNEXRAD as pnrad


def parseConfFile(filename):
    """
    """
    try:
        config = conf.SafeConfigParser()
        config.read_file(open(filename, 'r'))
    except IOError as err:
        config = None
        print(str(err))
        return config

    sections = config.sections()
    tsections = ' '.join(sections)

    print("Found the following sections in the configuration file:")
    print("%s\n" % tsections)

    return config


def getFilenameAgeDiff(fname, now, dtfmt="%Y%j%H%M%S%f"):
    """
    NOTE: HERE 'maxage' is already in seconds! Convert before calling.
    """
    # Need to basename it to get just the actual filename and not the path
    beach = os.path.basename(fname)
    try:
        dts = dt.strptime(beach, dtfmt)
        diff = (now - dts).total_seconds()
    except Exception as err:
        # TODO: Catch the right datetime conversion error!
        print(str(err))
        # Make it "current" to not delete it
        diff = 0

    return diff


def clearOldFiles(inloc, fmask, now, maxage=24., dtfmt="%Y%j%H%M%S%f"):
    """
    'maxage' is in hours
    """
    maxage *= 60. * 60.
    flist = sorted(glob.glob(inloc + fmask))

    remaining = []
    for each in flist:
        diff = getFilenameAgeDiff(each, now, dtfmt=dtfmt)
        if diff > maxage:
            print("Deleting %s since it's too old (%.3f hr)" %
                  (each, diff/60./60.))
            try:
                os.remove(each)
            except OSError as err:
                # At least see what the issue was
                print(str(err))
        else:
            remaining.append(each)

    return remaining


def main(outdir, creds, sleep=150., keephours=24.,
         forceDown=False, forceRegen=False):
    """
    'outdir' is the *base* directory for outputs, stuff will be put into
    subdirectories inside of it.

    'keephours' is the number of hours of data to keep on hand. Old stuff
    is deleted to keep things managable
    """
    aws_keyid = creds['s3_RO']['aws_access_key_id']
    aws_secretkey = creds['s3_RO']['aws_secret_access_key']

    dout = outdir + "/raws/"
    pout = outdir + "/pngs/"
    lout = outdir + "/nows/"

    # Filename to copy the last/latest image into for easier web integration
    #   Ok to just hardcopy these since they'll be staticly named
    latestname = '%s/nexradaws_latest.png' % (lout)

    # Need this for parsing the filename into a dt obj
    dtfmt = "KFSX%Y%m%d_%H%M%S"

    # Prepare some things for plotting so we don't have to do it
    #   forever in the main loop body
    rclasses = ["Interstate", "Federal"]

    # On the assumption that we'll plot something, downselect the full
    #   road database into the subset we want
    print("Parsing road data...")
    print("\tClasses: %s" % (rclasses))

    # roads will be a dict with keys of rclasses and values of geometries
    roads = pnrad.parseRoads(rclasses)
    print("Roads parsed!")

    # Construct/grab the color map. It really just returns the pyart one.
    gcmap = pnrad.getCmap()

    print("Starting infinite loop...")
    while True:
        # 'keephours' is time (in hours!) to search for new files relative
        #   to the present.
        #   If they exist, they'll be skipped unless forceDown is True
        when = dt.utcnow()
        print("Looking for files!")
        ffiles = naws.NEXRADAWSgrab(aws_keyid, aws_secretkey, when, dout,
                                    timedelta=keephours, forceDown=forceDown)

        print("Found the following files:")
        for f in ffiles:
            print(os.path.basename(f.key))

        print("Making the plots...")
        # TODO: Return the projection coordinates (and a timestamp of them)
        #   so they can be reused between loop cycles.
        nplots = pnrad.makePlots(dout, pout, roads=roads, cmap=gcmap,
                                 forceRegen=forceRegen)
        print("%03d plots done!" % (nplots))

        # NOTE: I'm literally adding a 'fudge' factor here because the initial
        #   AWS/data query has a resolution of 1 hour, so there can sometimes
        #   be fighting of downloading/deleting/redownloading/deleting ...
        fudge = 1.
        # BUT only do anything if we actually made a new file!
        if nplots > 0:
            dtfmtpng = dtfmt + '.png'
            cpng = clearOldFiles(pout, "*.png", when,
                                 maxage=keephours+fudge, dtfmt=dtfmtpng)
            craw = clearOldFiles(dout, "*", when,
                                 maxage=keephours+fudge, dtfmt=dtfmt)

            print("%d, %d raw and png files remain within %.1f + %.1f hours" %
                  (len(cpng), len(craw), keephours, fudge))

            print("Copying the latest/last files to an accessible spot...")
            # Since they're good filenames we can just sort and take the last
            #   if there are actually any current ones left of course
            nstaticfiles = 48
            if cpng != []:
                if len(cpng) < nstaticfiles:
                    lindex = len(cpng)
                else:
                    lindex = nstaticfiles

                # It's easier to do this via reverse list indicies
                icount = 0
                for findex in range(-1*lindex, 0, 1):
                    try:
                        lname = "%s/nexrad_latest_%03d.png" % (lout, icount)
                        icount += 1
                        copyfile(cpng[findex], lname)
                    except Exception as err:
                        # TODO: Figure out the proper/specific exception
                        print(str(err))
                        print("WHOOPSIE! COPY FAILED")

                # Put the very last file in the last file slot
                latest = cpng[-1]
                try:
                    copyfile(latest, latestname)
                    print("Latest file copy done!")
                except Exception as err:
                    # TODO: Figure out the proper/specific exception to catch
                    print(str(err))
                    print("WHOOPSIE! COPY FAILED")
        else:
            print("No new files downloaded so skipping all actions.")

        print("Sleeping for %03d seconds..." % (sleep))
        time.sleep(sleep)


if __name__ == "__main__":
    outdir = "./outputs/"
    awsconf = "./awsCreds.conf"
    forceDownloads = False
    forceRegenPlot = False
    logname = './logs/radarlove.log'

    # Set up logging (using ligmos' quick 'n easy wrapper)
    logs.setup_logging(logName=logname, nLogs=30)

    creds = parseConfFile(awsconf)

    main(outdir, creds, forceDown=forceDownloads, forceRegen=forceRegenPlot)
    print("Exiting!")
