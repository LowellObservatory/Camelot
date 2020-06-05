# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 19 Sep 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from glob import glob
import datetime as dt

import pytz

from ligmos import utils


def parseMOXA_LS218(fname, inst):
    """
    Just parse the whole damn file one line at a time in one function, so
    I can actually keep track of when the date rollover occurs (if at all).
    """
    # The starting date for this one is the last bit of the filename
    #   We need this because we need to handle the 0 hour rollover ourselves.
    startdate = fname.split(".")[-1]
    startdatedt = dt.datetime.strptime(startdate, "%Y%m%d")
    startdatedt = startdatedt.replace(tzinfo=pytz.UTC)

    # Replace these column labels with non-spaced ones so we can just split()
    stupidKeys = {"FL SHLD": "FLSHLD",
                  "DET BRK": "DETBRK",
                  "BIG FOLD": "BIGFOLD"}

    metric = "%s_lakeshore218" % (inst.upper())

    headerFound = False
    allpackets = []
    with open(fname) as f:
        for line in f:
            # We need to skip any header lines until we find the one that
            #   starts with some spaces and then "UTC" since that's the label
            #   line that we'll need to disentangle
            if line.strip().startswith("UTC"):
                headerFound = True

                # Replace the crappy labels
                for badKey in stupidKeys:
                    line = line.replace(badKey, stupidKeys[badKey])
                labels = line.split()
                print(startdate, labels)
            else:
                if headerFound is True:
                    # Actually parse the guts: a timestamp and 8 sensor temps
                    fields = line.strip().split()
                    if len(fields) == 9:
                        time = fields[0].strip().split(":")
                        lineTime = startdatedt.replace(hour=int(time[0]),
                                                       minute=int(time[1]),
                                                       second=int(time[2]))

                        data = {}
                        for i, each in enumerate(fields):
                            if i == 0:
                                # Convert it to milliseconds for influx
                                #   NOTE: It CAN NOT be a float!
                                #   If we omit ndigits to round() it'll
                                #     return an int
                                ts = lineTime.timestamp()
                                ts = round(ts*1e3)
                            else:
                                try:
                                    data.update({labels[i]: float(each)})
                                except ValueError:
                                    print("Bad value %s in column %d" %
                                          (each, i+1))

                        pkt = utils.packetizer.makeInfluxPacket(meas=[metric],
                                                                fields=data,
                                                                ts=ts)
                        allpackets.append(pkt[0])

    return allpackets


if __name__ == "__main__":
    cryodir = "/Users/rhamilton/Scratch/NIHTSCryo/"

    dbhost = 'dbhost'
    dbport = 8086
    dbuser = None
    dbpass = None
    dbtabl = "moxa_history"
    inst = "NIHTS"

    database = utils.database.influxobj(host=dbhost,
                                        port=dbport,
                                        user=dbuser,
                                        pw=dbpass,
                                        tablename=dbtabl)

    lfiles = sorted(glob(cryodir + "log_NIHTS_Lakeshore218.*"))
    print("%d LS218 logs found!" % (len(lfiles)))

    for lfile in lfiles:
        allpackets = parseMOXA_LS218(lfile, inst)

        database.singleCommit(allpackets, table=database.tablename,
                              timeprec='ms')
