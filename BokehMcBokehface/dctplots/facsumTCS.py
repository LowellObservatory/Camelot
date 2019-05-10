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


def dataGatherer(m, qdata):
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
                        name="Current RA", comptime=now)
    cDec = bplot.deshred([r.cDec_d,
                          r.cDec_m,
                          r.cDec_s],
                         delim=":",
                         name="Current Dec", comptime=now)

    cFrame = bplot.getLast(r.cFrame,
                           label="Current Frame", comptime=now)

    # DEMAND coords
    dRA = bplot.deshred([r.dRA_h,
                         r.dRA_m,
                         r.dRA_s],
                        delim=":",
                        name="Demand RA", comptime=now)

    dDec = bplot.deshred([r.dDec_d,
                          r.dDec_m,
                          r.dDec_s],
                         delim=":",
                         name="Demand Dec", comptime=now)

    dFrame = bplot.getLast(r.dFrame,
                           label="Demand Frame", comptime=now)

    # HA
    cHA = bplot.deshred([r.cHA_h,
                         r.cHA_m,
                         r.cHA_s],
                        delim=":",
                        name="Current HA", comptime=now)

    # LST
    lst = bplot.deshred([r.LST_h,
                         r.LST_m,
                         r.LST_s],
                        delim=":",
                        name="TCS LST", comptime=now)

    airmass = bplot.getLast(r.Airmass, comptime=now, fstr="%.2f")
    targname = bplot.getLast(r.TargetName, comptime=now)
    guidemode = bplot.getLast(r.GuideMode, comptime=now)
    sundist = bplot.getLast(r.SunDistance, comptime=now, fstr="%.2f")
    moondist = bplot.getLast(r.MoonDistance, comptime=now, fstr="%.2f")

    # Now snag our pyephem ephemeris information
    e = qdata['ephemera']
    sunrise = bplot.getLast(e.sunrise, label='Sunrise', comptime=now)
    sunset = bplot.getLast(e.sunset, label='Sunset', comptime=now)

    # nsunrise = bplot.getLast(e.nextsunrise, label='Next Sunrise',
    #                          comptime=now)
    # nsunset = bplot.getLast(e.nextsunset, label='Next Sunset',
    #                         comptime=now)

    sunalt = bplot.getLast(e.sun_dms, label='Sun Altitude',
                           comptime=now, fstr="%.2f")
    moonalt = bplot.getLast(e.moon_dms, label='Moon Altitude',
                            comptime=now, fstr="%.2f")
    moonphase = bplot.getLast(e.moonphase*100., label='Moon Phase',
                              comptime=now, fstr="%.2f")

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [targname, lst, cHA,
                cRA, cDec, cFrame,
                dRA, dDec, dFrame,
                airmass, guidemode,
                sundist, moondist,
                sunrise, sunset,
                # nsunrise, nsunset,
                sunalt, moonalt, moonphase]

    values = []
    labels = []
    tooold = []
    for each in tableDat:
        if each.label.lower().find("rise") != -1 or\
           each.label.lower().find("set") != -1:
            values.append(each.value.strftime("%Y-%m-%d %H:%M:%S %Z"))
        else:
            values.append(each.value)

        labels.append(each.label)
        tooold.append(each.tooOld)

    mds = dict(labels=labels, values=values, ageStatement=tooold)
    cds = ColumnDataSource(mds)

    return cds


def makeFacSum(doc):
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
    cds = dataGatherer(m, qdata)

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
        ncds = dataGatherer(m, qdata)
        cds.stream(ncds.data, rollover=18)

    print("Set doc periodic callback")
    doc.add_periodic_callback(grabNew, 5000)

    return doc
