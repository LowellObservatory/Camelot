# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 7 May 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import datetime as dt
from collections import OrderedDict

import numpy as np

from bokeh.models import DataTable, TableColumn, HTMLTemplateFormatter
from bokeh.plotting import ColumnDataSource

from . import modulePlots as bplot


def dataGatherer_TCS(m, qdata, timeFilter=None, fillNull=True, debug=True):
    """
    Instrument/plot/query specific contortions needed to make the
    bulk of the plot code generic and abstract.  I feel ok
    hardcoding stuff in here at least, since this will always be namespace
    protected and unambigious (e.g. instrumentTelem.dataGatherer).
    """
    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    # Get the keys that define the input dataset
    r = pdata['q_tcssv']

    if timeFilter is None:
        rj = r

        if fillNull is True:
            # Make sure that we don't have too awkward of a dataframe
            #   by filling gaps. This has the benefit of making the
            #   tooltip patches WAY easier to handle.
            rj.fillna(method='ffill', inplace=True)
    else:
        # Now select only the data in those frames since lastTime
        #   But! Of course there's another caveat.
        # lastTimedt could be a dt.datetime object, but r.index has a type of
        #   Timestamp which is really a np.datetime64 wrapper. So we need
        #   to put them on the same page for actual comparisons.
        # NOTE: The logic here was unrolled for debugging timestamp crap.
        #   it can be rolled up again in the next version.
        ripydt = r.index.to_pydatetime()

        if debug is True:
            print("Last in CDS: %s" % (timeFilter))
            print("Last in r  : %s" % (ripydt[-1]))

        rTimeSearchMask = ripydt > timeFilter

        # Need .loc since we're really filtering by label
        rj = r.loc[rTimeSearchMask]

    return rj


def dataGatherer_LPI(m, qdata, timeFilter=None, fillNull=True, debug=True):
    """
    Instrument/plot/query specific contortions needed to make the
    bulk of the plot code generic and abstract.  I feel ok
    hardcoding stuff in here at least, since this will always be namespace
    protected and unambigious (e.g. instrumentTelem.dataGatherer).
    """
    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    # Get the keys that define the input dataset
    r = pdata['q_tcssv']
    r2 = pdata['q_tcslois']
    r3 = pdata['q_cubeinstcover']
    r4 = pdata['q_cubefolds']

    if timeFilter is None:
        # Join them so the timestamps are sorted for us nicely, and nan's
        #   put into the gaps so we don't get all confused later on
        rj = r.join(r2, how='outer')
        rj = rj.join(r3, how='outer')
        rj = rj.join(r4, how='outer')

        if fillNull is True:
            # Make sure that we don't have too awkward of a dataframe
            #   by filling gaps. This has the benefit of making the
            #   tooltip patches WAY easier to handle.
            rj.fillna(method='ffill', inplace=True)
    else:
        # Now select only the data in those frames since lastTime
        #   But! Of course there's another caveat.
        # lastTimedt could be a dt.datetime object, but r.index has a type of
        #   Timestamp which is really a np.datetime64 wrapper. So we need
        #   to put them on the same page for actual comparisons.
        # NOTE: The logic here was unrolled for debugging timestamp crap.
        #   it can be rolled up again in the next version.
        ripydt = r.index.to_pydatetime()
        r2ipydt = r2.index.to_pydatetime()
        r3ipydt = r3.index.to_pydatetime()
        r4ipydt = r4.index.to_pydatetime()

        if debug is True:
            print("Last in CDS: %s" % (timeFilter))
            print("Last in r  : %s" % (ripydt[-1]))
            print("Last in r2 : %s" % (r2ipydt[-1]))
            print("Last in r3 : %s" % (r3ipydt[-1]))
            print("Last in r4 : %s" % (r4ipydt[-1]))

        rTimeSearchMask = ripydt > timeFilter
        r2TimeSearchMask = r2ipydt > timeFilter
        r3TimeSearchMask = r3ipydt > timeFilter
        r4TimeSearchMask = r4ipydt > timeFilter

        # Need .loc since we're really filtering by label
        rf = r.loc[rTimeSearchMask]
        rf2 = r2.loc[r2TimeSearchMask]
        rf3 = r3.loc[r3TimeSearchMask]
        rf4 = r4.loc[r4TimeSearchMask]

        # Now join the dataframes into one single one that we can stream.
        #   Remember to use 'outer' otherwise information will be
        #   mutilated since the two dataframes are on two different
        #   time indicies!
        rj = rf.join(rf2, how='outer')
        rj = rj.join(rf3, how='outer')
        rj = rj.join(rf4, how='outer')

    return rj


