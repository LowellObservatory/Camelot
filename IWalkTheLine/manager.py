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

from ligmos import utils, workers

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

    # Interval between successive runs of the polling loop (seconds)
    bigsleep = 15

    # Quick renaming to keep line length under control
    malarms = utils.multialarm
    ip = utils.packetizer
    ic = utils.common.brokerCommandingTarget
    udb = utils.database
    listener = listener.MrFreezeCommandConsumer()

    # idict: dictionary of parsed config file
    # cblk: common block from config file
    # args: parsed options of wadsworth.py
    # runner: class that contains logic to quit nicely
    idict, cblk, args, runner = workers.workerSetup.toServeMan(mynameis, conf,
                                                               passes,
                                                               logfile,
                                                               desc=desc,
                                                               extraargs=eargs,
                                                               conftype=ic,
                                                               logfile=False)

    # ActiveMQ connection checker
    conn = None

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Print the preamble of this particular instance
            #   (helpful to find starts/restarts when scanning thru logs)
            utils.common.printPreamble(p, idict)

            conn, crackers = utils.amq.setupBroker(idict, cblk, ic,
                                                   listener=listener)

            # Semi-infinite loop
            while runner.halt is False:

                # Double check that the broker connection is still up
                #   NOTE: conn.connect() handles ConnectionError exceptions
                if conn.conn is None:
                    print("No connection at all! Retrying...")
                    conn.connect(listener=crackers)
                elif conn.conn.transport.connected is False:
                    print("Connection died! Reestablishing...")
                    conn.connect(listener=crackers)
                else:
                    print("Connection still valid")

                # Do some stuff!
                print("Doing some sort of loop ...")
                time.sleep(15.)
                print("Done stuff!")

                print("Cleaning out the queue...")
                # We NEED deepcopy() here to prevent the loop from being
                #   confused by a mutation/addition from the listener
                checkQueue = copy.deepcopy(crackers.brokerQueue)
                print("%d items in the queue" % len(checkQueue.items()))
                if checkQueue != {}:
                    for uuid in checkQueue:
                        print("Processing command %s" % (uuid))
                        print(checkQueue[uuid])
                        print("Removing it from the queue...")
                        crackers.brokerQueue.pop(uuid)

                print("Done queue processing!")
                print("%d items remain in the queue" % len(crackers.brokerQueue.items()))

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

            # Disconnect from the ActiveMQ broker
            conn.disconnect()

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
        utils.common.nicerExit()
