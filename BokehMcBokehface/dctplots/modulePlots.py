# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 4 Dec 2018
#
#  @author: rhamilton

"""Collection of routines used to make good Bokeh plots.

I admit it's a big damn mess in here.  This really needs to be cleaned
up in the near future, and streamlined to align to the new containerized
way that the plots are called/generated/updated.  A lot of this code could
turn out to be vestigial from the initial version that made plot snapshots.
    - RTH 20190426
"""

from __future__ import division, print_function, absolute_import

import datetime as dt

import numpy as np
import pandas as pd
from pytz import timezone

from bokeh.models import Range1d, HoverTool, Legend, LegendItem
from bokeh.plotting import figure, output_file, ColumnDataSource


class valJudgement(object):
    def __init__(self):
        self.label = None
        self.value = None
        self.timestamp = None
        self.tooOld = False

    def judgeAge(self, maxage=None,
                 comptime=None):
        # Need to put everything into Numpy datetime64/timedelta64 objects
        #   to allow easier interoperations
        if maxage is None:
            maxage = dt.timedelta(minutes=5.5)
            maxage = np.timedelta64(maxage)

        if comptime is None:
            comptime = np.datetime64(dt.datetime.utcnow())

        delta = comptime - self.timestamp
        if delta > maxage:
            self.tooOld = True
        else:
            self.tooOld = False


def convertTimestamp(lastTime, tz='UTC'):
    """
    """
    if tz.upper() == 'UTC':
        storageTZ = timezone('UTC')
    else:
        raise NotImplementedError

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
            lastTimedt = lastTimedt.replace(tzinfo=storageTZ)
            # print("Converted %s to %s" % (lastTime, lastTimedt))
        else:
            print("IDK WTF BBQ")
            print("Unexpected timestamp type:", type(lastTime))

    return lastTimedt


