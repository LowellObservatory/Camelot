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

from bokeh.plotting import ColumnDataSource
from bokeh.models import Legend, LegendItem

from . import modulePlots as bplot


def dataGatherer(m, qdata, timeFilter=None, fillNull=True, debug=True):
    """
    Instrument/plot/query specific contortions needed to make the
    bulk of the plot code generic and abstract.  I feel ok
    hardcoding stuff in here at least, since this will always be namespace
    protected and unambigious (instrumentTelem.dataGatherer).
    """
    pdata = OrderedDict()
    for qtag in m.queries.keys():
        pdata.update({qtag: qdata[qtag]})

    # Get the keys that define the input dataset
    r = pdata['q_insttemps']['deveny']
    r2 = pdata['q_insttemps']['lemi']

    # Since it was a batch query, we need to add prefixes to each
    #   so we know what they are after joining
    r = r.add_prefix("Deveny")
    r2 = r2.add_prefix("LMI")

    if timeFilter is None:
        # Join them so the timestamps are sorted for us nicely, and nan's
        #   put into the gaps so we don't get all confused later on
        rj = r.join(r2, how='outer')

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

        if debug is True:
            print("Last in CDS: %s" % (timeFilter))
            print("Last in r  : %s" % (ripydt[-1]))
            print("Last in r2 : %s" % (r2ipydt[-1]))

        rTimeSearchMask = ripydt > timeFilter
        r2TimeSearchMask = r2ipydt > timeFilter

        # Need .loc since we're really filtering by label
        rf = r.loc[rTimeSearchMask]
        rf2 = r2.loc[r2TimeSearchMask]

        # Now join the dataframes into one single one that we can stream.
        #   Remember to use 'outer' otherwise information will be
        #   mutilated since the two dataframes are on two different
        #   time indicies!
        rj = rf.join(rf2, how='outer')

    return rj


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
    # Ultimately, I need to combine mods and qdata into a single dict
    #   and select based on that.  But that can come later.
    m = mods[2]

    print("Serving %s" % (m.title))

    # Use this to consistently filter/gather the data based on some
    #   specific tags/reorganizing
    r = dataGatherer(m, qdata)

    # A dict of helpful plot labels
    ldict = {'title': "Instrument Temperatures",
             'xlabel': "Time (UTC)",
             'y1label': "Temperature (C)"}

    fig = bplot.commonPlot(ldict, height=400, width=600)

    # Since we haven't plotted anything yet, we don't have a decent idea
    #   of the bounds that we make our patches over. So just do that manually.
    # Remember that .min and .max are methods! Need the ()
    #   Also adjust plot extents to pad +/- N percent
    npad = 0.1
    y1lim = None
    if y1lim is None:
        y1lim = [r.LMICCDTemp.min(skipna=True),
                 r.LMIAUXTemp.max(skipna=True)]

        # Now pad them appropriately, checking for a negative limit
        if y1lim[0] < 0:
            y1lim[0] *= (1.+npad)
        else:
            y1lim[0] *= (1.-npad)

        if y1lim[1] < 0:
            y1lim[1] *= (1.-npad)
        else:
            y1lim[1] *= (1.+npad)

    #
    # NOTE: At this point, the *rest* of the code is more or less
    #   completely generic and should be function-ed out!
    #

    fig.x_range.follow = "end"
    fig.x_range.range_padding = 0.1
    fig.x_range.range_padding_units = 'percent'

    # Hack! But it works. Need to do this *before* you create cds below!
    #   Includes a special flag (first=True) to pad the beginning so all
    #   the columns in the final ColumnDataSource are the same length
    pix, piy = bplot.makePatches(r.index, y1lim, first=True)

    # The "master" data source to be used for plotting.
    #   Generate it via the column names in the now-merged 'r' DataFrame
    #   Start with the 'index' 'pix' and 'piy' since they're always those names
    mds = dict(index=r.index, pix=pix, piy=piy)

    # Start our plot source
    cds = ColumnDataSource(mds)

    # Now loop over the rest of our columns to fill it out, plotting as we go
    cols = r.columns
    lineSet = []
    legendItems = []
    for i, col in enumerate(cols):
        # Add our data to the cds
        cds.add(getattr(r, col), name=col)

        # Make the actual line plot object
        lineObj, _ = bplot.plotLineWithPoints(fig, cds, col, dset[i])
        lineSet.append(lineObj)

        # Now make it's corresponding legend item
        legendObj = LegendItem(label=col, renderers=[lineObj])
        legendItems.append(legendObj)

    legend = Legend(items=legendItems,
                    location="bottom_center",
                    orientation='horizontal', spacing=15)
    fig.add_layout(legend, 'below')

    # Customize the active tools
    fig.toolbar.autohide = True

    # HACK HACK HACK HACK HACK
    #   Apply the patches to carry the tooltips
    #
    # Shouldn't I just stream this instead of pix/nix and piy/niy ???
    #
    simg = fig.patches('pix', 'piy', source=cds,
                       fill_color=None,
                       fill_alpha=0.0,
                       line_color=None)

    # This will also create the tooltips for each of the entries in cols
    ht = bplot.createHoverTool(simg, cols)
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

        # Sweep up all the data, and filter down to only those
        #   after the given time
        nf = dataGatherer(m, qdata, timeFilter=lastTimedt)

        if nf.size == 0:
            print("No new data.")
        else:
            # At this point, there might be a NaN in the column(s) from rf2.
            #   Since we stream only the NEW values, we need to be nice to
            #   ourselves and fill in the prior value for those columns so
            #   the tooltips function and don't spaz out. So get the final
            #   values manually and then fill them into those columns.
            cfills = {}
            for col in cols:
                fillVal = bplot.getLastVal(cds, col)
                cfills.update({col: fillVal})

            # Fill in our column holes. If there are *multiple* temporal holes,
            #   it'll look bonkers because there's only one fill value.
            nf.fillna(value=cfills, inplace=True)

            # Create the patches for the *new* data only
            nix, niy = bplot.makeNewPatches(nf, y1lim, lastTimedt)

            # It is VITALLY important that the length of all of these
            #   is the same! If it's not, it'll slowly go bonkers.
            #
            # Could add a check to make sure here, but I'll ride dirty for now.
            mds2 = dict(index=nf.index, pix=nix, piy=niy)
            for col in cols:
                mds2.update({col: getattr(nf, col)})

            cds.stream(mds2, rollover=15000)
            print("New data streamed; %d row(s) added" % (nf.shape[0]))

        print("Range now: %s to %s" % (fig.x_range.start, fig.x_range.end))
        print("")

    doc.add_periodic_callback(grabNew, 5000)

    return doc
