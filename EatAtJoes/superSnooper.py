# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 12 Nov 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import time

import stomp
import xmltodict as xmld

from ligmos import utils


class joeListener(stomp.listener.ConnectionListener):
    """
    """
    def __init__(self, dictify=True):
        self.dictify = dictify

    # Subclassing stomp.listener.ConnectionListener
    def on_message(self, headers, body):
        tname = headers['destination'].split('/')[-1]
        # Manually turn the bytestring into a string
        try:
            body = body.decode("utf-8")
            badMsg = False
        except Exception as err:
            print(str(err))
            print("Badness 10000")
            print(body)
            badMsg = True

        if badMsg is False:
            try:
                if self.dictify is True:
                    xml = xmld.parse(body)
                    res = {tname: [headers, xml]}
                else:
                    # If we want to have the XML as a string:
                    res = {tname: [headers, body]}
            except xmld.expat.ExpatError:
                # This means that XML wasn't found, so it's just a string
                #   packet with little/no structure. Attach the sub name
                #   as a tag so someone else can deal with the thing
                res = {tname: [headers, body]}
            except Exception as err:
                # This means that there was some kind of transport error
                #   or it couldn't figure out the encoding for some reason.
                #   Scream into the log but keep moving
                print("="*42)
                print(headers)
                print(body)
                print("="*42)
                badMsg = True

        print("Message Source: %s" % (tname))
        print("Message Headers:", headers)
        if badMsg:
            print("Header: %s" % (headers))
            print("Body: %s" % (body))
        else:
            if self.dictify is True:
                print(res)
            else:
                print(body)


def main(brokerHost, topics, brokerPort=61613):
    """
    """
    bigsleep = 30

    print("Setting up listener...")
    listener = joeListener(dictify=False)

    conn = utils.amq.amqHelper(brokerHost,
                               topics,
                               user=None,
                               passw=None,
                               port=brokerPort,
                               connect=False,
                               listener=listener)

    first = True
    while True:
        # Double check that the connection is still up
        #   NOTE: conn.connect() handles ConnectionError exceptions
        if conn.conn is None:
            print("No connection at all! Retrying...")
            conn.connect(listener=listener)
        elif conn.conn.transport.connected is False and first is False:
            # Added the "first" flag to take care of a double sub. bug
            print("Connection died! Reestablishing...")
            conn.connect(listener=listener)
        else:
            print("Connection still valid")

        print("Starting a big sleep")
        # Sleep for bigsleep, but in small chunks to check abort
        for i in range(bigsleep):
            time.sleep(1)
        first = False

    # Disconnect from the ActiveMQ broker
    conn.disconnect()


if __name__ == "__main__":
    tlist = ['joeCommand',
             'joeGuiderActions', 'joeGuiderDeltaLimit', 'joeGuiderDeltas',
             'joeHeartbeat',
             'joeoms.Command',
             'joeoms.lmi.CommandResult', 'joeoms.rc1.CommandResult',
             'joePdu', 'joePduResult',
             'joeReply', 'joeReplyBroadcast',
             'joeRequest', 'joeStage', 'joeStageResult',
             'joetcs.Command', 'joetcs.CommandResult']

    # dbname = "DCTInfo"
    dbname = None
    brokerHost = 'joe.lowell.edu'

    main(brokerHost, tlist)