def assembleFacSumTCS(r):
    """
    """
    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # Now the tedious bit - reassemble the shredded parameters like RA/Dec/etc.
    #   Whomever designed the TCS XML...know that I'm not a fan of your work.
    #
    # 'deshred' will automatically take the last entry and return a
    #   non-annoying version with its timestamp for later display.
    #
    # First, get the last valid index in the q_tcssv dataframe and use that
    #   for all the TCS queries to make sure it's at least consistent
    tcsLastIdx = r.cRA_h.index[-1]

    # CURRENT coords
    cRA = bplot.deshred([r.cRA_h,
                         r.cRA_m,
                         r.cRA_s],
                        delim=":", lastIdx=tcsLastIdx,
                        name="cRA", comptime=now)
    cDec = bplot.deshred([r.cDec_d,
                          r.cDec_m,
                          r.cDec_s],
                         delim=":", lastIdx=tcsLastIdx,
                         name="cDec", comptime=now)

    cFrame = bplot.getLast(r.cFrame, lastIdx=tcsLastIdx, comptime=now)
    # cEpoch = bplot.deshred([r.cEqP,
    #                         r.cEqY,
    #                         r.cFrame],
    #                        delim="", lastIdx=tcsLastIdx,
    #                        name="cEpoch", comptime=now)

    # DEMAND coords
    dRA = bplot.deshred([r.dRA_h,
                         r.dRA_m,
                         r.dRA_s],
                        delim=":", lastIdx=tcsLastIdx,
                        name="dRA", comptime=now)
    dDec = bplot.deshred([r.dDec_d,
                          r.dDec_m,
                          r.dDec_s],
                         delim=":", lastIdx=tcsLastIdx,
                         name="dDec", comptime=now)

    dFrame = cFrame = bplot.getLast(r.dFrame, lastIdx=tcsLastIdx, comptime=now)
    # dEpoch = bplot.deshred([r.dEqP,
    #                         r.dEqY,
    #                         r.dFrame],
    #                        delim="", lastIdx=tcsLastIdx,
    #                        name="dEpoch", comptime=now)

    airmass = bplot.getLast(r.Airmass,
                            lastIdx=tcsLastIdx, comptime=now)
    targname = bplot.getLast(r.TargetName,
                             lastIdx=tcsLastIdx, comptime=now)
    guidemode = bplot.getLast(r.GuideMode,
                              lastIdx=tcsLastIdx, comptime=now)
    sundist = bplot.getLast(r.SunDistance,
                            lastIdx=tcsLastIdx, comptime=now)
    moondist = bplot.getLast(r.MoonDistance,
                             lastIdx=tcsLastIdx, comptime=now)

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [tcsLastIdx, targname,
                # cRA, cDec, cEpoch,
                # dRA, dDec, dEpoch,
                cRA, cDec, cFrame,
                dRA, dDec, dFrame,
                airmass, guidemode,
                sundist, moondist]

    values = []
    labels = []
    tooold = []
    for i, each in enumerate(tableDat):
        if i == 0:
            values.append(each.strftime("%Y-%m-%d %H:%M:%S.%f %Z"))
            labels.append("DataTimestamp")
            tooold.append(None)
        else:
            values.append(each.value)
            labels.append(each.label)

        if i > 0:
            # Rather than put this in each elif, I'll just do it here.
            #   Add in our age comparison column, for color/styling later
            tooold.append(each.tooOld)

    mds = dict(labels=labels, values=values, ageStatement=tooold)
    cds = ColumnDataSource(mds)

    return cds


