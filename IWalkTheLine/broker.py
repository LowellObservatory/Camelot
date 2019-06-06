# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 6 Jun 2019
#
#  @author: rhamilton

"""
"""

from __future__ import division, print_function, absolute_import

from ligmos import utils


def parseBrokerConfig(conffile, passfile, conftype, debug=True):
    """
    """
    # idict: dictionary of parsed config file
    # cblk: common block from config file
    # Read in the configuration file and act upon it
    idict, cblk = utils.confparsers.getActiveConfiguration(conffile,
                                                           conftype=conftype,
                                                           debug=debug)

    # If there's a password file, associate that with the above
    if passfile is not None:
        idict, cblk = utils.confparsers.parsePassConf(passfile, idict,
                                                      cblk=cblk,
                                                      debug=debug)

    return idict, cblk


def setupBroker(idict, cblk, conftype, listener=None):
    """
    """
    # ActiveMQ connection checker
    conn = None

    if cblk.brokertype is not None and\
        cblk.brokertype.lower() == "activemq":
        # Register the listener class for this connection.
        #   This will be the thing that parses packets depending
        #   on their topic name and does the hard stuff!
        # If you don't specify one, the default (print-only) one will be used.
        if listener is None:
            listener = utils.amq.ParrotSubscriber()

    else:
        # No other broker types are defined yet
        pass

    # Collect the activemq topics that are desired
    topics = []
    if conftype is utils.common.brokerCommandingTarget:
        for each in idict:
            topics.append(idict[each].cmdtopic)
            topics.append(idict[each].replytopic)
    elif conftype is utils.common.snoopTarget:
        for each in idict:
            topics.append(idict[each].topics)

        # Flatten the topic list (only good for 2D)
        topics = [val for sub in topics for val in sub]

    # A final downselect to make sure we don't have any duplicates
    topics = list(set(topics))

    # Establish connections and subscriptions w/our helper
    # TODO: Figure out how to fold in broker passwords
    print("Connecting to %s" % (cblk.brokerhost))
    conn = utils.amq.amqHelper(cblk.brokerhost,
                               topics=topics,
                               user=cblk.brokeruser,
                               passw=cblk.brokerpass,
                               port=cblk.brokerport,
                               connect=False,
                               listener=listener)

    return conn, listener
