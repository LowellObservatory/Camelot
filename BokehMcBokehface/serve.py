# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 26 Dec 2018
#
#  @author: rhamilton

"""
"""

from __future__ import division, print_function, absolute_import

from collections import OrderedDict

import dctplots.confHerder as ch
import dctplots.dbQueries as dbq
import dctplots.modulePlots as bplot
import dctplots.colorWheelies as cwheels

from bokeh.themes import Theme

import bokeh.server as bs
from tornado.ioloop import PeriodicCallback

from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure, ColumnDataSource


#
#
# Ugh. I can't quite figure out a way to do this without globals. Yet.
#
#
qconff = './config/dbqueries.conf'
mconff = './config/modules.conf'
# 'mods' is a list of ch.moduleConfig objects.
# 'quer' is a list of all the active database sections associated
mods, quer = ch.parser(qconff, mconff)

themefile = "./config/bokeh_dark_theme.yml"
theme = Theme(filename=themefile)

# Get the default color sets; second one is sorted by hue but
#   I'm ditching it since I'm not using it
dset, _ = cwheels.getColors()

# Raw query result dict
qdata = OrderedDict()


def batchQuery():
    """
    It's important to do all of these queries en-masse, otherwise the results
    could end up being confusing - one plot's data could differ by
    one (or several) update cycle times eventually, and that could be super
    confusing and cause users to think that things like coordinates are
    not right when it's really just our view of them that has drifted.

    By doing them all at once or in quick succession, it's more likely
    that we'll capture the same instantaneous 'state' of the telescope/site.
    """
    for iq in quer.keys():
        q = quer[iq]
        query = dbq.queryConstructor(q, dtime=q.rn)
        td = dbq.getResultsDataFrame(q.db.host, query,
                                     q.db.port,
                                     dbuser=q.db.user,
                                     dbpass=q.db.pasw,
                                     dbname=q.db.tabl,
                                     datanames=q.dn)
        qdata.update({iq: td})

    print("%d queries complete!" % (len(qdata)))

    #source.stream() specific data to every plot endpoint now?
    #  ... might work ...
    return qdata

    # Cycle thru each module and generate it
    # for m in mods:
    #     print(m.title)
    #     # Gather up the query data into a single dict so we don't
    #     #   have to encode absolutely everything in every single plot/page
    #     pdata = OrderedDict()
    #     for qtag in m.queries.keys():
    #         pdata.update({qtag: qdata[qtag]})

    #     # A neat party trick:
    #     #   Grab the actual function reference by getting the named
    #     #   attribute of an import (bplot). Then we can call
    #     #   'thingLonger' with the args to actually do it.
    #     try:
    #         thingLonger = getattr(bplot, m.pymodule)
    #     except AttributeError:
    #         print("FATAL ERROR: Module %s not found!" % (m.pymodule))

    #     outfile = m.outname
    #     thingLonger(pdata, themefile, dset, outfile=outfile)


def make_dctweather(doc):
    """
    This is called every time someone visits a pre-defined endpoint;
    see the apps dict in the main calling code for what that actualls is.
    """
    # Hard coding the access/dict key for the data needed for this plot
    #   ... no, I'm not happy about this either.  This is pretty fugly.
    m = mods[0]

    print(m.title)
    # Gather up the query data into a single dict so we don't
    #   have to encode absolutely everything in every single plot/page
    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    # A neat party trick:
    #   Grab the actual function reference by getting the named
    #   attribute of an import (bplot). Then we can call
    #   'thingLonger' with the args to actually do it.
    try:
        thingLonger = getattr(bplot, m.pymodule)
    except AttributeError:
        print("FATAL ERROR: Module %s not found!" % (m.pymodule))

    outfile = m.outname
    fig = thingLonger(pdata, themefile, dset, outfile=outfile)

    doc.theme = theme
    doc.title = m.title
    doc.add_root(fig)

    def grabNew():
        pdata = OrderedDict()
        for qtag in m.queries.keys():
            pdata.update({qtag: qdata[qtag]})

        print("Data reference updated")

    doc.add_periodic_callback(grabNew, 30000)


if __name__ == "__main__":
    apps = {'/dctweather': Application(FunctionHandler(make_dctweather))}

    print("Starting bokeh server...")
    server = Server(apps, port=5000)

    # Do this as a periodic callback?  Need to do it at least once before
    #   we start so we have some data to work with initially
    qdata = batchQuery()

    pcallback = PeriodicCallback(batchQuery, 60000, jitter=0.1)
    pcallback.start()

    server.start()
    server.io_loop.start()