def getLastVal(cds, cdstag):
    """
    Given a ColumnDataSource (or numpy array) return the last value.

    Mostly useful to grab a quick-and-dirty 'fill' value when combining
    multiple independent sources.

    Does not check if that last value is actually a NaN, which is probably
    a bad thing to ignore.  But that could be fixed too.
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


def getLast(p1, lastIdx=None, comptime=None):
    """
    TODO: Remember how this is different than the one above (getLastVal)
    """
    if lastIdx is None:
        # Get the last valid position/value in the dataframe
        lastIdx = p1.last_valid_index()

    retObj = valJudgement()
    retObj.label = p1.name
    retObj.value = p1[lastIdx]

    # Use datetime64 to avoid an annoying nanoseconds warning when
    #   using just regular .to_pydatetime()
    retObj.timestamp = lastIdx.to_datetime64()
    retObj.judgeAge(comptime=comptime)

    return retObj


def deshred(plist, delim=":", name=None, lastIdx=None,
            comptime=None, last=True):
    """
    NOTE: p1 thru 3 are expected to be Pandas dataframes
    """
    if comptime is None:
        comptime = np.datetime64(dt.datetime.utcnow())

    if last is True:
        retStr = ""
        for i, each in enumerate(plist):
            # Made this a function so I can reuse it elsewhere
            retVal = getLast(each, lastIdx=lastIdx)

            # Smoosh it all together; if it's the last value, don't
            #   add the delim since it's not needed at the end of the str
            if i == len(plist) - 1:
                delim = ""

            try:
                retStr += "%02d%s" % (retVal.value, delim)
            except TypeError:
                # This means we probably had heterogeneous datatypes so just
                #   print them all as strings to move on quickly
                retStr += "%s%s" % (retVal.value, delim)

        # Pack everything up for returning it all as one object
        fObj = valJudgement()
        if name is None:
            fObj.label = retVal.label
        else:
            fObj.label = name
        fObj.value = retStr
        fObj.timestamp = retVal.timestamp
        fObj.judgeAge(comptime=comptime)

        return fObj
    else:
        # Should do a sort of a zip dance here to combine the multiple
        #   dataframes into a single dataframe with the delim; would save some
        #   CPU cycles if I did this just after the query so the plotting
        #   routine doesn't have to do it, but that sounds a lot like
        #   "Version 2.0" sort of talk.
        raise NotImplementedError


def checkForEmptyData(indat):
    """
    """
    # Check to make sure we actually have data ...
    abort = False
    for q in indat:
        if len(indat[q]) == 0:
            abort = True
            break

    return abort


def commonPlot(ldict, height=None, width=None):
    """
    """
    tools = "pan, wheel_zoom, box_zoom, crosshair, reset, save"

    title = ldict['title']
    xlabel = ldict['xlabel']
    y1label = ldict['y1label']

    p = figure(title=title, x_axis_type='datetime',
               x_axis_label=xlabel, y_axis_label=y1label,
               tools=tools, output_backend="webgl")

    if height is not None:
        p.plot_height = height

    if width is not None:
        p.plot_width = width

    return p


def makeNewPatches(nf, y1lim, lastTimedt):
    """
    Make a new set of patches based on the stuff in the 'nf' Dataframe.

    This is most useful when stream()ing new data to an already
    existing ColumnDataSource.

    There is some special handling necessary for the case where we just
    have one new point in time, since makePatches assumes that you give
    it enough to sketch out a box.  It could be changed so it makes
    the last box the full xwidth, and that it's .patch()'ed on update
    here to always be correct.  But, that's a little too complicated right now.

    This is generally confusing without a diagram. Sorry.
    """
    numRows = nf.shape[0]
    if numRows == 1:
        print("Single row!")

        nidx = [pd.Timestamp(lastTimedt), nf.index[-1]]
        nix, niy = makePatches(nidx, y1lim)
        fix = [nf.index[-1]]

        print("Made patches")
        print(np.shape(nix), np.shape(niy), np.shape(fix))
    else:
        print("Multirow!")

        nidx = [pd.Timestamp(lastTimedt)] + list(nf.index)
        nix, niy = makePatches(nidx, y1lim)
        fix = nidx[:-1]

        print("Made patches")
        print(np.shape(nix), np.shape(niy), np.shape(fix))

    return nix, niy


def makePatches(xindex, y1lim, first=False):
    """
    This is a bit of a HACK!  It might be a little screwy at the edges.

    It gives way better tooltips on a timeseries plot.  It works by
    turning the indicies into a list of lists of x coordinates and
    y coordinates for a series of adjacent patches.  Their width is the time
    between two datapoints and height spans the (initial) y1 range.
    """
    ix = []
    iy = []

    if len(xindex) < 2:
        print("ERROR: Need at least two xindex values!")
        raise ValueError

    if len(y1lim) != 2:
        print("ERROR: Need exactly two y1lim values!")
        raise ValueError

    for i, _ in enumerate(xindex):
        store = False
        # NOTE: Life is just easier if we make sure to keep things in
        #   terms of pandas.Timestamp from this point forward, since
        #   this will ultimately be stream()'ed back into the
        #   original plot's ColumnDataSource, which was really a
        #   pandas.DataFrame at the start of it's life
        if i == 0:
            if first is True:
                # Special case for the very first row of data the first
                #   time we make the hacked patches; we pad out the xrange
                #   so the first value is shown.  Subsequent calls
                #   MUST be first=False or else things will go poorly, quickly
                # It's small enough to hit, but not large enough to screw with
                #   the auto-scaled x range.  Or at least that's the intent!
                x1 = pd.Timestamp(xindex[0])
                x0 = x1 - pd.Timedelta(seconds=60)
                store = True
        else:
            x0 = pd.Timestamp(xindex[i-1])
            x1 = pd.Timestamp(xindex[i])
            store = True

        if store is True:
            ix.append([x0, x1, x1, x0])
            iy.append([y1lim[0], y1lim[0], y1lim[1], y1lim[1]])

    return ix, iy


def plotLineWithPoints(p, cds, sname, color,
                       hcolor=None, yrname=None):
    """
    p: plot object
    cds: ColumnDataSource
    sname: source name (in cds)
    slabel: series label (for legend)
    Assumes that you have both 'index' and sname as columns in your
    ColumnDataSource! slabel is then used for the Legend and tooltip labels.
    """
    # NOTE: The way my polling code is set up, mode='after' is the correct
    #   step mode since I get the result and then sleep for an interval
    if hcolor is None:
        hcolor = '#E24D42'

    if yrname is None:
        l = p.step('index', sname, line_width=2, source=cds, mode='after',
                   color=color, name=sname)
        s = p.scatter('index', sname, size=8, source=cds,
                      color=color, name=sname,
                      alpha=0., hover_alpha=1., hover_color=hcolor)
    else:
        l = p.step('index', sname, line_width=2, source=cds, mode='after',
                   y_range_name=yrname,
                   color=color, name=sname)
        s = p.scatter('index', sname, size=8, source=cds,
                      y_range_name=yrname,
                      color=color, name=sname,
                      alpha=0., hover_alpha=1., hover_color=hcolor)

    return l, s


def makeWindPlots(indat, cwheel, outfile=None):
    """
    """

    y1lim = [0, 15]

    r = indat['q_wrs']
    output_file(outfile)

    ldict = {'title': "WRS Wind Information",
             'xlabel': "Time (UTC)",
             'y1label': "Wind Speed (m/s)"}

    p = commonPlot(r, ldict)
    timeNow = dt.datetime.utcnow()
    tWindow = dt.timedelta(hours=24)

    if y1lim is None:
        y1lim = [r.WindSpeedMin.values.min,
                 r.WindSpeedMax.values.max]
    p.y_range = Range1d(start=y1lim[0], end=y1lim[1])
    p.x_range = Range1d(start=timeNow-tWindow, end=timeNow)

    # Hack! But it works. Need to do this *before* you create cds below!
    ix, iy = makePatches(r, y1lim)

    # The "master" data source to be used for plotting.
    #    I wish there was a way of abstracting this but I'm not *quite*
    #    clever enough with a baby imminent. Make the dict in a loop using
    #    the data keys? I dunno. "Future Work" for sure.
    mds = dict(index=r.index,
               WindSpeed=r.WindSpeed,
               WindSpeedMin=r.WindSpeedMin,
               WindSpeedMax=r.WindSpeedMax,
               WindDir=r.WindDir,
               ix=ix, iy=iy)
    cds = ColumnDataSource(mds)

    # Make the plots/lines!
    l1, _ = plotLineWithPoints(p, cds, "WindSpeed", cwheel[0])
    l2, _ = plotLineWithPoints(p, cds, "WindSpeedMin", cwheel[1])
    l3, _ = plotLineWithPoints(p, cds, "WindSpeedMax", cwheel[2])

    li1 = LegendItem(label="WindSpeed", renderers=[l1])
    li2 = LegendItem(label="WindSpeedMin", renderers=[l2])
    li3 = LegendItem(label="WindSpeedMax", renderers=[l3])
    legend = Legend(items=[li1, li2, li3], location='top_left',
                    orientation='horizontal', spacing=15)
    p.add_layout(legend)

    # HACK HACK HACK HACK HACK
    #   Apply the patches to carry the tooltips
    simg = p.patches('ix', 'iy', source=cds,
                     fill_color=None,
                     fill_alpha=0.0,
                     line_color=None)

    # Make the hovertool only follow the patches (still a hack)
    htline = simg

    # Customize the active tools
    p.toolbar.autohide = True

    ht = HoverTool()
    ht.tooltips = [("Time", "@index{%F %T}"),
                   ("WindSpeed", "@WindSpeed{0.0} m/s"),
                   ("WindSpeedMin", "@WindSpeedMin{0.0} m/s"),
                   ("WindSpeedMax", "@WindSpeedMax{0.0} m/s")
                   ]
    ht.formatters = {'index': 'datetime'}
    ht.show_arrow = False
    ht.point_policy = 'follow_mouse'
    ht.line_policy = 'nearest'
    ht.renderers = [htline]
    p.add_tools(ht)

    return p
