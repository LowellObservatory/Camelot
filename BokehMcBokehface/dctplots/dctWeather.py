# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 6 May 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import datetime as dt
from collections import OrderedDict

import numpy as np
import pandas as pd
from pytz import timezone

from bokeh.plotting import ColumnDataSource
from bokeh.models import DataRange1d, LinearAxis, \
                         HoverTool, Legend, LegendItem

from . import modulePlots as bplot

def getLastVal(cds, cdstag):
    """
    """
    # Default/failsafe value
    fVal = np.nan

    try:
        # This means that the data are a pandas Series
        fVal = cds.data[cdstag].values[-1]
    except AttributeError:
        # This means that the data are really just an array now
        fVal = cds.data[cdstag][-1]

    return fVal


def make_plot(doc):
    """
    This is called every time someone visits a pre-defined endpoint;
    see the apps dict in the main calling code for what that actualls is.
    """
    # Grab our stashed information from the template
    plotState = doc.template.globals['plotState']

    mods = plotState.modules
    qdata = plotState.data
    dset = plotState.colors
    theme = plotState.theme

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
    r = pdata['q_dctweather']
    r2 = pdata['q_mounttemp']

    # Join them so the timestamps are sorted for us nicely, and nan's
    #   put into the gaps so we don't get all confused later on
    r = r.join(r2, how='outer')

    # Change F -> C because we're scientists god dammit
    r.AirTemp = (r.AirTemp - 32.) * (5./9.)
    r.DewPoint = (r.DewPoint - 32.) * (5./9.)

    # A dict of helpful plot labels
    ldict = {'title': "DCT Weather Information",
             'xlabel': "Time (UTC)",
             'y1label': "Temperature (C)",
             'y2label': "Humidity (%)"}

    fig = bplot.commonPlot(ldict, height=500, width=600)
    timeNow = dt.datetime.utcnow()
    tWindow = dt.timedelta(hours=13)
    tEndPad = dt.timedelta(hours=0.5)

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

    fig.y_range = DataRange1d(start=y1lim[0], end=y1lim[1])
    fig.x_range = DataRange1d(start=timeNow-tWindow, end=timeNow+tEndPad)

    fig.x_range.follow = "end"
    fig.x_range.range_padding = 0.1
    fig.x_range.range_padding_units = 'percent'

    fig.extra_y_ranges = {"y2": DataRange1d(start=y2lim[0], end=y2lim[1])}
    fig.add_layout(LinearAxis(y_range_name="y2",
                              axis_label=ldict['y2label']), 'right')

    # Make sure that we don't have too awkward of a dataframe by filling gaps
    #   This has the benefit of making the tooltip patches WAY easier to handle
    r.fillna(method='ffill', inplace=True)

    # Hack! But it works. Need to do this *before* you create cds below!
    pix, piy = bplot.makePatches(r.index, y1lim)

    # The "master" data source to be used for plotting.
    #    I wish there was a way of abstracting this but I'm not
    #    clever enough. Make the dict in a loop using
    #    the data keys? I dunno. "Future Work" for sure.
    mds = dict(index=r.index, AirTemp=r.AirTemp, Humidity=r.Humidity,
               DewPoint=r.DewPoint, MountTemp=r.MountTemp,
               pix=pix, piy=piy)
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
    simg = fig.patches('pix', 'piy', source=cds,
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
        print("Checking for new data!")

        # Check our stash
        qdata = doc.template.globals['plotState'].data
        timeUpdate = doc.template.globals['plotState'].timestamp
        tdiff = (dt.datetime.utcnow() - timeUpdate).total_seconds()
        print("Data were updated %f seconds ago (%s)" % (tdiff, timeUpdate))

        # Get the last timestamp present in the existing ColumnDataSource
        lastTime = cds.data['index'].max()

        # Update our current time so we can adjust the plot range
        timeNow = dt.datetime.utcnow()

        # It's possible that the timestamp class/type shifts slightly as we
        #   stream data into the main CDS; do some sanitization to check
        #   that we're not going to suddenly barf because of that.
        try:
            # warn=False because I strip the nanoseconds out of everything
            #   ... eventually.  Remember that 'warn' is only valid on an
            #   individual Timestamp object, not the DatetimeIndex as a whole!
            lastTimedt = lastTime.to_pydatetime(warn=False)
        except AttributeError:
            # This means it wasn't a Timestamp object, and it doesn't have
            #   the method that we want/desire.
            if type(lastTime) == np.datetime64:
                # A bit silly, but since pandas Timestamp is a subclass of
                #   datetime.datetime and speaks numpy.datetime64
                #   this is the easiest thing to do
                lastTimedt = pd.Timestamp(lastTime).to_pydatetime(warn=False)

                # The server timezone has been set (during its setup) to UTC;
                #   we need to specifically add that to avoid timezone
                #   shenanigans because in a prior life we were bad and
                #   apparently now must be punished
                storageTZ = timezone('UTC')
                lastTimedt = lastTimedt.replace(tzinfo=storageTZ)
                # print("Converted %s to %s" % (lastTime, lastTimedt))
            else:
                print("IDK WTF BBQ")
                print("Unexpected timestamp type:", type(lastTime))

        # Grab the newest data from the master query dictionary
        pdata = OrderedDict()
        for qtag in m.queries.keys():
            pdata.update({qtag: qdata[qtag]})

        # Update the data references; these are actual DataFrame objects btw.
        r = pdata['q_dctweather']
        r2 = pdata['q_mounttemp']

        # Now select only the data in those frames since lastTime
        #   But! Of course there's another caveat.
        # lastTimedt is dt.datetime object, but r.index has a type of
        #   Timestamp which is really a np.datetime64 wrapper. So we need
        #   to put them on the same page for actual comparisons.
        # NOTE: The logic here was unrolled for debugging timestamp crap.
        #   it can be rolled up again in the next version.
        ripydt = r.index.to_pydatetime()
        r2ipydt = r2.index.to_pydatetime()

        print("Last in CDS: %s" % (lastTimedt))
        print("Last in r  : %s" % (ripydt[-1]))
        print("Last in r2 : %s" % (r2ipydt[-1]))

        rTimeSearchMask = ripydt > lastTimedt
        r2TimeSearchMask = r2ipydt > lastTimedt

        # Need .loc since we're really filtering by label
        rf = r.loc[rTimeSearchMask]
        rf2 = r2.loc[r2TimeSearchMask]

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

            # At this point, there might be a NaN in the column(s) from rf2.
            #   Since we stream only the NEW values, we need to be nice to
            #   ourselves and fill in the prior value for those columns so
            #   the tooltips function and don't spaz out. So get the final
            #   values manually and then fill them into those columns.
            cfills = {}

            # Get the fill values that might be needed for all of our series
            tempFillVal = getLastVal(cds, 'AirTemp')
            humiFillVal = getLastVal(cds, 'Humidity')
            dewpFillVal = getLastVal(cds, 'DewPoint')
            mountFillVal = getLastVal(cds, 'MountTemp')

            cfills.update({"MountTemp": mountFillVal,
                           "AirTemp": tempFillVal,
                           "Humidity": humiFillVal,
                           "DewPoint": dewpFillVal})

            # Now join the dataframes into one single one that we can stream.
            #   Remember to use 'outer' otherwise information will be
            #   mutilated since the two dataframes are on two different
            #   time indicies!
            nf = rf.join(rf2, how='outer')

            # Fill in our column holes. If there are *multiple* temporal holes,
            #   it'll look bonkers because there's only one fill value.
            nf.fillna(value=cfills, inplace=True)

            # Update the new hack patches, too. Special handling for the case
            #   where we just have one new point in time, since
            #   makePatches assumes that you give it enough to sketch out
            #   a box.  It could be changed so it makes the last box the full
            #   xwidth, and that it's .patch()'ed on update here to always be
            #   correct.  But, that's a little too complicated for right now.
            numRows = nf.shape[0]
            if numRows == 1:
                print("Single row!")
                nidx = [pd.Timestamp(lastTimedt), nf.index[-1]]
                nix, niy = bplot.makePatches(nidx, y1lim)
                print("Made patches")
                ndf = pd.DataFrame(data={'pix': nix, 'piy': niy},
                                   index=[nf.index[-1]])
                print("Made DataFrame")
            else:
                # This implies that there are multiple rows, or, more likely,
                #   two different time frames that pandas filled with nans
                #   during the join.  The latter makes our life ... complex.
                print("Multirow!")
                nidx = nf.index
                nix, niy = bplot.makePatches(nidx, y1lim)
                ndf = pd.DataFrame(data={'pix': nix, 'piy': niy},
                                   index=nidx)

            cf = nf.join(ndf, how='outer')
            cf.fillna(method='ffill', inplace=True)

            # Actually update the cds in the plot.
            #   We can just stream a DataFrame! Makes life easy.
            cds.stream(cf, rollover=15000)
            print("New data streamed; %d row(s) added" % (numRows))

        # Manually override the X range so we get the windowing I prefer
        fig.x_range.start = timeNow-tWindow
        fig.x_range.end = timeNow+tEndPad

        print("Range now: %s to %s" % (fig.x_range.start, fig.x_range.end))
        print("")

    doc.add_periodic_callback(grabNew, 5000)

    return doc
