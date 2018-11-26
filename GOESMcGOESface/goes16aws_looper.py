# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 26 Nov 2018
#
#  @author: rhamilton

"""Main loop for GOES-16 reprojection and animation service.
"""

from __future__ import division, print_function, absolute_import

import time
import configparser as conf
from os.path import basename
from datetime import datetime as dt

import goes16_aws as gaws
import plotGOES as pgoes


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


def main(outdir, creds, sleep=300., forceDown=False, forceRegen=False):
    """
    outdir is the *base* directory for outputs, stuff will be put into
    subdirectories inside of it.
    """
    aws_keyid = creds['s3_RO']['aws_access_key_id']
    aws_secretkey = creds['s3_RO']['aws_secret_access_key']

    dout = outdir + "/raws/"
    pout = outdir + "/pngs/"
    while True:
        # Time (in hours!) to search for new files relative to the present
        #   If they exist, they'll be skipped unless forceRegen is True
        tdelta = 3
        forceDown = False

        when = dt.utcnow()
        print("Looking for files!")
        ffiles = gaws.GOESAWSgrab(aws_keyid, aws_secretkey, when, dout,
                                  timedelta=tdelta, forceDown=forceDown)

        print("Found the following files:")
        for f in ffiles:
            print(basename(f.key))

        print("Making the plots...")
        pgoes.makePlots(pout, forceRegen=forceRegen)

        time.sleep(sleep)


if __name__ == "__main__":
    outdir = "./outputs/"
    awsconf = "./awsCreds.conf"
    creds = parseConfFile(awsconf)
    forceDownloads = False
    forceRegenPlot = False

    print("Starting infinite loop...")
    main(outdir, creds, forceDown=forceDownloads, forceRegen=forceRegenPlot)
    print("Exiting!")
