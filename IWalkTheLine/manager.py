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

import os
import sys
import copy
import time

from pid import PidFile, PidFileError

from ligmos.utils import amq, common, classes
from ligmos.workers import workerSetup, connSetup

import listener


if __name__ == "__main__":
    # For PIDfile stuff; kindly ignore
    mynameis = os.path.basename(__file__)
    if mynameis.endswith('.py'):
        mynameis = mynameis[:-3]
    pidpath = '/tmp/'

    # Define the default files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    conf = './queue.conf'
    passes = './passwords.conf'
    logfile = './queueDev.log'
    desc = "I Walk The Line: Experimenting with queues"
    eargs = None
    conftype = classes.brokerCommandingTarget
    amqlistener = listener.MrFreezeCommandConsumer()

    # Interval between successive runs of the polling loop (seconds)
    bigsleep = 15

    # config: dictionary of parsed config file
    # comm: common block from config file
    # args: parsed options
    # runner: class that contains logic to quit nicely
    config, comm, args, runner = workerSetup.toServeMan(mynameis, conf,
                                                        passes,
                                                        logfile,
                                                        desc=desc,
                                                        extraargs=eargs,
                                                        conftype=conftype,
                                                        logfile=True)

    # ActiveMQ connection checker
    conn = None

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Print the preamble of this particular instance
            #   (helpful to find starts/restarts when scanning thru logs)
            common.printPreamble(p, config)

            # Specify our custom listener that will really do all the work
            #   Since we're hardcoding for the DCTConsumer anyways, I'll take
            #   a bit shortcut and hardcode for the DCT influx database.
            # TODO: Figure out a way to create a dict of listeners specified
            #   in some creative way. Could add a configuration item to the
            #   file and then loop over it, and change connAMQ accordingly.
            amqtopics = amq.getAllTopics(config, comm)
            amqs = connSetup.connAMQ(comm, amqtopics, amqlistener=amqlistener)

            # Just hardcode this for now. It's a prototype!
            conn = amqs['broker-dct'][0]

            # Semi-infinite loop
            while runner.halt is False:
                # Check on our connections
                amqs = amq.checkConnections(amqs, subscribe=True)

                # Double check that the broker connection is still up
                #   NOTE: conn.connect() handles ConnectionError exceptions
                if conn.conn is None:
                    print("No connection at all! Retrying...")
                    conn.connect(listener=amqlistener)
                elif conn.conn.transport.connected is False:
                    print("Connection died! Reestablishing...")
                    conn.connect(listener=amqlistener)
                else:
                    print("Connection still valid")

                # Do some stuff!
                print("Doing some sort of loop ...")
                time.sleep(15.)
                print("Done stuff!")

                print("Cleaning out the queue...")
                # We NEED deepcopy() here to prevent the loop from being
                #   confused by a mutation/addition from the listener
                checkQueue = copy.deepcopy(amqlistener.brokerQueue)
                print("%d items in the queue" % len(checkQueue.items()))
                if checkQueue != {}:
                    for uuid in checkQueue:
                        print("Processing command %s" % (uuid))
                        print(checkQueue[uuid])
                        print("Removing it from the queue...")
                        amqlistener.brokerQueue.pop(uuid)

                print("Done queue processing!")
                print("%d items remain in the queue" % len(amqlistener.brokerQueue.items()))

                # Consider taking a big nap
                if runner.halt is False:
                    print("Starting a big sleep")
                    # Sleep for bigsleep, but in small chunks to check abort
                    for _ in range(bigsleep):
                        time.sleep(0.5)
                        if runner.halt is True:
                            break

            # The above loop is exited when someone sends SIGTERM
            print("PID %d is now out of here!" % (p.pid))

            # Disconnect from all ActiveMQ brokers
            amq.disconnectAll(amqs)

            # The PID file will have already been either deleted/overwritten by
            #   another function/process by this point, so just give back the
            #   console and return STDOUT and STDERR to their system defaults
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            print("Archive loop completed; STDOUT and STDERR reset.")
    except PidFileError:
        # We've probably already started logging, so reset things
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        print("Already running! Quitting...")
        common.nicerExit()
