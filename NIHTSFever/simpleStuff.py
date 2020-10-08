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
from astropy.stats import mad_std


def medStack(frameList):
    """
    """
    memLimit = 3.5e9
    combined_cal = ccdp.combine(frameList,
                                method='average',
                                sigma_clip=True,
                                sigma_clip_low_thresh=5,
                                sigma_clip_high_thresh=5,
                                sigma_clip_func=np.ma.median,
                                sigma_clip_dev_func=mad_std,
                                mem_limit=memLimit)

    combined_cal.meta['combined'] = True

    return combined_cal


def subtract():
    """
    """
    pass


if __name__ == "__main__":
    inlist = [""]
    outPath = "./"
    outName = "combo.fits"
    clobber = True

    combined_cal = medStack(inlist)

    outname = "%s/%s" % (outPath, outName)
    try:
        # NOTE: 'clobber' is depreciated in astropy 2.x, it's overwrite now
        combined_cal.write(outname, overwrite=clobber)
    except OSError:
        print("%s already exists!" % (outname))