def assembleFacSumLPI(r):
    """
    """
    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # Now the tedious bit - reassemble the shredded parameters like RA/Dec/etc.
    #   Whomever designed the TCS XML...know that I'm not a fan of your work.
    #
    # 'deshred' will automatically take the last entry and return a
    #   non-annoying version with its timestamp for later display.
    #
    # First, get the last index in the q_tcssv dataframe and use that
    #   for all the TCS queries to make sure it's at least consistent
    tcsLastIdx = r.cRA_h.index[-1]

    mirrorcov = bplot.getLast(r.MirrorCover, lastIdx=tcsLastIdx,
                              comptime=now)

    # These are from other data sources, so get their values too
    domeshut = bplot.getLast(r.DomeShutter, comptime=now)
    instcover = bplot.getLast(r.InstCover, comptime=now)

    cubeLastIdx = r.PortThru.index[-1]
    portT = bplot.getLast(r.PortThru, lastIdx=cubeLastIdx,
                          comptime=now)
    portA = bplot.getLast(r.PortA, lastIdx=cubeLastIdx,
                          comptime=now)
    portB = bplot.getLast(r.PortB, lastIdx=cubeLastIdx,
                          comptime=now)
    portC = bplot.getLast(r.PortC, lastIdx=cubeLastIdx,
                          comptime=now)
    portD = bplot.getLast(r.PortD, lastIdx=cubeLastIdx,
                          comptime=now)

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [tcsLastIdx,
                domeshut, mirrorcov, instcover,
                portT, portA, portB, portC, portD]

    values = []
    labels = []
    tooold = []
    for i, each in enumerate(tableDat):
        if i == 0:
            values.append(each.strftime("%Y-%m-%d %H:%M:%S.%f %Z"))
            labels.append("DataTimestamp")
            tooold.append(None)
        elif each.label == "InstCover":
            # Special conversion to text for this one
            if each.value == 0:
                values.append("Closed")
            else:
                values.append("Open")
            labels.append(each.label)
        elif each.label.startswith("Port"):
            if each.value == 0:
                values.append("Inactive")
            else:
                values.append("Active")
            labels.append(each.label)
        else:
            values.append(each.value)
            labels.append(each.label)

        if i > 0:
            # Rather than put this in each elif, I'll just do it here.
            #   Add in our age comparison column, for color/styling later
            tooold.append(each.tooOld)

    mds = dict(labels=labels, values=values, ageStatement=tooold)
    cds = ColumnDataSource(mds)

    return cds


def makeFacSum_LPI(doc):
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

    #
    # NOTE: Should clean this up or stuff it all into dataGatherer
    #
    # Hard coding the access/dict key for the data needed for this plot
    #   Cringe-worthy but tolerable. This MUST match what is set in the
    #   'modules.conf' file otherwise it'll blow up.
    moduleKey = 'facsum_lpi'
    m = mods[moduleKey]

    print("Serving %s" % (m.title))

    # Use this to consistently filter/gather the data based on some
    #   specific tags/reorganizing
    r = dataGatherer_LPI(m, qdata)

    cds = assembleFacSumLPI(r)
    print()

    # Define our color format/template
    #   This uses Underscore’s template method and syntax.
    #   http://underscorejs.org/#template
    template = """
               <b>
                 <div style="background:<%=
                   (function ageColorer(){
                      if(ageStatement){
                        return("#ff0000;opacity:0.25;")
                      }
                      else{
                        return("White")
                      }
                    }()) %>;">
                   <%= value %>
                 </div>
               </b>
               """

    formatter = HTMLTemplateFormatter(template=template)

    # Now we construct our table by specifying the columns we actually want.
    #   We ignore the 'ageStatement' row for this because we
    #   just get at it via the formatter/template defined above
    labelCol = TableColumn(field='labels', title='Parameter')
    valueCol = TableColumn(field='values', title='Value', formatter=formatter)
    cols = [labelCol, valueCol]

    # Now actually construct the table
    dtab = DataTable(columns=cols, source=cds)

    # THIS IS SO GOD DAMN IRRITATING
    #   It won't accept this in a theme file because it seems like there's a
    #   type check on it and None is not an int type
    dtab.index_position = None

    # This is also irritating
    #   Specify a css group to be stuffed into the resulting div/template
    #   which is then styled by something else. Can't get it thru the theme :(
    dtab.css_classes = ["nightwatch_bokeh_table"]

    doc.theme = theme
    doc.title = m.title
    doc.add_root(dtab)

    def grabNew():
        print("Checking for new data!")

        # WHYYYYYYY do I have to do this now? I feel like I didn't like
        #   5 minutes ago but now cds isn't inherited, but m and r are. WTF!
        cds = doc.roots[0].source

        # Check our stash
        qdata = doc.template.globals['plotState'].data
        timeUpdate = doc.template.globals['plotState'].timestamp
        tdiff = (dt.datetime.utcnow() - timeUpdate).total_seconds()
        print("Data were queried %f seconds ago (%s)" % (tdiff, timeUpdate))

        # Get the last timestamp present in the existing ColumnDataSource
        #  Hardcode it for now since I'm the one that makes it
        lastTime = cds.data['values'][0]

        # Turn it into a datetime.datetime (with UTC timezone)
        lastTimedt = bplot.convertTimestamp(lastTime, tz='UTC')

        # Sweep up all the data, and filter down to only those
        #   after the given time
        nr = dataGatherer_LPI(m, qdata, timeFilter=lastTimedt)

        if nr.empty is False:
            # Check the data for updates, and downselect to just the newest
            ncds = assembleFacSumLPI(nr)

            # Actually update the data. Just replace it wholesale!
            #   Should I really use .patch()? Or is that just for DataFrames?
            cds = ncds
            print("New data inplanted")
        else:
            print("No new data!")

    print("Set doc periodic callback")
    doc.add_periodic_callback(grabNew, 5000)

    return doc


