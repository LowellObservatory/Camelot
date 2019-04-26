# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 12 Apr 2019
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import os
from glob import glob
from datetime import datetime as dt

import numpy as np
from scipy import stats as sp

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

    # Define data saturation threshold (95% or above)
    sthresh = int(65535 * 0.95)

    avgs = []
    meds = []
    stds = []
    tims = []

    flist = sorted(glob(iloc + "/TARGET*.fit.bz2"))
    # Only do stuff if we actually found some files
    if flist != [] and len(flist) > 1:
        checkOutDir(oloc)

        for i, each in enumerate(flist):
            print("Reading %s" % (os.path.basename(each)))
            dat, heds = readFITS(each, hkeys)

            # Mask out the icky stuff
            #   (A better way to do this is with a masked array)
            dat *= mdata

            # Put it into ADU/s
            # dat = dat/heds['exptime']
            # print(os.path.basename(each), heds['date-obs'])
            tims.append(heds['date-obs'])
            plt.imshow(dat, vmin=0, vmax=65535, origin='lower', cmap='Greys_r')
            plt.savefig('./calced/mimg_%04d.png' % (i))
            plt.close()

            # Since we're doing histograms, just flatten the array now
            fdat = np.ndarray.flatten(dat)

            # How many pixels have already been masked/zeroed out?
            nmasked = fdat[fdat == 0]
            print("%d pixels masked/ignored" % (len(nmasked)))

            # How many pixels are above our saturation threshold?
            sdat = fdat[fdat > sthresh]
            fdat[sdat] = 0
            print("%d pixels above %d ADU also ignored" % (len(sdat), sthresh))

            binvals, binedges, patches = plt.hist(fdat,
                                                  # bins=64,
                                                  range=(1, sthresh),
                                                  histtype='step')

            plt.savefig('./calced/hist_%04d.png' % (i))
            plt.close()


if __name__ == "__main__":
    # NOTE: FITS file mask is still hardcoded in the assessAll func!

    inloc = './indata/newset/20181024/'
    outloc = './calced/'
    mask = './dctallsky_mask_dirty.tiff'
    hkeys = ['exptime', 'date-obs', 'tempamb', 'humidity']

    assessAll(inloc, outloc, mask, hkeys)
