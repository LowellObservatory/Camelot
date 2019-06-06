# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 6 Jun 2019
#
#  @author: rhamilton

"""Sends random requests to the given .cmd topic to test queue management.
"""

from __future__ import division, print_function, absolute_import

import time
import random
from collections import OrderedDict

import xmltodict as xmld

from ligmos import utils

import broker


def constructCMDPacket(cmdset, debug=False):
    """
    cmdset should be a list of dicts
    """
    if not isinstance(cmdset, list):
        print("cmdset must be a list of dicts! Aborting.")
        return None

    dPacket = OrderedDict()
    rootTag = "MrFreezeCommand"

    allcmds = {}
    for each in cmdset:
        allcmds.update(each)

    dPacket.update({rootTag: allcmds})
    xPacket = xmld.unparse(dPacket)
    if debug is True:
        print(xmld.unparse(dPacket, pretty=True))

    return xPacket


if __name__ == "__main__":
    # Define the default config files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    conf = './queue.conf'
    passes = './passwords.conf'
    # This defines the subclass that is filled by the confparser functions
    #   IT IS SITUATIONAL DEPENDENT!
    conftype = utils.common.brokerCommandingTarget

    # Actually parse the files and set stuff up
    idict, cblk = broker.parseBrokerConfig(conf, passes, conftype, debug=True)
    conn, crackers = broker.setupBroker(idict, cblk, conftype,
                                        listener=utils.amq.silentSubscriber())

    # Now that we have all of this, the final product will have command line
    #   switches that link commands to the actions; since this is just a test
    #   we need to do a little dance to set things up better for testing
    #   and actually just loop over the specified actor
    actors = {"MrFreezeControl": ["LMISunpowerSetpoint",
                                  "DeVenySunpowerSetpoint",
                                  "DeVenySunpowerPowerMin",
                                  "DeVenySunpowerPowerMax"]}

    # These will ultimately come from the command line input
    commandkey = "LMISunpowerSetpoint"
    commandval = 101.0

    # Find which actor has the desired commandkey and set it up
    commandTopic = None
    replyTopic = None
    for act in actors:
        if commandkey in actors[act]:
            commandTopic = idict[act].cmdtopic
            replyTopic = idict[act].replytopic

    # Now we're all set. In the final version this will just be a single-shot
    #   call, but again, we're testing here!
    while True:
        sleepTime = random.randint(10, 40)
        cmd2 = {commandkey: commandval}

        packet = constructCMDPacket([cmd2], debug=True)

        print("Sending test message...")
        conn.connect(listener=crackers, subscribe=False)
        conn.publish(commandTopic, packet, debug=True)
        conn.disconnect()

        print("Sleeping for %d seconds" % (sleepTime))
        time.sleep(sleepTime)
