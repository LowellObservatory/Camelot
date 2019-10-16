# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 15 Oct 2019
#
#  @author: rhamilton

"""LMI Quick Analysis Tools

Requires the astropy affiliated package ccdproc (as well as astropy).

Collection of things needed for quick and one-off analysis tasks, such as:

- Combining a set of flats/biases
- Bias/flatfielding a set of data
- ???
"""

import os
from pathlib import Path

import matplotlib.pyplot as plt

import astropy.units as u
import astropy.io.fits as pyf

from ccdproc import CCDData
from ccdproc import ImageFileCollection


class LMIKeywords(object):
    def __init__(self):
        """
        The intention here is to use the more generic class property names
        to actually access the real values in the image header, without
        having to know what the actual mapping is yourself.  That looks like:

        CCDData.header[LMIKeywords.namps] --> the value of the number of amps
        """
        # The absolute basics
        self.binning = "CCDSUM"
        self.namps = "NUMAMP"
        self.ampid = "AMPID"
        self.obstype = "OBSTYPE"
        self.imgstart = "DATE-OBS"
        self.exptime = "EXPTIME"
        self.objname = "OBJECT"
        # These are individual wheel positions and their detent status
        self.filt1v = "FILTER1"
        self.filt1s = "F1DETENT"
        self.filt2v = "FILTER2"
        self.filt2s = "F2DETENT"
        # This is the actual ("composite") filter name/setting combined from
        #   both wheels; i.e. "OPEN" + "V" == "V"
        self.filtv = "FILTERS"
        self.ra = "RA"
        self.dec = "DEC"
        self.az = "TELAZ"
        self.alt = "TELALT"
        self.ha = "HA"
        self.zd = "ZD"
        self.za = "ZA"
        self.parangle = "PARANGLE"
        self.lsidtime = "ST"

        # This is just to convert all the keywords to lowercase, because
        #   ccdproc is a little janky and weird with keywords.
        self = convertToLowercase(self)


def convertToLowercase(obj):
    """
    Given a class, step through each keyword and just set the value to the
    .lower() representation; if it's not a string, it just skips.
    """
    for each in obj.__dict__:
        if isinstance(getattr(obj, each), str):
            setattr(obj, each, getattr(obj, each).lower())
        else:
            pass

    return obj


def setSingleAmpProperties(amplifierID):
    aid = amplifierID.lower().strip()
    # Assuming single amplifier reads ... for now
    if aid == "a":
        gainkw = "AGAIN_01"
        readkw = "ARDNS_01"
        pixx0 = "AORGX_01"
        pixx1 = "AENDX_01"
        pixy0 = "AORGY_01"
        pixy1 = "AENDY_01"
        trim = "TRIM01"
        overscan = "BIAS01"
    elif aid == "b":
        gainkw = "AGAIN_02"
        readkw = "ARDNS_02"
        pixx0 = "AORGX_02"
        pixx1 = "AENDX_02"
        pixy0 = "AORGY_02"
        pixy1 = "AENDY_02"
        trim = "TRIM02"
        overscan = "BIAS02"
    elif aid == "c":
        gainkw = "AGAIN_03"
        readkw = "ARDNS_03"
        pixx0 = "AORGX_03"
        pixx1 = "AENDX_03"
        pixy0 = "AORGY_03"
        pixy1 = "AENDY_03"
        trim = "TRIM03"
        overscan = "BIAS03"
    elif aid == "d":
        gainkw = "AGAIN_04"
        readkw = "ARDNS_04"
        pixx0 = "AORGX_04"
        pixx1 = "AENDX_04"
        pixy0 = "AORGY_04"
        pixy1 = "AENDY_04"
        trim = "TRIM04"
        overscan = "BIAS04"

    ccdProps = [gainkw, readkw, pixx0, pixx1, pixy0, pixy1, trim, overscan]

    return ccdProps


def subImgs(imglist):
    """
    """
    if len(imglist) == 2:
        # Subtract the two images and move on
        pass
    elif (len(imglist) % 2) == 0:
        # Do subtractions in sequential pairs ?
        pass


def assembleMasterBias(imglist):
    """
    https://mwcraig.github.io/ccd-as-book/02-04-Combine-bias-images-to-make-master
    combined_bias = ccdp.combine(calibrated_biases,
                             method='average',
                             sigma_clip=True, sigma_clip_low_thresh=5, sigma_clip_high_thresh=5,
                             sigma_clip_func=np.ma.median, sigma_clip_dev_func=mad_std,
                             mem_limit=350e6
                            )
    """

    for file in imglist:
        ccd = CCDData.read(file, unit= u.adu)
        ampid = ccd.header[ampKW]


if __name__ == "__main__":
    # These define the images we actually care about
    rawDataPath = "/home/rhamilton/Scratch/20191015/"
    calDataPath = rawDataPath + "/red/"
    basename = "lmi."
    Vfiles = [51, 53, 55, 57, 58, 60, 62, 64]
    Bfiles = [52, 59]
    Rfiles = [54, 61]
    Ifiles = [56, 63]

    tf = rawDataPath + basename + "%04d" % (1) + ".fits"
    ccdimg = CCDData.read(tf)

    lmikw = LMIKeywords()

    rawData = Path(rawDataPath)
    calData = Path(calDataPath)

    rawFiles = ImageFileCollection(rawData, glob_include=basename+"*.fits")

    # This one is a little weird, the summary property just takes a list.
    #   Also the keywords can't be uppercase?  Janky but whatever.
    summ = rawFiles.summary["file", lmikw.obstype, lmikw.ampid,
                           lmikw.filtv, lmikw.objname]

    summ.pprint_all()

