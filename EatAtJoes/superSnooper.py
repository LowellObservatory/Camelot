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

from ligmos import utils


def main(brokerHost, topics, brokerPort=61613):
    """
    """
    bigsleep = 30

    print("Setting up listener...")
    listener = utils.amq.ParrotSubscriber(dictify=False)

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
