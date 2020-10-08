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

(Built with ccdproc v2.0.1, so later versions might break stuff)
"""

from pathlib import Path

import numpy as np

import astropy.units as u
from astropy.stats import mad_std

import ccdproc as ccdp
from ccdproc import CCDData
from ccdproc import ImageFileCollection
from ccdproc.utils.slices import slice_from_string


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

        # DCT-specific stuff
        self.mirrorcover = "M1CVR"
        self.instcover = "INSTCVR"

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


def getSingleAmpProperties(amplifierID):
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

    ccdProps = {"binning": "ccdsum",
                "gain": gainkw,
                "readnoise": readkw,
                "x0": pixx0,
                "x1": pixx1,
                "y0": pixy0,
                "y1": pixy1,
                "trimsec": trim,
                "overscan": overscan}

    return ccdProps


def makeMasterCalFrame(calCollection, kwmodel, calPath, outCalName,
                       subOverscan=False, subBias=None, clobber=False):
    """
    Given a ImageFileCollection of (single) amplifier calibration frames,
    combine them into a single file used for calibration.

    If desired, the overscan can be subtracted before combination.
    You might want to do that sometimes?  The logic should mostly work but
    it's basically untested.

    If subBias is None, no bias frame will be subtracted.  If it's not none,
    then the value of subBias is assumed to be a filename of a bias file to
    subtract.  The file must be in calPath.
    """
    allCalFrames = []

    # We just use the generator for the given ImageFileCollection
    for ccds, fname in calCollection.ccds(return_fname=True):
        # Grab some header keywords that we'll need
        ampKeywords = getSingleAmpProperties(ccds.header[kwmodel.ampid])
        fitsOverscan = ccds.header[ampKeywords['overscan']]
        trimreg = ccds.header[ampKeywords['trimsec']]

        # Binning for LMI is always symmetric
        binning = int(ccds.header[ampKeywords['binning']].split(" ")[0])

        if subOverscan is True:
            # We can't just jump in and use the standard ccdp.subtract_overscan
            #   because the LMI definitions of BIASnn keywords skip some
            #   rows, making the image and overscan incompatible shapes.
            #
            # We'll just include everything in the subtract_overscan call,
            #   but we'll record the medianed overscan value for the
            #   originally specified rows for record keeping.  The extra
            #   rows are going to be trimmed out in the very next step so
            #   it's really no biggie.
            #
            # TODO: Figure out if this is still the case with multiamps
            #
            # Remember; these are unbinned coordinates initially and they're
            #   already 1-indexed in the DSP/LOIS
            boty = int(ccds.header[ampKeywords['y0']])
            topy = int(ccds.header[ampKeywords['y1']]/binning)

            oscanslices = slice_from_string(fitsOverscan, fits_convention=True)
            oscanreg = ccds[oscanslices]
            print("Median overscan value: %06d ADU" % np.median(oscanreg))

            # This is for hacking back in the excluded rows
            foparts = fitsOverscan[1:-1].split(",")
            foy = foparts[1].split(":")
            foy = [boty, topy]
            fitsOverscan = "[%s,%s:%s]" % (foparts[0], foy[0], foy[1])
            oscanslices = slice_from_string(fitsOverscan, fits_convention=True)
            oscanreg = ccds[oscanslices]

            # Ok now we can finally call the subtract_overscan function
            osubbed = ccdp.subtract_overscan(ccds, overscan_axis=1,
                                             fits_section=fitsOverscan,
                                             median=True)
        else:
            # Just a rename for convienence in the final trimming below
            osubbed = ccds

        otrimmed = ccdp.trim_image(osubbed, fits_section=trimreg)

        if subBias is not None:
            bfilename = "%s/%s" % (calPath, subBias)
            bframe = CCDData.read(bfilename)
            otrimmed = ccdp.subtract_bias(otrimmed, bframe)

        allCalFrames.append(otrimmed)

    # memLimit is in bytes; if unspecified, default is 16e9 (14.9 GiB)
    memLimit = 3.5e9
    combined_cal = ccdp.combine(allCalFrames,
                                method='average',
                                sigma_clip=True,
                                sigma_clip_low_thresh=5,
                                sigma_clip_high_thresh=5,
                                sigma_clip_func=np.ma.median,
                                sigma_clip_dev_func=mad_std,
                                mem_limit=memLimit)

    combined_cal.meta['combined'] = True
    if subBias is not None:
        combined_cal.meta['biassub'] = True

    outname = "%s/%s" % (calPath, outCalName)
    try:
        # NOTE: 'clobber' is depreciated in astropy 2.x, it's overwrite now
        combined_cal.write(outname, overwrite=clobber)
    except OSError:
        print("%s already exists!" % (outname))


if __name__ == "__main__":
    # These define the images we actually care about
    rawDataPath = "/home/rhamilton/Scratch/20191015/"
    calDataPath = rawDataPath + "/red/"
    basename = "lmi.*.fits"

    # This defines all the keyword types to their actual keyword names
    lmikw = LMIKeywords()

    # For printing out sorting/diagnostic tables at various points
    kwsummarylist = ["file", lmikw.obstype, lmikw.exptime,
                     lmikw.ampid, lmikw.filtv, lmikw.objname,
                     lmikw.ra, lmikw.dec,
                     lmikw.mirrorcover, lmikw.instcover]

    rawData = Path(rawDataPath)
    calData = Path(calDataPath)
    calData.mkdir(exist_ok=True)

    rawFiles = ImageFileCollection(rawData, glob_include=basename)

    # This one is a little weird, the summary property just takes a list.
    #   Also the keywords can't be uppercase?  Janky but whatever.
    summ = rawFiles.summary[kwsummarylist]
    summ.pprint_all()

    # Now comes the ccdproc specific syntax for selecting subsets of the
    #   above rawFiles ImageFileCollection ...
    print("Selecting only the biases ...")

    # We do a little dance because the filter takes a **kwd matching the key
    #   to the value of that key found in the header.
    # NOTE: I'm only selecting the single/usual amplifier here, but it
    #   could be expanded in the future to itterate over all amp combos
    ampAbiasFilter = {lmikw.ampid: "A", lmikw.obstype: 'bias'}
    ampAbiases = rawFiles.filter(**ampAbiasFilter)

    summ = ampAbiases.summary[kwsummarylist]
    summ.pprint_all()

    # Now actually combine all the calibration frame bits
    #
    #   NOTE:
    #   This does it all in memory, so if the images are either large in
    #   size or number your computer might barf.  You can write out the
    #   trimmed biases one by one and then combine those if that's the case.
    #
    makeMasterCalFrame(ampAbiases, lmikw, calDataPath, "biasCombined.fits",
                       subOverscan=False, clobber=True)

    ampAFilterB = {lmikw.ampid: "A", lmikw.obstype: 'dome flat',
                   lmikw.filtv: "B"}
    makeMasterCalFrame(rawFiles.filter(**ampAFilterB), lmikw, calDataPath,
                       "domeflatBCombined.fits",
                       subOverscan=False, subBias="biasCombined.fits",
                       clobber=True)

    ampAFilterV = {lmikw.ampid: "A", lmikw.obstype: 'dome flat',
                   lmikw.filtv: "V"}
    makeMasterCalFrame(rawFiles.filter(**ampAFilterV), lmikw, calDataPath,
                       "domeflatVCombined.fits",
                       subOverscan=False, subBias="biasCombined.fits",
                       clobber=True)

    ampAFilterR = {lmikw.ampid: "A", lmikw.obstype: 'dome flat',
                   lmikw.filtv: "R"}
    makeMasterCalFrame(rawFiles.filter(**ampAFilterR), lmikw, calDataPath,
                       "domeflatRCombined.fits",
                       subOverscan=False, subBias="biasCombined.fits",
                       clobber=True)

    ampAFilterI = {lmikw.ampid: "A", lmikw.obstype: 'dome flat',
                   lmikw.filtv: "I"}
    makeMasterCalFrame(rawFiles.filter(**ampAFilterI), lmikw, calDataPath,
                       "domeflatICombined.fits",
                       subOverscan=False, subBias="biasCombined.fits",
                       clobber=True)

    #
    # At this point I gave up because the dataset I was using was trash;
    #   the dome flats were taken on-sky with basically no movement
    #   so it wasn't worth pursuing any further
    #
