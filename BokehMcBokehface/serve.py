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

import datetime as dt
from collections import OrderedDict

import pandas as pd
from pytz import timezone

from bokeh.themes import Theme
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import ColumnDataSource
from bokeh.models import Range1d, LinearAxis, \
                         HoverTool, Legend, LegendItem, \
                         DataTable, TableColumn

from tornado.ioloop import PeriodicCallback

import dctplots.confHerder as ch
import dctplots.dbQueries as dbq
import dctplots.modulePlots as bplot
import dctplots.colorWheelies as cwheels


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

# CDS Sources; easier to keep them globals for now since I'm going down
#   the path (to madness?) of inner functions
cds = ColumnDataSource()


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

    return qdata


def make_dctweather(doc):
    """
    This is called every time someone visits a pre-defined endpoint;
    see the apps dict in the main calling code for what that actualls is.
    """
    # Hard coding the access/dict key for the data needed for this plot
    #   ... no, I'm not happy about this either.  This is pretty fugly.
    m = mods[0]

    print("Serving %s" % (m.title))
    # Gather up the query data into a single dict so we don't
    #   have to encode absolutely everything in every single plot/page
    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    # Setting y1lim to None lets it autoscale based on the data;
    #   Seemed best to keep humidity as 0-100 though.
    y1lim = None
    y2lim = [0, 100]

    # Get the keys that define the input dataset
    #   TODO: make the first defined tag the "primary" meaning X1/Y1 plot
    #         ...but I can't quite figure out the abstraction well enough.
    r = pdata['q_wrs']
    r2 = pdata['q_mounttemp']

    # A dict of helpful plot labels
    ldict = {'title': "WRS Weather Information",
             'xlabel': "Time (UTC)",
             'y1label': "Temperature (C)",
             'y2label': "Humidity (%)"}

    fig = bplot.commonPlot(r, ldict)
    timeNow = dt.datetime.utcnow()
    tWindow = dt.timedelta(hours=24)
    tEndPad = dt.timedelta(hours=1.5)

    # Remember that .min and .max are methods! Need the ()
    #   Also adjust plot extents to pad +/- N percent
    npad = 0.1
    if y1lim is None:
        # Not a typo; make sure that the dewpoint values are always included
        #   since they're always the lowest (and sometimes negative)
        y1lim = [r.DewPoint.values.min(), r.AirTemp.values.max()]

        # Now pad them appropriately, checking for a negative limit
        if y1lim[0] < 0:
            y1lim[0] *= (1.+npad)
        else:
            y1lim[0] *= (1.-npad)

        if y1lim[1] < 0:
            y1lim[1] *= (1.-npad)
        else:
            y1lim[1] *= (1.+npad)

    if y2lim is None:
        # Remember that .min and .max are methods! Need the ()
        y2lim = [r.Humidity.values.min(), r.Humidity.values.max()]
        y2lim = [y2lim[0]*(1.-npad), y2lim[1]*(1.+npad)]

    fig.y_range = Range1d(start=y1lim[0], end=y1lim[1])
    fig.x_range = Range1d(start=timeNow-tWindow, end=timeNow+tEndPad)

    fig.extra_y_ranges = {"y2": Range1d(start=y2lim[0], end=y2lim[1])}
    fig.add_layout(LinearAxis(y_range_name="y2",
                              axis_label=ldict['y2label']), 'right')

    # Hack! But it works. Need to do this *before* you create cds below!
    ix, iy = bplot.makePatches(r, y1lim)

    # The "master" data source to be used for plotting.
    #    I wish there was a way of abstracting this but I'm not
    #    clever enough. Make the dict in a loop using
    #    the data keys? I dunno. "Future Work" for sure.
    mds = dict(index=r.index, AirTemp=r.AirTemp, Humidity=r.Humidity,
               DewPoint=r.DewPoint, MountTemp=r2.MountTemp,
               ix=ix, iy=iy)
    cds = ColumnDataSource(mds)

    # Make the plots/lines!
    l1, _ = bplot.plotLineWithPoints(fig, cds, "AirTemp", dset[0])
    l2, _ = bplot.plotLineWithPoints(fig, cds, "DewPoint", dset[1])
    l3, _ = bplot.plotLineWithPoints(fig, cds, "Humidity", dset[2], yrname="y2")
    l4, _ = bplot.plotLineWithPoints(fig, cds, "MountTemp", dset[3])

    li1 = LegendItem(label="AirTemp", renderers=[l1])
    li2 = LegendItem(label="DewPoint", renderers=[l2])
    li3 = LegendItem(label="Humidity", renderers=[l3])
    li4 = LegendItem(label="MountTemp", renderers=[l4])
    legend = Legend(items=[li1, li2, li3, li4], location='top_left',
                    orientation='horizontal', spacing=15)
    fig.add_layout(legend)

    # HACK HACK HACK HACK HACK
    #   Apply the patches to carry the tooltips
    simg = fig.patches('ix', 'iy', source=cds,
                       fill_color=None,
                       fill_alpha=0.0,
                       line_color=None)

    # Make the hovertool only follow the patches (still a hack)
    htline = simg

    # Customize the active tools
    fig.toolbar.autohide = True

    ht = HoverTool()
    ht.tooltips = [("Time", "@index{%F %T}"),
                   ("AirTemp", "@AirTemp{0.0} C"),
                   ("MountTemp", "@MountTemp{0.0} C"),
                   ("Humidity", "@Humidity %"),
                   ("DewPoint", "@DewPoint{0.0} C"),
                   ]
    ht.formatters = {'index': 'datetime'}
    ht.show_arrow = False
    ht.point_policy = 'follow_mouse'
    ht.line_policy = 'nearest'
    ht.renderers = [htline]
    fig.add_tools(ht)

    #####

    doc.theme = theme
    doc.title = m.title
    doc.add_root(fig)

    def grabNew():
        print("Updating data references!")

        # Get the last timestamp present in the existing ColumnDataSource
        lastTime = cds.data['index'].max()

        # Grab the newest data from the master query dictionary
        pdata = OrderedDict()
        for qtag in m.queries.keys():
            pdata.update({qtag: qdata[qtag]})

        # Update the data references; these are actual DataFrame objects btw.
        r = pdata['q_wrs']
        r2 = pdata['q_mounttemp']

        # Divide by 1000 since it's actually nanoseconds since epoch
        lastTimedt = dt.datetime.utcfromtimestamp(lastTime/1000.)

        # The server timezone has been set (during its setup) to UTC;
        #   we need to specifically add that to avoid timezone shenanigans
        #   because in a prior life we were bad and now must be punished
        storageTZ = timezone('UTC')
        lastTimedt = lastTimedt.replace(tzinfo=storageTZ)

        print("Selecting only data found since %s" % (lastTimedt.isoformat()))

        # Now select only the data in those frames since lastTime
        #   But! Of course there's another caveat.
        # lastTimedt is dt.datetime object, but r.index has a type of
        #   Timestamp which is really a np.datetime64 wrapper. So we need
        #   to put them on the same page for actual comparisons.
        rf = r[r.index.to_pydatetime() > lastTimedt]
        rf2 = r2[r2.index.to_pydatetime() > lastTimedt]

        if rf.size == 0:
            print("No new data! Skipping....")
            return
        else:
            # Update the new hack patches, too
            nix, niy = bplot.makePatches(rf, y1lim)

            # NOTE: y1lim should already have been set by this point since
            #   the callback is called *after* the plot has already initialized
            # ix, iy = bplot.makePatches(r, y1lim)
            mds = dict(index=rf.index, AirTemp=rf.AirTemp,
                       Humidity=rf.Humidity,
                       DewPoint=rf.DewPoint,
                       MountTemp=rf2.MountTemp,
                       ix=nix, iy=niy)

            # Actually update the cds in the plot.
            #   Note that .stream expects a dict, whose keys match those in the
            #   existing ColumnDataSource.
            # If you forget, you'll keep getting an 'AttributeError' because
            #   ColumnDataSource has no 'keys' attribute!
            cds.stream(mds, rollover=5000)
            print("Data reference updated")

    doc.add_periodic_callback(grabNew, 5000)


if __name__ == "__main__":
    # LOOP OVER THE CONFIG TO MAKE THIS; NEED INTERMEDIATE FUNCTIONS FOR
    #   ACTUALLY MAKING THE PLOTS LIKE "make_dctweather" !
    apps = {'/dctweather': Application(FunctionHandler(make_dctweather))}

    print("Starting bokeh server...")
    server = Server(apps, port=5000)

    # Do this as a periodic callback?  Need to do it at least once before
    #   we start so we have some data to work with initially
    qdata = batchQuery()

    # jitter=0.1 means the callback will be called at intervals +/- 10%
    #   to avoid constant clashes with other periodic processes that may be
    #   present and running on the server.
    pcallback = PeriodicCallback(batchQuery, 60000, jitter=0.1)
    pcallback.start()

    server.start()
    server.io_loop.start()
