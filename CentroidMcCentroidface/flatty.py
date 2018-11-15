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
    inloc = "./20180912/other/"
    irange1 = [36, 44]
    irange2 = [431, 439]
    # Remember to add more in here as needed
    rangers = [irange1, irange2]

    # Do we want the images in DN/sec?
    dnps = True

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
        fstack = []
        for i, f in enumerate(each):
            print("%d '%s'" % (i, os.path.basename(f)))
            header, tdata = prepData(f, pscan, oscan, dnps=dnps)

            fstack.append(tdata)
            tstamp = tstampRobo(header)
            if i == 0:
                tstamp0 = tstamp

            print("\t%s" % (tstamp))
            print("\tRA: %s" % (header['telra']))
            print("\tDEC: %s" % (header['teldec']))
            plt.style.use(astropy_mpl_style)
            norm = ImageNormalize(tdata, interval=PercentileInterval(85))
            plt.imshow(tdata/np.median(tdata),
                       origin='lower', interpolation='none', norm=norm,
                       vmin=0.9, vmax=1.1)
            plt.colorbar()
            plt.show(block=True)
            plt.close()

        # Actually calculate the median
        fstack = np.array(fstack)
        # fmed = np.median(fstack, axis=0)
        fmed = np.sum(fstack, axis=0)
        # Now normalize
        fmed /= np.median(fmed)

        plt.style.use(astropy_mpl_style)
        norm = ImageNormalize(tdata, interval=PercentileInterval(85))
        plt.imshow(fmed, origin='lower', interpolation='none', norm=norm,
                   vmin=0.9, vmax=1.1)
        plt.colorbar()
        plt.show(block=True)
        plt.close()
