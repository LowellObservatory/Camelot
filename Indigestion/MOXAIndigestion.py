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

from ligmos import utils, workers


def parseMOXA(fname, stupidKeys, metric, expectedFields):
    """
    Just parse the whole damn file one line at a time in one function, so
    I can actually keep track of when the date rollover occurs (if at all).
    """
    # The starting date for this one is the last bit of the filename
    #   We need this because we need to handle the 0 hour rollover ourselves.
    startdate = fname.split(".")[-1]
    startdatedt = dt.datetime.strptime(startdate, "%Y%m%d")
    startdatedt = startdatedt.replace(tzinfo=pytz.UTC)

    headerFound = False
    allpackets = []
    with open(fname) as f:
        for line in f:
            # For NIHTS vacgauge files, ETX (0x03) is at the end of the line.
            #   So kill that silly character
            line = line.replace('\x03', '')

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
                    if len(fields) == expectedFields:
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
    dbconfFile = './dbconf.conf'

    # By doing it this way we ignore the 'enabled' key
    #    but we avoid contortions needed if using
    #    utils.confparsers.parseConfig, so it's worth it
    dbc = utils.confparsers.rawParser(dbconfFile)
    dbs = workers.confUtils.assignConf(dbc['databaseSetup'],
                                       utils.classes.baseTarget,
                                       backfill=True)

    inst = "NIHTS"
    cryodir = "/Users/rhamilton/Scratch/NIHTSCryo/"

    database = utils.database.influxobj(host=dbs.host,
                                        port=dbs.port,
                                        user=dbs.user,
                                        pw=dbs.password,
                                        tablename=dbs.tablename,
                                        connect=True)

    # NOTE: stupidKeys provides a way to rename columns

    # lfiles = sorted(glob(cryodir + "log_NIHTS_Lakeshore218.*"))
    # print("%d LS218 logs found!" % (len(lfiles)))
    # stupidKeys = {"FL SHLD": "FLSHLD",
    #               "DET BRK": "DETBRK",
    #               "BIG FOLD": "BIGFOLD"}
    # metric = "%s_lakeshore218" % (inst.upper())
    # expectedFields = 9

    # lfiles = sorted(glob(cryodir + "log_NIHTS_Lakeshore325.*"))
    # print("%d LS325 logs found!" % (len(lfiles)))
    # stupidKeys = {}
    # metric = "%s_lakeshore325" % (inst.upper())
    # expectedFields = 7

    # lfiles = sorted(glob(cryodir + "log_NIHTS_vacgauge.*"))
    # print("%d vacuum logs found!" % (len(lfiles)))
    # stupidKeys = {"Torr": "Pressure"}
    # metric = "%s_vactransducer_mks972b" % (inst.upper())
    # expectedFields = 2

    # lfiles = sorted(glob(cryodir + "log_NIHTS1_cooler.*"))
    # print("%d Sunpower logs found!" % (len(lfiles)))
    # stupidKeys = {"TempK": "ColdTip", "Meanpow": "Cmdpow"}
    # metric = "%s_sunpowergen2_DetectorCooler" % (inst.upper())
    # expectedFields = 6

    lfiles = sorted(glob(cryodir + "log_NIHTS2_cooler.*"))
    print("%d Sunpower logs found!" % (len(lfiles)))
    stupidKeys = {"TempK": "ColdTip", "Meanpow": "Cmdpow"}
    metric = "%s_sunpowergen2_BenchCooler" % (inst.upper())
    expectedFields = 6

    for lfile in lfiles:
        allpackets = parseMOXA(lfile, stupidKeys, metric, expectedFields)
        if allpackets != []:
            database.singleCommit(allpackets, table=dbs.tablename,
                                  timeprec='ms')
        else:
            print("No valid packets to store in the database!")
