# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 12 Sep 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import os
import glob
import numpy as np
import datetime as dt

import astropy.io.fits as pyf

from astropy.wcs import WCS
from astropy.visualization import astropy_mpl_style
from astropy.visualization import PercentileInterval, ImageNormalize

from photutils import centroid_com, centroid_2dg

import matplotlib.pyplot as plt


def tstampRobo(header):
    """
    DATE-OBS= '2018/09/12'         / date (yyyy-mm-dd) of observation
    UT      = '05:04:14.895'       / universal time at beginning
    """
    # Get a real timestamp
    date = header['date-obs']
    time = header['ut']
    dstr = "%sT%s" % (date, time)
    tstamp = dt.datetime.strptime(dstr, "%Y/%m/%dT%H:%M:%S.%f")

    return tstamp


def inumRobo(fname):
    """
    Get the image number from a NASACAM robo-created FITS file.
    Robo is dumb and doesn't even give extensions, so the file will look
    something like:

    180912.143

    where the first part is the date (YYMMDD) and the second part is a
    running image number.
    """
    try:
        if os.path.isfile(fname):
            inum = int(os.path.basename(fname).split(".")[-1])
        else:
            inum = -9999
    except Exception as err:
        print("Can't get image number for file %s!" % (fname))
        print(str(err))
        inum = -9999

    return inum


def checkRange(flist, irange, inumfunc):
    numrange = np.arange(irange[0], irange[1]+1)
    inRange = []
    for each in flist:
        inum = inumfunc(each)
        if inum in numrange:
            inRange.append(each)
        else:
            pass

    return inRange


def uniqSets(flist):
    filts = []
    types = []
    objes = []

    # Sanity check scan thru the files
    for each in allfiles:
        try:
            header = pyf.getheader(each)
            cfilts = "%s + %s" % (header['filter1'], header['filter2'])
            filts.append(cfilts)
            types.append(header['imagetyp'])
            objes.append(header['object'])
        except Exception as err:
            print("Can't open thing named: %s" % (each))
            print("It's probably not a FITS file.")
            print(str(err))

    uniqObjects = set(objes)
    uniqImgTyps = set(types)
    uniqFilters = set(filts)

    print("Filter Bands used: ", uniqFilters)
    print("Image types found: ", uniqImgTyps)
    print("Object names found: ", uniqObjects)

    return uniqObjects, uniqImgTyps, uniqFilters


def prepData(fname, pscan, oscan, dnps=True):
    hed = pyf.open(fname)
    # Just a simple FITS file so let's just cut to the chase
    hed = hed[0]
    header = hed.header
    data = hed.data
    regionPrescan = data[:, 0:pscan]
    regionPosscan = data[:, oscan:]
    regionOvrscan = np.hstack((regionPrescan, regionPosscan))
    tdata = data[:, pscan:oscan+1]

    blevel = np.median(regionOvrscan)
    print("\tMedian overscan bias level: %d" % (blevel))

    tdata = tdata - blevel
    if dnps is True:
        tdata /= np.float(header['exptime'])

    return header, tdata


if __name__ == "__main__":
    # Location and file number range of stuff we care about
    inloc = "./20180912/"
    irange1 = [133, 172]
    irange2 = [173, 212]
    # Remember to add more in here as needed
    rangers = [irange1, irange2]

    # Do we want the images in DN/sec?
    dnps = True

    # Stellar locations to track; I could just cull the top N brightest stars
    #   found and track those centroids, but this is quicker (for now)
    #   NOTE: These are in X, Y coordinates (a la DS9) in the TRIMMED image
    #   and not raw frame coordinates! Add pscan to the first element
    #   to get raw frame coordinates (since I'm not trimming at all in Y).
    stars = [
             [595, 607],
             [1384, 417],
             [1721, 450],
             ]
    # Full width & height of cutout box around each star
    cutoutsize = 100

    # Define the pre/over scan ending/starting columns respectively
    #   These are the first/last columns in which there is real data,
    #        ---------->  indexed from 0  <----------
    pscan = 53
    oscan = 2100

    # Get a list of all the junk in the given directory
    flist = sorted(glob.glob(inloc + "/*"))

    # Downselect to only the files we wanted
    fsets = []
    allfiles = []
    for ir in rangers:
        rFiles = checkRange(flist, ir, inumRobo)
        fsets.append(rFiles)
        allfiles += rFiles

    uo, ut, uf = uniqSets(allfiles)

    # Now play with the files in their given chunks defined by the iranges
    for each in fsets:
        # A place to save each star set
        starCentroids = {}
        times = []
        cxseries = np.zeros((len(stars), len(each)))
        cyseries = np.zeros((len(stars), len(each)))

        for i, f in enumerate(each):
            print("%d '%s'" % (i, os.path.basename(f)))
            header, tdata = prepData(f, pscan, oscan, dnps=dnps)

            tstamp = tstampRobo(header)
            if i == 0:
                tstamp0 = tstamp

            print("\t%s" % (tstamp))
            # For later plotting
            times.append((tstamp-tstamp0).total_seconds())
            # For titling
            cfilts = "%s + %s" % (header['filter1'], header['filter2'])

            plt.style.use(astropy_mpl_style)
            norm = ImageNormalize(tdata, interval=PercentileInterval(99.9))
            # For the individual image cutouts
            fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(8, 4),
                                   sharey=True)

            # The actual work
            for j, star in enumerate(stars):
                crad = int(cutoutsize/2.)
                scutout = tdata[star[1]-crad:star[1]+crad,
                                star[0]-crad:star[0]+crad]

                im = ax[j].imshow(scutout, interpolation='none',
                                  origin='lower', norm=norm,
                                  vmin=0, vmax=200)

                # Actually calculate the centroid
                cen = centroid_com(scutout)
                # cen = centroid_2dg(scutout)

                cxseries[j, i] = cen[0]
                cyseries[j, i] = cen[1]

                # Plot the centroid on the image
                ax[j].scatter(cen[0], cen[1], color='green')

                print("\t\tStar%d: %f,%f" % (j, cen[0], cen[1]))

            # cbar = fig.colorbar(im, pad=0.05, orientation='vertical')
            if dnps is True:
                units = "DN/sec"
            else:
                units = "DN"
            # cbar.set_label("%s" % (units))
            # plt.set_title()

            oname = "./pngs/" + os.path.basename(f) + ".png"
            fig.savefig(oname)
            # plt.show(block=True)
            plt.close()

        # Now plot the centroid time series
        fig, ax = plt.subplots(nrows=3, ncols=1, figsize=(14, 12), dpi=300.,
                               sharex=True)
        for i, star in enumerate(stars):
            ax[i].plot(times, cxseries[i]-cxseries[i][0],
                       color='r', label='Centroid X', marker='o', markersize=4)
            ax[i].plot(times, cyseries[i]-cyseries[i][0],
                       color='b', label='Centroid Y', marker='o', markersize=4)
            ax[i].set_ylim([-7.5, 12.5])
            ax[i].set_xlim([-10, 550])
            if i == 0:
                ax[i].legend()

        title = "%s - %s" % (header['object'], cfilts)
        ax[0].set_title(title)
        ax[-1].set_xlabel("Time Elapsed (seconds)")
        ax[1].set_ylabel("Centroid Drift (pixels)")
        oname = "./centroids_%s.png" % (header['object'])
        fig.subplots_adjust(hspace=0.15)
        fig.savefig(oname)
