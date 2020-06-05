# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 3 Jun 2020
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import time
from datetime import datetime as dt

import numpy as np
import xmltodict as xmld
from stomp.listener import ConnectionListener

from ligmos import utils


class domeListener(ConnectionListener):
    def __init__(self):
        """
        ALL listeners need to subclass ConnectionListener.
        The listener will work in it's own thread, and on_message() is called
        for each message on subscribed topics.

        See also:
        https://github.com/LowellObservatory/DataServants/blob/master/dataservants/iago/listener.py
        https://github.com/LowellObservatory/DataServants/blob/master/dataservants/iago/parsetopics.py
        """
        # Grab all the schemas that are in the ligmos library
        # self.schemaDict = utils.amq.schemaDicter()
        self.domeOcculting = "UNKNOWN"

    def on_message(self, headers, body):
        """
        Basically subclassing stomp.listener.ConnectionListener.
        This is called for each and every message from a subscribed topic,
        so don't dilly dally in here!
        """
        # This is used to flag messages that ... well, are bad in some way.
        badMsg = False

        # This is the actual topic name the message came from
        tname = headers['destination'].split('/')[-1].strip()

        # Occasionally, there can be a bit of gibberish due to a network break
        #   or other network gremlin.  So it's best to manually turn the
        #   message bytestring into a regular string.
        try:
            body = body.decode("utf-8")
            badMsg = False
        except UnicodeDecodeError as err:
            print(str(err))
            print("Badness 10000")
            print(body)
            badMsg = True

        if badMsg is False:
            res = {tname: [headers, body]}

            # Wrap everything in a try...except because it'll help catch
            #   and actually handle errors, rather than just crashing out
            try:
                if tname.lower() == "dcs.dcspubdatasv.occultationwarning":
                    # Call your custom parser here
                    val = res[tname][1]
                    if val.lower() == 'true':
                        self.domeOcculting = True
                    else:
                        self.domeOcculting = False
            except Exception as err:
                # Mostly this catches instances where the topic name doesn't
                #   have a valid schema, but it catches all oopsies really.
                # Very helpful for debugging.
                print("="*11)
                print(str(err))
                print(headers)
                print(body)
                print("="*11)


if __name__ == "__main__":
    default_host = 'joe.lowell.edu'
    default_port = 61613
    bigsleep = 2
    sleepstep = 0.5
    fastsleep = 0.1
    confidenceWindow = 5.
    topics = ['DCS.DCSPubDataSV.OccultationWarning']

    print("Setting up listener...")
    listener = domeListener()

    # Use the ligmos ActiveMQ helper function
    conn = utils.amq.amqHelper(default_host,
                               topics,
                               user=None,
                               passw=None,
                               port=default_port,
                               connect=False,
                               listener=listener)

    # This helper class catches various signals; see
    #   ligmos.utils.common.HowtoStopNicely() for details
    runner = utils.common.HowtoStopNicely()

    prevDomeOccult = "UNKNOWN"

    # All LIG codes are run in docker containers so infinite loops are the norm
    while runner.halt is False:
        # Check the actual state of things and do stuff
        if listener.domeOcculting != prevDomeOccult:
            print("Dome Occulting Status has changed!")
            print(dt.utcnow(), listener.domeOcculting)
            if listener.domeOcculting is True:
                print("The dome is potentially occulting")
                print("Entering the fast dome check loop...")

            elif listener.domeOcculting is False and prevDomeOccult is True:
                print("The dome has probably stopped occulting")

            prevDomeOccult = listener.domeOcculting

        # All of these are possibilities of heartbeat failure or success
        #   NOTE: conn.connect() handles ConnectionError exceptions
        if conn.conn is None:
            print("No connection!  Attempting to connect ...")
            conn.connect(listener=listener)
        elif conn.conn.transport.connected is False:
            print("Connection died! Reestablishing ...")
            conn.connect(listener=listener)
        else:
            # You can do other stuff in here, if needed, since this means
            #   that the connection to the broker is A-OK.
            # print("Connection still valid")
            pass

        # Consider taking a big nap
        if runner.halt is False:
            # print("Starting a big sleep")
            # Sleep for bigsleep, but in small chunks to check abort
            for _ in np.arange(0, bigsleep, sleepstep):
                time.sleep(sleepstep)
                if runner.halt is True:
                    break

    # Disconnect from the ActiveMQ broker
    conn.disconnect()
