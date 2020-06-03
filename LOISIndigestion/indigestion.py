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

import os
import datetime as dt

import matplotlib.pyplot as plt


def parseWholeFile(fname):
    """
    Just parse the whole damn file one line at a time in one function, so
    I can actually keep track of when the date rollover occurs (if at all).
    """
    # The starting date for this one is the last bit of the filename
    #   We need this because we need to handle the 0 hour rollover ourselves.
    startdate = fname.split(".")[-1]
    startdatedt = dt.datetime.strftime(startdate, "%Y%M%D")

    dateRollover = False
    with open(lfile) as f:
        for line in f:
            # print(line)
            ltime = msg[0:8].split(":")

            # Bail early since this indicates it's not really a log line but
            #   some other type of message (like a LOIS startup or something)
            if len(ltime) != 3:
                print("Unknown log line!")
            else:
                # This means we found a valid timestamp
                #
                # CONTINUE HERE
                pass


def parseLOISTemps(msg, startdate):
    """
    A SLIGHTLY DIFFERENT COPY OF THIS STUPID FUNCTION
    """
    # print(ts, msg)
    # Some time shenanigans; the LOIS log doesn't include date but
    #   we can assume it's referencing UT time on the same day.
    #   I suppose that there could be some ambiguity right at UT midnight
    #   ... but oh well.
    now = dt.datetime.strftime(startdate, "%Y%M%D")
    ltime = msg[0:8].split(":")

    # Bail early since this indicates it's not really a log line but
    #   some other type of message (like a LOIS startup or something)
    if len(ltime) != 3:
        print("Unknown log line!")
        print(msg)
        return

    now = now.replace(hour=int(ltime[0]), minute=int(ltime[1]),
                      second=int(ltime[2]), microsecond=0)

    decimalTime = ((int(ltime[2])/60. + int(ltime[1]))/60.) + int(ltime[0])

    # Get just the log level
    loglevel = msg.split(" ")[1].split(":")[0]
    # Now get the message, putting back together anything split by ":"
    #   this is so we can operate fully on the full message string
    logmsg = " ".join(msg.split(":")[3:]).strip()

    fields = {}
    if loglevel in ["Level_5", "Level_4"]:
        if logmsg.startswith("CCD sensor adus"):
            # print("Parsing: %s" % (logmsg))
            # CCD sensor adus temp1 2248 temp2 3329 set1 2249 heat1 2016'
            adutemp1 = int(logmsg.split(" ")[4])
            adutemp2 = int(logmsg.split(" ")[6])
            aduset1 = int(logmsg.split(" ")[8])
            aduheat1 = int(logmsg.split(" ")[10])

            fields = {"aduT1": adutemp1}
            fields.update({"DecimalTime": decimalTime})
            fields.update({"aduT2": adutemp2})
            fields.update({"aduT2": adutemp2})
            fields.update({"aduS1": aduset1})
            fields.update({"aduH1": aduheat1})

            # print(adutemp1, adutemp2, aduset1, aduheat1)
        elif logmsg.startswith("CCD Heater"):
            # NOTE! This one will have had a ":" removed by the
            #   logmsg creation line above, so you can just split normally
            # print("Parsing: %s" % (logmsg))
            # CCD Heater Values:1.21 0.00
            heat1 = float(logmsg.split(" ")[3])
            heat2 = float(logmsg.split(" ")[4])

            fields = {"H1": heat1}
            fields.update({"DecimalTime": decimalTime})
            fields.update({"H2": heat2})

            # print(heat1, heat2)
        elif logmsg.startswith("CCD Temp"):
            # Same as "CCD Heater" in that ":" have been removed by this point
            # print("Parsing: %s" % (logmsg))
            # CCD Temp -110.06 18.54 Setpoints -109.95 0.00 '
            temp1 = float(logmsg.split(" ")[2])
            temp2 = float(logmsg.split(" ")[3])
            set1 = float(logmsg.split(" ")[5])
            set2 = float(logmsg.split(" ")[6])

            fields = {"T1": temp1}
            fields.update({"DecimalTime": decimalTime})
            fields.update({"T2": temp2})
            fields.update({"S1": set1})
            fields.update({"S2": set2})
            fields.update({"T1S1delta": temp1-set1})

            # print(temp1, temp2, set1, set2)
        else:
            fields = {}
            # print(loglevel, logmsg)

    return fields


if __name__ == "__main__":
#    lfile = "lois_log.obs42.20190919"
    lfile = "logs/lois_log.obs42.20180117"

    t1t = []
    t1v = []
    t2t = []
    t2v = []

    # The starting date for this one is the last bit of the filename
    #   We need this because we need to handle the 0 hour rollover ourselves.
    startdate = lfile.split(".")[-1]

    with open(lfile) as f:
        for line in f:
            # print(line)
            fields = parseLOISTemps(line, startdate)
            if fields is not None:
                if "T1" in fields.keys():
                    t1t.append(fields["DecimalTime"])
                    t1v.append(fields['T1'])
                if "T2" in fields.keys():
                    t2t.append(fields["DecimalTime"])
                    t2v.append(fields['T2'])

            print(fields)

    ax = plt.axes()
    linet1 = ax.plot(t1v, color='r', label="T1")
    ax.set_ylim([25, -100])
    ax.set_ylabel("T1 (red)")
    ax2 = ax.twinx()
    linet2 = ax2.plot(t2v, color='b', label='T2')
    ax2.set_ylim([25, -180])
    ax2.set_ylabel("T2 (blue)")
    plt.tight_layout()
    plt.legend([linet1, linet2])
    plt.show()
