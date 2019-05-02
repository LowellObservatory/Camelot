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
    r = pdata['q_Rywrs']
    r2 = pdata['q_mounttemp']

    # Join them so the timestamps are sorted for us nicely, and nan's
    #   put into the gaps so we don't get all confused later on
    r = r.join(r2, how='outer')

    # Change F -> C because we're scientists god dammit
    r.AirTemp = (r.AirTemp - 32.) * (5./9.)
    r.DewPoint = (r.DewPoint - 32.) * (5./9.)

    # A dict of helpful plot labels
    ldict = {'title': "WRS Weather Information",
             'xlabel': "Time (UTC)",
             'y1label': "Temperature (C)",
             'y2label': "Humidity (%)"}

    fig = bplot.commonPlot(r, ldict)
    timeNow = dt.datetime.utcnow()
    tWindow = dt.timedelta(hours=13)
    tEndPad = dt.timedelta(hours=1.5)

    # Remember that .min and .max are methods! Need the ()
    #   Also adjust plot extents to pad +/- N percent
    npad = 0.1
    if y1lim is None:
        # Not a typo; make sure that the dewpoint values are always included
        #   since they're always the lowest (and sometimes negative)
        y1lim = [r.DewPoint.min(skipna=True),
                 r.AirTemp.max(skipna=True)]

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
        y2lim = [r.Humidity.min(skipna=True),
                 r.Humidity.max(skipna=True)]
        y2lim = [y2lim[0]*(1.-npad), y2lim[1]*(1.+npad)]

    fig.y_range = Range1d(start=y1lim[0], end=y1lim[1])
    fig.x_range = Range1d(start=timeNow-tWindow, end=timeNow+tEndPad)

    fig.extra_y_ranges = {"y2": Range1d(start=y2lim[0], end=y2lim[1])}
    fig.add_layout(LinearAxis(y_range_name="y2",
                              axis_label=ldict['y2label']), 'right')

    # Make sure that we don't have too awkward of a dataframe by filling gaps
    r.fillna(method='ffill', inplace=True)

    # Hack! But it works. Need to do this *before* you create cds below!
    ix, iy = bplot.makePatches(r.index, y1lim)

    # The "master" data source to be used for plotting.
    #    I wish there was a way of abstracting this but I'm not
    #    clever enough. Make the dict in a loop using
    #    the data keys? I dunno. "Future Work" for sure.
    mds = dict(index=r.index, AirTemp=r.AirTemp, Humidity=r.Humidity,
               DewPoint=r.DewPoint, MountTemp=r.MountTemp,
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
    legend = Legend(items=[li1, li2, li3, li4],
                    location="top_left",
                    orientation='vertical', spacing=15)
    fig.add_layout(legend)

    # Customize the active tools
    fig.toolbar.autohide = True

    # # HACK HACK HACK HACK HACK
    # #   Apply the patches to carry the tooltips
    simg = fig.patches('ix', 'iy', source=cds,
                       fill_color=None,
                       fill_alpha=0.0,
                       line_color=None)

    # Make the hovertool only follow the patches (still a hack)
    htline = simg

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
        timeUpdate = dt.datetime.utcnow()
        print("Checking for new data!")

        # Get the last timestamp present in the existing ColumnDataSource
        lastTime = cds.data['index'].max()

        # Grab the newest data from the master query dictionary
        pdata = OrderedDict()
        for qtag in m.queries.keys():
            pdata.update({qtag: qdata[qtag]})

        # Update the data references; these are actual DataFrame objects btw.
        r = pdata['q_Rywrs']
        r2 = pdata['q_mounttemp']

        # Divide by 1000 since it's actually nanoseconds since epoch
        # lastTimedt = dt.datetime.utcfromtimestamp(lastTime/1000.)
        # NOTE: This is probably not necessary anymore, and all the timestamp
        #   logic can probably be overhauled and simplified since bokeh 1.1.0
        #   seems to be smarter about this sort of thing.
        lastTimedt = lastTime.to_pydatetime()

        # The server timezone has been set (during its setup) to UTC;
        #   we need to specifically add that to avoid timezone shenanigans
        #   because in a prior life we were bad and now must be punished
        # storageTZ = timezone('UTC')
        # lastTimedt = lastTimedt.replace(tzinfo=storageTZ)

        print("Selecting only data found since %s" % (lastTimedt.isoformat()))

        # Now select only the data in those frames since lastTime
        #   But! Of course there's another caveat.
        # lastTimedt is dt.datetime object, but r.index has a type of
        #   Timestamp which is really a np.datetime64 wrapper. So we need
        #   to put them on the same page for actual comparisons.
        rf = r[r.index.to_pydatetime() > lastTimedt]
        rf2 = r2[r2.index.to_pydatetime() > lastTimedt]

        if rf.size == 0 and rf2.size == 0:
            print("No new data.")
        else:
            # Prune out stuff we don't want/care about anymore.
            #   If there are columns that end up in 'nf' below that aren't
            #   already in the main CDS, Bokeh will barf/the plot won't update.
            rf = rf.drop("WindDir2MinAvg", axis=1)
            rf = rf.drop("WindSpeed2MinAvg", axis=1)

            rf.AirTemp = (rf.AirTemp - 32.) * (5./9.)
            rf.DewPoint = (rf.DewPoint - 32.) * (5./9.)

            # Now join the dataframes into one single one that we can stream.
            #   Remember to use 'outer' otherwise information will be
            #   mutilated since the two dataframes are on two different
            #   time indicies!
            nf = rf.join(rf2, how='outer')

            # Update the new hack patches, too. Special handling for the case
            #   where we just have one new point in time, since
            #   makePatches assumes that you give it enough to sketch out
            #   a box.  It could be changed so it makes the last box the full
            #   xwidth, and that it's .patch()'ed on update here to always be
            #   correct.  But, that's a little too complicated for right now.
            numRows = nf.shape[0]
            if numRows == 1:
                print("Single row!")
                nidx = [lastTimedt, nf.index[-1]]
                nix, niy = bplot.makePatches(nidx, y1lim)
                ndf = pd.DataFrame(data={'ix': nix, 'iy': niy},
                                   index=[nf.index[-1]])
            else:
                print("Multirow!")
                nix, niy = bplot.makePatches(nf.index, y1lim)
                ndf = pd.DataFrame(data={'ix': nix, 'iy': niy},
                                   index=nf.index)

            nf = nf.join(ndf, how='outer')
            # nf.fillna(method='ffill', inplace=True)

            # Actually update the cds in the plot.
            #   We can just stream a DataFrame! Makes life easy.
            cds.stream(nf, rollover=5000)
            print("New data streamed; %d row(s) added" % (numRows))

        # Update the X range, at least, to show that we're still moving
        print("Adjusted plot x-range.")
        fig.x_range = Range1d(start=timeUpdate-tWindow,
                              end=timeUpdate+tEndPad)
        print("")

    doc.add_periodic_callback(grabNew, 5000)


if __name__ == "__main__":
    # LOOP OVER THE CONFIG TO MAKE THIS; NEED INTERMEDIATE FUNCTIONS FOR
    #   ACTUALLY MAKING THE PLOTS LIKE "make_dctweather" !
    apps = {'/dctweather': Application(FunctionHandler(make_dctweather))}

    print("Starting bokeh server...")
    server = Server(apps, port=5000,
                    allow_websocket_origin=['localhost:5000',
                                            'dctsleeperservice:5000'])

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
