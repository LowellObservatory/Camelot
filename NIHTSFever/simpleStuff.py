# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 7 Oct 2020
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import glob


import numpy as np
import ccdproc as ccdp

from astropy import units as u
from astropy.stats import mad_std


def medStack(frameList, expNorm=False):
    """
    """
    memLimit = 3.5e9
    combined = ccdp.combine(frameList,
                            method='average',
                            sigma_clip=True,
                            sigma_clip_low_thresh=5,
                            sigma_clip_high_thresh=5,
                            sigma_clip_func=np.ma.median,
                            sigma_clip_dev_func=mad_std,
                            mem_limit=memLimit)

    combined.meta['combined'] = True

    if expNorm is True:
        expTime = float(combined.meta['EXPTIME'])
        combined = combined.divide(expTime * u.second)

    return combined


def quickSubber(callist, arclist, outpath, prefix):
    """
    """
    print("CalList:")
    for each in callist:
        print(each)
    print()
    print("ArcList:")
    for each in arclist:
        print(each)

    combined_cal = medStack(callist, expNorm=True)
    combined_arc = medStack(arclist, expNorm=True)

    combined_sub = combined_arc.subtract(combined_cal)

    outOff = "%s/%s" % (outPath, "%s_comboXeOff.fits" % (prefix))
    outOn = "%s/%s" % (outPath, "%s_comboXeOn.fits" % (prefix))
    sub = "%s/%s" % (outPath, "%s_comboSub.fits" % (prefix))
    try:
        # NOTE: 'clobber' is depreciated in astropy 2.x, it's overwrite now
        combined_cal.write(outOff, overwrite=clobber)
        combined_arc.write(outOn, overwrite=clobber)
        combined_sub.write(sub, overwrite=clobber)
    except OSError as e:
        print(str(e))


def singleSub(f1, f2, outpath, prefix, expNorm=False):
    """
    """
    img1 = ccdp.CCDData.read(f1)
    img2 = ccdp.CCDData.read(f2)
    if expNorm is True:
        expTime1 = float(img1.meta['EXPTIME'])
        expTime2 = float(img2.meta['EXPTIME'])

        img1 = img1.divide(float(expTime1) * u.second)
        img2 = img2.divide(float(expTime2) * u.second)

    sub = img1.subtract(img2)
    outname = "%s/%s" % (outPath, "%s_comboSub.fits" % (prefix))
    try:
        # NOTE: 'clobber' is depreciated in astropy 2.x, it's overwrite now)
        sub.write(outname, overwrite=clobber)
    except OSError as e:
        print(str(e))



if __name__ == "__main__":
    inmask = '*.fits'
    outPath = "./outputs/"
    clobber = True


    on = '/Users/rhamilton/Scratch/nihts/nihts_eng/20200509/20200509.0012.fits'
    off = '/Users/rhamilton/Scratch/nihts/nihts_eng/20200509/20200509.0019.fits'
    sub = singleSub(on, off, outPath, "20200509", expNorm=True)

    inpath = '/Users/rhamilton/Scratch/nihts/nihts_eng/20180822/'
    searcher = inpath + inmask
    inlist = sorted(glob.glob(searcher))
    callist = inlist[12:14]
    arclist = inlist[2:4]
    quickSubber(callist, arclist, outPath, "20180822")

    inpath = '/Users/rhamilton/Scratch/nihts/nihts_eng/20201007a/'
    searcher = inpath + inmask
    inlist = sorted(glob.glob(searcher))
    callist = inlist[0:2]
    arclist = inlist[2:]
    quickSubber(callist, arclist, outPath, "20201007")

    inpath = '/Users/rhamilton/Scratch/nihts/nihts_eng/20201007/'
    searcher = inpath + inmask
    inlist = sorted(glob.glob(searcher))
    arclist = inlist[18:23]
    callist = inlist[23:]
    quickSubber(callist, arclist, outPath, "20201006")
