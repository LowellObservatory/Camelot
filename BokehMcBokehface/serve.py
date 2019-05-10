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

from datetime import datetime as dt
from collections import OrderedDict

from bokeh.themes import Theme
from bokeh.util import logconfig
from bokeh.plotting import curdoc
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler

from tornado.ioloop import PeriodicCallback

import ephem
import numpy as np
import pandas as pd
from pytz import timezone

import dctplots.confHerder as ch
import dctplots.dbQueries as dbq
import dctplots.colorWheelies as cwheels

from dctplots import dctWeather, instrumentTelem, facsums


# Make sure all the endpoints work from the same base document.
#   This is also where we stash the plot data
doc = curdoc()


class masterPlotState():
    def __init__(self):
        self.data = None
        self.theme = None
        self.colors = None
        self.modules = None
        self.queries = None
        self.timestamp = None


class observingSite():
    def __init__(self, sitename='dct'):
        self.eObserver = None
        self.sunmoon = None

        if sitename.lower() == 'dct':
            # Remaking the observer here updates the time automagically for us.
            #   Could change the date/time manually, but this is fine for now.
            self.eObserver = ephem.Observer()
            self.eObserver.lat = '34.7443'
            self.eObserver.lon = '-111.4223'
            self.eObserver.elevation = 2361
            self.eObserver.name = "Lowell Observatory DCT"

            # Go ahead and calculate all the angles/times we care about
            self.sunmoon = solarsystemAngles(self.eObserver)
        else:
            print("UNKNOWN OBSERVATORY SITE! ABORTING.")
            raise NotImplementedError

    def toPandasDataFrame(self):
        """
        Convienent way to pack up the things we care about into a Pandas
        DataFrame for stashing elsewhere
        """
        colNames = ['sunrise', 'nextsunrise',
                    'sunset', 'nextsunset',
                    'sun_dms', 'moon_dms', 'moonphase']

        # Loop over these and make a dict as we go
        ddict = {}
        for col in colNames:
            entry = {col: getattr(self.sunmoon, col)}
            ddict.update(entry)

        # Thankfully, pyephem always uses UTC. So add that tzinfo just
        #   so we can compare stuff without warnings/exceptions later on
        index = self.eObserver.date.datetime()
        storageTZ = timezone('UTC')
        index = index.replace(tzinfo=storageTZ)

        return pd.DataFrame(data=ddict, index=[index])


class solarsystemAngles():
    def __init__(self, obssite, autocalc=True):
        self.site = obssite

        self.sun = ephem.Sun()
        self.sun_alt = None
        self.sun_dms = None
        self.sunrise = None
        self.nextsunrise = None
        self.sunset = None
        self.nextsunset = None

        self.moon = ephem.Moon()
        self.moon_alt = None
        self.moon_dms = None
        self.moonphase = None

        if autocalc is True:
            self.updateSunInfo()
            self.updateMoonInfo()

    def updateSunInfo(self):
        """
        """
        self.sun.compute(self.site)
        self.sun_alt = self.sun.alt
        self.sun_dms = np.degrees(ephem.degrees(self.sun_alt))
        self.sunrise = self.sun.rise_time.datetime()
        self.nextsunrise = self.site.next_rising(self.sun).datetime()
        self.sunset = self.sun.set_time.datetime()
        self.nextsunset = self.site.next_setting(self.sun).datetime()

    def updateMoonInfo(self):
        """
        """
        self.moon.compute(self.site)
        self.moon_alt = self.moon.alt
        self.moon_dms = np.degrees(ephem.degrees(self.moon_alt))
        self.moonphase = self.moon.moon_phase


