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

import configparser as conf
from datetime import datetime as dt

import boto3
import botocore


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


def main(aws_keyid, aws_secretkey, when):
    """
    """
    # AWS GOES bucket location/name
    #  https://registry.opendata.aws/noaa-goes/
    awsbucket = 'noaa-goes16'

    # s3cli = boto3.client()
    print(aws_keyid)
    print(aws_secretkey)

    year = when.year
    jday = when.timetuple().tm_yday
    inst = "ABI-L2-CMIPC"

    filekey = "%s/%s/%s/" % (inst, year, jday)

    s3 = boto3.resource('s3', 'us-east-1',
                        aws_access_key_id=aws_keyid,
                        aws_secret_access_key=aws_secretkey)

    try:
        buck = s3.Bucket(awsbucket)

        # for objs in buck.objects.all():
        todaydata = buck.objects.filter(Prefix=filekey)

        for objs in todaydata:
            print(objs)
            # buck.download_file(filekey, 'downloaded.nc')

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise


if __name__ == "__main__":
    awsconf = "./GOESMcGOESface/awsCreds.conf"
    creds = parseConfFile(awsconf)

    aws_keyid = creds['s3_RO']['aws_access_key_id']
    aws_secretkey = creds['s3_RO']['aws_secret_access_key']

    when = dt.now()

    main(aws_keyid, aws_secretkey, when)
