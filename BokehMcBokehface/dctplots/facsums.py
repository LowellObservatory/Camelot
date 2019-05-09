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

    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # Now the tedious bit - reassemble the shredded parameters like RA/Dec/etc.
    #   Whomever designed the TCS XML...know that I'm not a fan of your work.
    #
    # 'deshred' will automatically take the last entry and return a
    #   non-annoying version with its timestamp for later display.

    # CURRENT coords
    cRA = bplot.deshred([r.cRA_h,
                         r.cRA_m,
                         r.cRA_s],
                        delim=":",
                        name="cRA", comptime=now)
    cDec = bplot.deshred([r.cDec_d,
                          r.cDec_m,
                          r.cDec_s],
                         delim=":",
                         name="cDec", comptime=now)

    cFrame = bplot.getLast(r.cFrame, comptime=now)
    # cEpoch = bplot.deshred([r.cEqP,
    #                         r.cEqY,
    #                         r.cFrame],
    #                        delim="", lastIdx=tcsLastIdx,
    #                        name="cEpoch", comptime=now)

    # DEMAND coords
    dRA = bplot.deshred([r.dRA_h,
                         r.dRA_m,
                         r.dRA_s],
                        delim=":",
                        name="dRA", comptime=now)
    dDec = bplot.deshred([r.dDec_d,
                          r.dDec_m,
                          r.dDec_s],
                         delim=":",
                         name="dDec", comptime=now)

    dFrame = cFrame = bplot.getLast(r.dFrame, comptime=now)
    # dEpoch = bplot.deshred([r.dEqP,
    #                         r.dEqY,
    #                         r.dFrame],
    #                        delim="", lastIdx=tcsLastIdx,
    #                        name="dEpoch", comptime=now)

    airmass = bplot.getLast(r.Airmass, comptime=now)
    targname = bplot.getLast(r.TargetName, comptime=now)
    guidemode = bplot.getLast(r.GuideMode, comptime=now)
    sundist = bplot.getLast(r.SunDistance, comptime=now)
    moondist = bplot.getLast(r.MoonDistance, comptime=now)

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [targname,
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
        values.append(each.value)
        labels.append(each.label)
        tooold.append(each.tooOld)

    mds = dict(labels=labels, values=values, ageStatement=tooold)
    cds = ColumnDataSource(mds)

    return cds


def dataGatherer_LPI(m, qdata):
    """
    Instrument/plot/query specific contortions needed to make the
    bulk of the plot code generic and abstract.  I feel ok
    hardcoding stuff in here at least, since this will always be namespace
    protected and unambigious (e.g. instrumentTelem.dataGatherer).
    """
    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    # Downselect to just the final rows in each of the query dataframes
    r = pdata['q_tcssv'].tail(1)
    r2 = pdata['q_tcslois'].tail(1)
    r3 = pdata['q_cubeinstcover'].tail(1)
    r4 = pdata['q_cubefolds'].tail(1)

    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # Now the tedious bit - reassemble the shredded parameters like RA/Dec/etc.
    #   Whomever designed the TCS XML...know that I'm not a fan of your work.
    #
    # 'deshred' will automatically take the last entry and return a
    #   non-annoying version with its timestamp for later display.
    mirrorcov = bplot.getLast(r.MirrorCover, comptime=now)

    # These are from other data sources, so get their values too
    domeshut = bplot.getLast(r2.DomeShutter, comptime=now)
    instcover = bplot.getLast(r3.InstCover, comptime=now)

    portT = bplot.getLast(r4.PortThru, comptime=now)
    portA = bplot.getLast(r4.PortA, comptime=now)
    portB = bplot.getLast(r4.PortB, comptime=now)
    portC = bplot.getLast(r4.PortC, comptime=now)
    portD = bplot.getLast(r4.PortD, comptime=now)

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [domeshut, mirrorcov, instcover,
                portT, portA, portB, portC, portD]

    values = []
    labels = []
    tooold = []
    for i, each in enumerate(tableDat):
        if each.label == "InstCover":
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
    cds = dataGatherer_LPI(m, qdata)

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

        # Let's just be dumb and replace everything all at once
        ncds = dataGatherer_LPI(m, qdata)
        cds.stream(ncds.data, rollover=7)

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
    cds = dataGatherer_TCS(m, qdata)

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

        # Let's just be dumb and replace everything all at once
        ncds = dataGatherer_TCS(m, qdata)
        cds.stream(ncds.data, rollover=11)

    print("Set doc periodic callback")
    doc.add_periodic_callback(grabNew, 5000)

    return doc
