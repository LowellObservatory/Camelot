# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 26 Oct 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import os
from glob import glob
from datetime import datetime as dt

import numpy as np
from PIL import Image
import astropy.io.fits as pyf

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def checkOutDir(outdir):
    """
    """
    # Check if the directory exists, and if not, create it!
    try:
        os.mkdir(outdir)
    except FileExistsError:
        pass
    except Exception as err:
        # Catch for other (permission?) errors just to be safe for now
        print(str(err))


def readFITS(fname, hkeys, dataExtension=0):
    """
    """
    hvals = {}
    hdu = pyf.open(fname)

    for key in hkeys:
        try:
            dext = hdu[dataExtension]
            # Special handling of the datetime one
            if key.lower() == 'date-obs':
                ftime = dt.strptime(dext.header[key],
                                    "%Y-%m-%dT%H:%M:%S.%f")
                hvals.update({key.lower(): ftime})
            else:
                hvals.update({key.lower(): np.float(dext.header[key])})
        except KeyError as err:
            print(str(err))
            hvals.update({key.lower(): None})

    dat = dext.data
    hdu.close()

    return dat, hvals


def assessAll(iloc, oloc, mask, hkeys):
    """
    """
    # Warning, you may explode
    #  https://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.switch_backend
    plt.switch_backend("Agg")

    # Read in the mask; convert to greyscale
    mdata = Image.open(mask)

    # Convert to greyscale and flip it so it can be used with the FITS files
    mdata = np.array(mdata.convert("L").transpose(Image.FLIP_TOP_BOTTOM))

    # Now need to threshold it so it can be used as a segmentation mask easier
    mdata = (mdata > 200)

    avgs = []
    meds = []
    stds = []
    tims = []

    flist = sorted(glob(iloc + "/TARGET*.fit.bz2"))
    # Only do stuff if we actually found some files
    if flist != [] and len(flist) > 1:
        checkOutDir(oloc)

        for i, each in enumerate(flist):
            dat, heds = readFITS(each, hkeys)

            # Mask out the icky stuff
            dat *= mdata

            # Put it into ADU/s
            dat = dat/heds['exptime']
            print(os.path.basename(each), heds['date-obs'])

            if i > 0:
                tims.append(heds['date-obs'])
                # sdat = np.abs(dat - odat)
                sdat = dat - odat

                avgs.append(np.average(sdat))
                stds.append(np.std(sdat))
                meds.append(np.median(sdat))

                plt.imshow(sdat, origin='lower', cmap='Greys_r',
                           vmin=0, vmax=50)

                plt.text(900, 30, ("%s" % (heds['date-obs'])), color='white')
                plt.savefig('./subbed/simg_%04d.png' % (i))
                plt.close()

            odat = dat

        plt.plot(tims, avgs, color='g', label="Avrage")
        plt.plot(tims, meds, color='b', label="Median")
        plt.plot(tims, stds, color='r', label="StdDev")

        # plt.ylim([0, 250])
        # plt.ylim([0, 10])
        # plt.ylim([0, 40])

        # majTicks = mdates.HourLocator(interval=1)
        majTicks = mdates.MinuteLocator(interval=15)
        minTicks = mdates.MinuteLocator(interval=5)
        fmt = mdates.DateFormatter('%m/%d %H:%M')

        plt.gca().xaxis.set_major_locator(majTicks)
        plt.gca().xaxis.set_minor_locator(minTicks)
        plt.gca().xaxis.set_major_formatter(fmt)

        plt.legend()
        plt.savefig("./sky.png")
        plt.close()


if __name__ == "__main__":
    # NOTE: FITS file mask is still hardcoded in the assessAll func!

    inloc = './indata/'
    outloc = './subbed/'
    mask = './dctallsky_mask_dirty.tiff'
    hkeys = ['exptime', 'date-obs', 'tempamb', 'humidity']

    assessAll(inloc, outloc, mask, hkeys)
