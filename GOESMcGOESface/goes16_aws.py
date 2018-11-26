# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 15 Nov 2018
#
#  @author: rhamilton

"""Grab GOES16 data from AWS bucket(s)

Requires AWS credentials in the awsCreds.conf file.
"""

from __future__ import division, print_function, absolute_import

import glob
from os import mkdir
from os.path import basename

from datetime import timedelta as td

import boto3
import botocore


def checkOutDir(outdir):
    """
    """
    # Check if the directory exists, and if not, create it!
    try:
        mkdir(outdir)
    except FileExistsError:
        pass
    except Exception as err:
        # Catch for other (permission?) errors just to be safe for now
        print(str(err))

    flist = sorted(glob.glob(outdir + "/*.nc"))
    flist = [basename(each) for each in flist]

    return flist


def GOESAWSgrab(aws_keyid, aws_secretkey, now, outdir,
                timedelta=6, forceDown=False):
    """
    AWS IAM user key
    AWS IAM user secret key
    Time query is relative to (usually datetime.datetime.utcnow)
    Hours to query back from above
    """
    # AWS GOES bucket location/name
    #  https://registry.opendata.aws/noaa-goes/
    awsbucket = 'noaa-goes16'
    awszone = 'us-east-1'

    # ABI: Advanced Baseline Imager
    # L2: "Level 2" (processed) data
    # CMIPC are the "Cloud & Moisture Imagery CONUS" products
    #   these are derived products based on the "ABI-L1b-Rad*" data
    #   See also: https://www.ncdc.noaa.gov/data-access/satellite-data/goes-r-series-satellites
    inst = "ABI-L2-CMIPC"
    channel = 13

    # Check our output directory for files already downloaded
    donelist = checkOutDir(outdir)

    # Sample key:
    # ABI-L2-CMIPC/2018/319/23/OR_ABI-L2-CMIPC-M3C13_G16_s20183192332157_e20183192334541_c20183192334582.nc

    # Construct the key prefixes between the oldest and the newest
    querybins = []
    for i in range(timedelta, -1, -1):
        delta = td(hours=i)
        qdt = (now - delta).timetuple()

        # Include the year so it works on 1/1 UT
        qyear = qdt.tm_year
        qday = qdt.tm_yday
        qhour = qdt.tm_hour

        ckey = "%s/%04d/%03d/%02d/" % (inst, qyear, qday, qhour)
        querybins.append(ckey)
    # print(querybins)

    s3 = boto3.resource('s3', awszone,
                        aws_access_key_id=aws_keyid,
                        aws_secret_access_key=aws_secretkey)

    try:
        buck = s3.Bucket(awsbucket)
    except botocore.exceptions.ClientError as e:
        # NOTE: Is this the correct exception?  No clue.
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

    matches = []
    for qt in querybins:
        print("Querying:", qt)
        try:
            todaydata = buck.objects.filter(Prefix=qt)

            for objs in todaydata:
                # Current filename
                ckey = basename(objs.key)

                # print("Found %s" % (ckey))

                # Specific filename to search for
                fkey = "OR_%s-M3C%02d_G16" % (inst, channel)

                if ckey.startswith(fkey):
                    # Construct the output filename to save it as
                    oname = ckey.split("_")[4][1:]
                    oname = "%s/%s_C%02d.nc" % (outdir, oname, channel)

                    # Just basename it so we can quickly check to see if
                    #   we already downloaded this file; if so, skip it.
                    boname = basename(oname)
                    if boname not in donelist:
                        matches.append(objs)
                        buck.download_file(objs.key, oname)
                        print("Downloaded: %s" % (oname))
                    else:
                        print(oname, "already downloaded!")
                        if forceDown is True:
                            print("Download forced.")
                            buck.download_file(objs.key, oname)

        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
            else:
                raise

    return matches


# if __name__ == "__main__":
#     outdir = "./GOESMcGOESface/data/"
#     awsconf = "./GOESMcGOESface/awsCreds.conf"
#     creds = parseConfFile(awsconf)

#     aws_keyid = creds['s3_RO']['aws_access_key_id']
#     aws_secretkey = creds['s3_RO']['aws_secret_access_key']

#     when = dt.utcnow()

#     ffiles = main(aws_keyid, aws_secretkey, when, outdir, timedelta=6)

#     print("Found the following files:")
#     for f in ffiles:
#         print(basename(f.key))