def batchQuery(plotState=None, site='dct'):
    """
    It's important to do all of these queries en-masse, otherwise the results
    could end up being confusing - one plot's data could differ by
    one (or several) update cycle times eventually, and that could be super
    confusing and cause users to think that things like coordinates are
    not right when it's really just our view of them that has drifted.

    By doing them all at once or in quick succession, it's more likely
    that we'll capture the same instantaneous 'state' of the telescope/site.
    """
    qdata = OrderedDict()

    if plotState is None:
        quer = doc.template.globals['plotState'].queries
    else:
        quer = plotState.queries

    for iq in quer.keys():
        q = quer[iq]

        # Should not only pull this out of the loop, but change it to
        #   use 'bind_params' for extra safety!
        query = dbq.queryConstructor(q, dtime=q.rn)

        td = dbq.getResultsDataFrame(q.db.host, query,
                                     q.db.port,
                                     dbuser=q.db.user,
                                     dbpass=q.db.pasw,
                                     dbname=q.db.tabl,
                                     datanames=q.dn)
        qdata.update({iq: td})

    dts = dt.utcnow()
    print("%d queries complete!" % (len(qdata)))

    # Create pyEphem object at the above for the current time
    #   Doing it in a class so it can also contain the solarsystemAngles too
    #   along with anything else we decide we need later on
    obsSite = observingSite(sitename=site)

    # Translate all those times and angles into a dataframe that we can
    #   then stuff into our hiding spot with all the other things
    edf = obsSite.toPandasDataFrame()

    qdata.update({'ephemera': edf})

    print("Data stored at %s" % (dts))

    # Put the plotState into the server document root so the plotting routines
    #   can actually access the stuff they need
    # TODO: Figure this shit out.
    if plotState is not None:
        # Update our class, then stash it
        plotState.data = qdata
        plotState.timestamp = dts

        # Here's the sneaky stash!
        doc.template.globals.update({'plotState': plotState})
        print("Data stashed in doc.template.globals.")
    else:
        # We already stashed, so just update the changed bits
        doc.template.globals['plotState'].data = qdata
        doc.template.globals['plotState'].timestamp = dts


def configServer():
    """
    """
    # LOOP OVER THE CONFIG TO MAKE THIS
    dctWeatherFunc = FunctionHandler(dctWeather.make_plot)
    dctWeatherApp = Application(dctWeatherFunc)

    lmiTempFunc = FunctionHandler(instrumentTelem.make_plot)
    lmiTempApp = Application(lmiTempFunc)

    facsumTCSFunc = FunctionHandler(facsums.makeFacSum_TCS)
    facsumTCSApp = Application(facsumTCSFunc)

    facsumLPIFunc = FunctionHandler(facsums.makeFacSum_LPI)
    facsumLPIApp = Application(facsumLPIFunc)

    apps = {'/dctweather': dctWeatherApp,
            '/lmitemps': lmiTempApp,
            '/facsum_tcs': facsumTCSApp,
            '/facsum_lpi': facsumLPIApp}

    print("Starting bokeh server...")
    server = Server(apps, port=5000,
                    allow_websocket_origin=['localhost:5000',
                                            'dctsleeperservice:5000',
                                            'dctsleeperservice:9876',
                                            'nightwatch',
                                            'nightwatch.lowell.edu'])

    return server


if __name__ == "__main__":
    # Can spin these off to configParser things later
    qconff = './config/dbqueries.conf'
    mconff = './config/modules.conf'
    themefile = "./config/bokeh_dark_theme.yml"

    # Parse the configuration files
    #   'mods' is a list of ch.moduleConfig objects.
    #   'quer' is a list of all the active database sections associated
    mods, quer = ch.parser(qconff, mconff)

    # Create the bokeh theme object to be applied in the actual documents
    theme = Theme(filename=themefile)

    # Get the default color sets; second one is sorted by hue but
    #   I'm ditching it since I'm not using it
    dset, _ = cwheels.getColors()

    # Set up logging to a file
    # TODO: Just use my standard ligmos logger to grab everything?
    #   Initial attempt failed because python logging is really weird
    print("Sending the output to the file")
    logconfig.basicConfig(level='DEBUG',
                          format='%(asctime)s %(levelname)-8s %(message)s',
                          filename='./logs/bokehmcbokehface.log')

    # Now pack it all into a nice class that can be added to the
    #   main doc to be inherited by each plot that we make
    plotState = masterPlotState()

    # TODO: Make this possible in __init__ by passing in **kwargs
    plotState.theme = theme
    plotState.colors = dset
    plotState.modules = mods
    plotState.queries = quer

    # Go and get our initial state of data. Give it the masterPlotState
    #   class so it can be initially stashed in the doc template
    batchQuery(plotState=plotState)

    # Set up the server
    server = configServer()

    # Set up the data-refreshing periodic callback
    # NOTE: jitter=0.1 means the callback will be called at intervals +- 10%
    #   to avoid constant clashes with other periodic processes
    pcallback = PeriodicCallback(batchQuery, 60000, jitter=0.1)
    print("Starting server ioloop periodic callback")
    pcallback.start()

    # Actually start the server
    server.start()
    server.io_loop.start()