def makeFacSum_TCS(doc):
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

    #
    # NOTE: Should clean this up or stuff it all into dataGatherer
    #
    # Hard coding the access/dict key for the data needed for this plot
    #   Cringe-worthy but tolerable. This MUST match what is set in the
    #   'modules.conf' file otherwise it'll blow up.
    moduleKey = 'facsum_tcs'
    m = mods[moduleKey]

    print("Serving %s" % (m.title))

    # Use this to consistently filter/gather the data based on some
    #   specific tags/reorganizing
    r = dataGatherer_TCS(m, qdata)

    cds = assembleFacSumTCS(r)
    print()

    # Define our color format/template
    #   This uses Underscore’s template method and syntax.
    #   http://underscorejs.org/#template
    template = """
               <b>
                 <div style="background:<%=
                   (function ageColorer(){
                      if(ageStatement){
                        return("#ff0000;opacity:0.25;")
                      }
                      else{
                        return("White")
                      }
                    }()) %>;">
                   <%= value %>
                 </div>
               </b>
               """

    formatter = HTMLTemplateFormatter(template=template)

    # Now we construct our table by specifying the columns we actually want.
    #   We ignore the 'ageStatement' row for this because we
    #   just get at it via the formatter/template defined above
    labelCol = TableColumn(field='labels', title='Parameter')
    valueCol = TableColumn(field='values', title='Value', formatter=formatter)
    cols = [labelCol, valueCol]

    # Now actually construct the table
    dtab = DataTable(columns=cols, source=cds)

    # THIS IS SO GOD DAMN IRRITATING
    #   It won't accept this in a theme file because it seems like there's a
    #   type check on it and 'None' is not the 'correct' type
    dtab.index_position = None

    # This is also irritating
    #   Specify a css group to be stuffed into the resulting div/template
    #   which is then styled by something else. Can't get it thru the theme :(
    dtab.css_classes = ["nightwatch_bokeh_table"]

    doc.theme = theme
    doc.title = m.title
    doc.add_root(dtab)

    def grabNew():
        print("Checking for new data!")

        # WHYYYYYYY do I have to do this now? I feel like I didn't like
        #   5 minutes ago but now cds isn't inherited, but m and r are. WTF!
        cds = doc.roots[0].source

        # Check our stash
        qdata = doc.template.globals['plotState'].data
        timeUpdate = doc.template.globals['plotState'].timestamp
        tdiff = (dt.datetime.utcnow() - timeUpdate).total_seconds()
        print("Data were queried %f seconds ago (%s)" % (tdiff, timeUpdate))

        # Get the last timestamp present in the existing ColumnDataSource
        #  Hardcode it for now since I'm the one that makes it
        lastTime = cds.data['values'][0]

        # Turn it into a datetime.datetime (with UTC timezone)
        lastTimedt = bplot.convertTimestamp(lastTime, tz='UTC')

        # Sweep up all the data, and filter down to only those
        #   after the given time
        nr = dataGatherer_TCS(m, qdata, timeFilter=lastTimedt)

        if nr.empty is False:
            # Check the data for updates, and downselect to just the newest
            ncds = assembleFacSumTCS(nr)

            # Actually update the data. Just replace it wholesale!
            #   Should I really use .patch()? Or is that just for DataFrames?
            cds = ncds
            print("New data inplanted")
        else:
            print("No new data!")

    print("Set doc periodic callback")
    doc.add_periodic_callback(grabNew, 5000)

    return doc
