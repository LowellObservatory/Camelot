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

from bokeh.plotting import ColumnDataSource
from bokeh.models import DataRange1d, HoverTool, Legend, LegendItem

from . import modulePlots as bplot


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
    m = mods[2]

    print("Serving %s" % (m.title))
    # Gather up the query data into a single dict so we don't
    #   have to encode absolutely everything in every single plot/page
    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    # Setting y1lim to None lets it autoscale based on the data;
    #   Seemed best to keep humidity as 0-100 though.
    y1lim = None

    # Get the keys that define the input dataset
    r = pdata['q_insttemps']['deveny']
    r2 = pdata['q_insttemps']['lemi']

    # Join them so the timestamps are sorted for us nicely, and nan's
    #   put into the gaps so we don't get all confused later on
    r = r.join(r2, how='outer', lsuffix='_deveny', rsuffix='_lemi')

    # A dict of helpful plot labels
    ldict = {'title': "Instrument Temperatures",
             'xlabel': "Time (UTC)",
             'y1label': "Temperature (C)"}

    fig = bplot.commonPlot(ldict, height=400, width=600)

    # Remember that .min and .max are methods! Need the ()
    #   Also adjust plot extents to pad +/- N percent
    npad = 0.1
    if y1lim is None:
        y1lim = [r.CCDTemp_lemi.min(skipna=True),
                 r.AUXTemp_lemi.max(skipna=True)]

        # Now pad them appropriately, checking for a negative limit
        if y1lim[0] < 0:
            y1lim[0] *= (1.+npad)
        else:
            y1lim[0] *= (1.-npad)

        if y1lim[1] < 0:
            y1lim[1] *= (1.-npad)
        else:
            y1lim[1] *= (1.+npad)

    # fig.y_range = DataRange1d(start=y1lim[0], end=y1lim[1])
    # fig.x_range = DataRange1d(start=timeNow-tWindow, end=timeNow+tEndPad)

    fig.x_range.follow = "end"
    fig.x_range.range_padding = 0.1
    fig.x_range.range_padding_units = 'percent'

    # Make sure that we don't have too awkward of a dataframe by filling gaps
    #   This has the benefit of making the tooltip patches WAY easier to handle
    r.fillna(method='ffill', inplace=True)

    # Hack! But it works. Need to do this *before* you create cds below!
    #   Includes a special flag (first=True) to pad the beginning so all
    #   the columns in the final ColumnDataSource are the same length
    pix, piy = bplot.makePatches(r.index, y1lim, first=True)

    # The "master" data source to be used for plotting.
    #    I wish there was a way of abstracting this but I'm not
    #    clever enough. Make the dict in a loop using
    #    the data keys? I dunno. "Future Work" for sure.

    mds = dict(index=r.index,
               CCDDeveny=r.CCDTemp_deveny, CCDLMI=r.CCDTemp_lemi,
               AUXDeveny=r.AUXTemp_deveny, AUXLMI=r.AUXTemp_lemi,
               pix=pix, piy=piy)
    cds = ColumnDataSource(mds)

    # Make the plots/lines!
    l1, _ = bplot.plotLineWithPoints(fig, cds, "CCDDeveny", dset[0])
    l2, _ = bplot.plotLineWithPoints(fig, cds, "CCDLMI", dset[1])
    l3, _ = bplot.plotLineWithPoints(fig, cds, "AUXDeveny", dset[2])
    l4, _ = bplot.plotLineWithPoints(fig, cds, "AUXLMI", dset[3])

    li1 = LegendItem(label="CCDDeveny", renderers=[l1])
    li2 = LegendItem(label="CCDLMI", renderers=[l2])
    li3 = LegendItem(label="AUXDeveny", renderers=[l3])
    li4 = LegendItem(label="AUXLMI", renderers=[l4])
    legend = Legend(items=[li1, li2, li3, li4],
                    location="bottom_center",
                    orientation='horizontal', spacing=15)
    fig.add_layout(legend, 'below')

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
                   ("CCDDeveny", "@CCDDeveny{0.0} C"),
                   ("CCDLMI", "@CCDLMI{0.0} C"),
                   ("AUXDeveny", "@AUXDeveny C"),
                   ("AUXLMI", "@AUXLMI{0.0} C"),
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

        # Turn it into a datetime.datetime (with UTC timezone)
        lastTimedt = bplot.convertTimestamp(lastTime, tz='UTC')

        # Grab the newest data from the master query dictionary
        pdata = OrderedDict()
        for qtag in m.queries.keys():
            pdata.update({qtag: qdata[qtag]})

        # Update the data references; these are actual DataFrame objects btw.
        r = pdata['q_insttemps']['deveny']
        r2 = pdata['q_insttemps']['lemi']

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
            # At this point, there might be a NaN in the column(s) from rf2.
            #   Since we stream only the NEW values, we need to be nice to
            #   ourselves and fill in the prior value for those columns so
            #   the tooltips function and don't spaz out. So get the final
            #   values manually and then fill them into those columns.
            cfills = {}
            fillVal1 = bplot.getLastVal(cds, 'CCDDeveny')
            fillVal2 = bplot.getLastVal(cds, 'CCDLMI')
            fillVal3 = bplot.getLastVal(cds, 'AUXDeveny')
            fillVal4 = bplot.getLastVal(cds, 'AUXLMI')
            cfills.update({"CCDDeveny": fillVal1,
                           "CCDLMI": fillVal2,
                           "AUXDeveny": fillVal3,
                           "AUXLMI": fillVal4})

            # Now join the dataframes into one single one that we can stream.
            #   Remember to use 'outer' otherwise information will be
            #   mutilated since the two dataframes are on two different
            #   time indicies!
            nf = rf.join(rf2, how='outer', lsuffix='_deveny', rsuffix='_lemi')

            # Need to make sure that the column names in the dataframe
            #   actually match those that we set in the
            #   original ColumnDataSource
            nf.rename(columns={"CCDTemp_deveny": "CCDDeveny",
                               "CCDTemp_lemi": "CCDLMI",
                               "AUXTemp_deveny": "AUXDeveny",
                               "AUXTemp_lemi": "AUXLMI"},
                      inplace=True)

            # Fill in our column holes. If there are *multiple* temporal holes,
            #   it'll look bonkers because there's only one fill value.
            nf.fillna(value=cfills, inplace=True)

            # Create the patches for the *new* data only
            nix, niy = bplot.makeNewPatches(nf, y1lim, lastTimedt)

            # It is VITALLY important that the length of all of these
            #   is the same! If it's not, it'll slowly go bonkers.
            # Could add a check to make sure here, but I'll ride dirty for now.
            mds2 = dict(index=nf.index,
                        CCDDeveny=nf.CCDDeveny,
                        CCDLMI=nf.CCDLMI,
                        AUXDeveny=nf.AUXDeveny,
                        AUXLMI=nf.AUXLMI,
                        pix=nix, piy=niy)

            cds.stream(mds2, rollover=15000)
            print("New data streamed; %d row(s) added" % (nf.shape[0]))

        print("Range now: %s to %s" % (fig.x_range.start, fig.x_range.end))
        print("")


    doc.add_periodic_callback(grabNew, 5000)

    return doc
