# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 16 Nov 2018
#
#  @author: rhamilton

"""Actually plot the GOES-16 data.
"""

from __future__ import division, print_function, absolute_import

import glob

import os
from datetime import datetime as dt

import numpy as np

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches

import pyart.graph.cm as pyartcm
from pyart.io import read_nexrad_archive
from pyart.graph import RadarMapDisplay

from metpy.io import Level2File
from metpy.plots import colortables

import cartopy.crs as ccrs
import cartopy.feature as cfeat
import cartopy.io.shapereader as cshape


def readNEXRAD(filename):
    """
    """
    print("Reading: %s" % (filename))
    dat = read_nexrad_archive(filename, linear_interp=False)
    print("Done reading!")

    return dat


def set_plot_extent(clat, clon):
    # pr.plot.show_quicklook(old_grid, data, coast_res='10m')

    # Output grid centered on clat, clon
    # latWid = 3.5
    # lonWid = 3.5
    # lonMin = clon - lonWid
    # lonMax = clon + lonWid
    # latMin = clat - latWid
    # latMax = clat + latWid

    # Handpicked favorites; generates all of AZ centered on the DCT
    # latWid = 3.5
    # lonWid = 3.5
    # lonMin = clon - lonWid
    # lonMax = clon + lonWid - 1.0
    # latMin = clat - latWid
    # latMax = clat + latWid - 0.75

    # Zoomed in portion around the DCT, showing an approximate radius
    #   of 'desiredRadius' statute miles.
    # To do this right it's easier to think in terms of nautical miles;
    #   See https://github.com/LowellObservatory/Camelot/issues/5 for the math.

    # In *statute miles* since they're easier to measure (from Google Maps)
    # desiredRadius = 150.
    desiredRadius = 150.

    # Now it's in nautical miles so we just continue
    dRnm = desiredRadius/1.1507794
    latWid = dRnm/60.
    lonWid = dRnm/(np.cos(np.deg2rad(clat))*60.)

    # Small fudge factor to make the aspect a little closer to 1:1
    latWid += 0.053

    print(latWid, lonWid)

    lonMin = clon - lonWid
    lonMax = clon + lonWid
    latMin = clat - latWid
    latMax = clat + latWid

    return latMin, latMax, lonMin, lonMax


def add_map_features(ax, roads=None):
    ax.add_feature(cfeat.COASTLINE.with_scale('10m'))
    ax.add_feature(cfeat.BORDERS.with_scale('10m'))

    # Slightly transparent rivers
    ax.add_feature(cfeat.RIVERS.with_scale('10m'),
                   alpha=0.75, edgecolor='aqua')

    # Dotted lines for state borders
    ax.add_feature(cfeat.STATES.with_scale('10m'),
                   linestyle=":", edgecolor='black')

    if roads is not None:
        # Reminder that roads is a dict with keys:
        #  interstates, fedroads, stateroads, otherroads
        for rtype in roads:
            good = True
            if rtype == "Interstate":
                rcolor = 'gold'
                ralpha = 0.55
            elif rtype == "Federal":
                rcolor = 'gold'
                ralpha = 0.55
            elif rtype == 'State':
                rcolor = 'LightSkyBlue'
                ralpha = 0.55
            elif rtype == "Other":
                rcolor = 'LightSkyBlue'
                ralpha = 0.45
            else:
                good = False

            # Only plot the ones specifed above; if it doesn't fit one of
            #   those categories then skip it completely because something
            #   is wrong or changed.
            if good is True:
                sfeat = cfeat.ShapelyFeature(roads[rtype], ccrs.PlateCarree())
                ax.add_feature(sfeat, facecolor='none',
                               edgecolor=rcolor, alpha=ralpha)

    return ax


def parseRoads(rclasses):
    """
    See https://www.naturalearthdata.com/downloads/10m-cultural-vectors/roads/
    for field information; below is just a quick summary.

    CLASS:
        Interstate (Interstates and Quebec Autoroutes)
        Federal (US Highways, Mexican Federal Highways, Trans-Canada Highways)
        State (US State, Mexican State, and Canadian Provincial Highways)
        Other (any other road class)
        Closed (road is closed to public)
        U/C (road is under construction)
    TYPE:
        Tollway
        Freeway
        Primary
        Secondary
        Other Paved
        Unpaved
        Winter (ice road, open winter only)
        Trail
        Ferry
    """
    rds = cshape.natural_earth(resolution='10m',
                               category='cultural',
                               name='roads_north_america')

    rdsrec = cshape.Reader(rds)

    rdict = {}
    # A dict is far easier to interact with so make one
    for rec in rdsrec.records():
        for key in rclasses:
            if rec.attributes['class'] == key:
                try:
                    rdict[key].append(rec.geometry)
                except KeyError:
                    # This means the key hasn't been created yet so make it
                    #   and then fill it with the value.
                    #   It should then work fine the next time
                    rdict.update({key: [rec.geometry]})

    return rdict


def add_AZObs(ax):
    """
    Hardcoded this for now, with a Lowell/Mars Hill getting a "*" marker.

    Would be easy to pass in a dict of locations and marker/color info too
    and just loop through that, but since I only have 5 now it's no big deal.
    """
    # Lowell
    ax.plot(-111.664444, 35.202778, marker='*', color='red',
            markersize=8, alpha=0.95, transform=ccrs.Geodetic())

    # DCT
    ax.plot(-111.4223, 34.7443, marker='o', color='red', markersize=6,
            alpha=0.95, transform=ccrs.Geodetic())

    # Anderson Mesa
    ax.plot(-111.535833, 35.096944, marker='o', color='red',
            markersize=6, alpha=0.95, transform=ccrs.Geodetic())

    # KPNO
    ax.plot(-111.5967, 31.9583, marker='o', color='purple',
            markersize=5, alpha=0.95, transform=ccrs.Geodetic())

    # LBT
    ax.plot(-109.889064, 32.701308, marker='o', color='purple',
            markersize=5, alpha=0.95, transform=ccrs.Geodetic())

    # MMT
    ax.plot(-110.885, 31.6883, marker='o', color='purple',
            markersize=5, alpha=0.95, transform=ccrs.Geodetic())

    return ax


def getCmap():
    # Pulled by hand from the NWS NEXRAD plots
    ct = ["#ccffff", "#cc99cc", "#996699", "#663366", "#cccc99", "#999966",
          "#646464", "#04e9e7", "#019ff4", "#0300f4", "#02fd02", "#01c501",
          "#008e00", "#fdf802", "#e5bc00", "#fd9500", "#fd0000", "#d40000",
          "#bc0000", "#f800fd", "#9854c6", "#fdfdfd"]
    cl = range(-30, 75, 5)
    nwsref = mcolors.from_levels_and_colors(cl, ct, extend='both')
    nwsref[0].name = "NWSRefNoND"

    return nwsref


def literallyDeBug(radar, vcpmode):
    """
    Apply rudimentary quality control, as done in the example by
    Valliappa Lakshmanan.

    See the full notebook at:
    https://github.com/lakshmanok/nexradaws/blob/master/nexrad_sample.ipynb

    This is also helpful:
    https://www.radarscope.app/guide/radarscope-products-dual-polarization

    As is this:
    https://www.ncdc.noaa.gov/data-access/radar-data/nexrad-products

    Differential Reflectivity (ZDR) values are measurements related to the
    returned energy difference between the vertical and horizontal radar
    pulses. Large positive values indicate that targets are generally much
    larger horizontally than vertically. Values near zero indicate the
    targets are generally spherical. Negative values indicate targets are
    larger in the vertical than in the horizontal.

    Correlation Coefficient (RHO_hv) values are measurements related to
    the similarity between the behaviors of the horizontally and vertically
    polarized pulses and how they are behaving within a pulse volume.
    Values between 0.95 and 1.0 indicate near uniformity in pulse behavior.
    Meteorological targets with complex shapes, or with a large degree of
    variety, will generally have values between 0.85 and 0.95.
    Biological targets, anthropogenic targets, and ground clutter tend to
    cause very different behaviors between the pulses, resulting in values
    less than 0.9 (and often less than 0.7).
    """
    refl_grid = radar.get_field(0, 'reflectivity')
    rhohv_grid = radar.get_field(0, 'cross_correlation_ratio')
    zdr_grid = radar.get_field(0, 'differential_reflectivity')

    # Reflectivity values less than some cutoff point
    #   value originally was 20
    # The logic below attempts to account for the radar scan operating
    #   in "Clear Air Mode" which can result in valid values < 0.  If that's
    #   the scan type, we set a super low bar for reflectivity filtering
    #   otherwise we choose a low-ish value to try to eliminate fuzziness
    if vcpmode in [31, 32, 35]:
        refCutVal = -40
    else:
        refCutVal = 5
    refLow = np.less(refl_grid, refCutVal)

    # Differential reflectivity greater than some cutoff point
    #   Note that this is doing abs() first, so it's filtering out both ends
    #   value originally was 2.3
    zdrCut = np.greater(np.abs(zdr_grid), 2.0)

    # Cross correlation values below a threshold
    #   value originally was 0.95
    rhohvLow = np.less(rhohv_grid, 0.90)

    # Combine all of the above into a master mask array. Flag values where:
    #   Reflectivity < cutoff OR (DifferentialReflectivity is high OR
    #                             CrossCorrelationRatio is low)
    notweather = np.logical_or(refLow, np.logical_or(zdrCut, rhohvLow))

    # Generate the masked array from the above
    qcrefl_grid = np.ma.masked_where(notweather, refl_grid)

    qced = radar.extract_sweeps([0])
    qced.add_field_like('reflectivity', 'reflectivity_masked', qcrefl_grid)

    return qced


def makePlots(inloc, outloc, roads=None, cmap=None, forceRegen=False):
    # Warning, you may explode
    #  https://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.switch_backend
    plt.switch_backend("Agg")

    cLat = 34.7443
    cLon = -111.4223

    flist = sorted(glob.glob(inloc + "/*"))

    if roads is None:
        rclasses = ["Interstate", "Federal"]
        # rclasses = ["Interstate", "Federal", "State", "Other"]

        # On the assumption that we'll plot something, downselect the full
        #   road database into the subset we want
        print("Parsing road data...")
        print("\tClasses: %s" % (rclasses))

        # roads will be a dict with keys of rclasses and values of geometries
        roads = parseRoads(rclasses)
        print("Roads parsed!")

    if cmap is None:
        cmap = getCmap()

    # i is the number-of-images processed counter
    i = 0
    for each in flist:
        outpname = "%s/%s.png" % (outloc, os.path.basename(each))

        # Logic to skip stuff already completed, or just redo everything
        if forceRegen is True:
            save = True
        else:
            # Check to see if we're already done with this image
            found = os.path.isfile(outpname)

            if found is True:
                save = False
                print("File %s exists! Skipping." % (outpname))
            else:
                save = True

        if save is True:
            radar = readNEXRAD(each)

            # Pull out the identifiers
            site = radar.metadata['instrument_name']
            siteLat = radar.latitude['data'][0]
            siteLon = radar.longitude['data'][0]

            dprod = radar.metadata['original_container']

            # Get the VCP mode (specific radar scan mode); see also:
            # https://www.weather.gov/jetstream/vcp_max
            vcpmode = radar.metadata['vcp_pattern']

            # Pull out the time stamp; skip the site name
            fullts = os.path.basename(each)[4:]
            tend = dt.strptime(fullts, "%Y%m%d_%H%M%S")

            # Filter out crud that is probably bugs and stuff,
            #   good enough for what we're doing
            print("Debugging...")
            qcradar = literallyDeBug(radar, vcpmode)
            print("Debugging complete!")
            display = RadarMapDisplay(qcradar, )

            latMin, latMax, lonMin, lonMax = set_plot_extent(cLat, cLon)

            # Get the projection info for the plot axes
            crs = ccrs.LambertConformal(central_latitude=siteLat,
                                        central_longitude=siteLon)

            # Get the proper plot extents so we have no whitespace
            prlon = (crs.x_limits[1] - crs.x_limits[0])
            prlat = (crs.y_limits[1] - crs.y_limits[0])
            # Ultimate image width/height
            paspect = prlon/prlat

            # !!! WARNING !!!
            #   I hate this kludge, but it works if you let the aspect stretch
            #   just a tiny bit. Necessary for the MP4 creation because the
            #   compression algorithm needs an even number divisor
            # figsize = (7., np.round(7./paspect, decimals=2))
            figsize = (7., 7.)

            print(prlon, prlat, paspect)
            print(figsize)

            # Figure creation
            fig = plt.figure(figsize=figsize, dpi=100)

            # Needed to remove any whitespace/padding around the imshow()
            plt.subplots_adjust(left=0., right=1., top=1., bottom=0.)

            # Tell matplotlib we're using a map projection so cartopy
            #   takes over and overloades Axes() with GeoAxes()
            ax = plt.axes(projection=crs)

            ax.background_patch.set_facecolor('#262629')

            # Some custom stuff
            ax = add_map_features(ax, roads=roads)
            ax = add_AZObs(ax)

            # Clear out the crap on the edges
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.set_xticklabels([])
            ax.set_yticklabels([])

            print("Plotting radar data...")
            display.plot_ppi_map('reflectivity_masked',
                                 mask_outside=True,
                                 min_lon=lonMin, max_lon=lonMax,
                                 min_lat=latMin, max_lat=latMax,
                                 projection=crs,
                                 fig=fig,
                                 cmap=cmap[0],
                                 norm=cmap[1],
                                 lat_0=siteLat,
                                 lon_0=siteLon,
                                 embelish=False,
                                 colorbar_flag=False,
                                 title_flag=False,
                                 ticklabs=[],
                                 ticks=[],
                                 lat_lines=[],
                                 lon_lines=[],
                                 raster=True)

            display.plot_point(siteLon, siteLat, symbol='^', color='orange')
            print("Plotting complete! Finishing up...")

            # plt.colorbar()

            # Add the informational bar at the top, using info directly
            #   from the original datafiles that we opened at the top
            line1 = "%s  %s  Filtered Reflectivity" % (site, dprod)
            line1 = line1.upper()

            # We don't need microseconds shown on this plot
            tendstr = tend.strftime("%Y-%m-%d  %H:%M:%SZ")
            line2 = "VCP MODE %03d  %s" % (vcpmode, tendstr)
            line2 = line2.upper()

            # Black background for top label text
            #   NOTE: Z order is important! Text should be higher than trect
            trect = mpatches.Rectangle((0.0, 0.955), width=1.0, height=0.045,
                                       edgecolor=None, facecolor='black',
                                       fill=True, alpha=1.0, zorder=100,
                                       transform=ax.transAxes)
            ax.add_patch(trect)

            # Line 1
            plt.annotate(line1, (0.5, 0.985), xycoords='axes fraction',
                         fontfamily='monospace',
                         horizontalalignment='center',
                         verticalalignment='center',
                         color='white', fontweight='bold', zorder=200)
            # Line 2
            plt.annotate(line2, (0.5, 0.965), xycoords='axes fraction',
                         fontfamily='monospace',
                         horizontalalignment='center',
                         verticalalignment='center',
                         color='white', fontweight='bold', zorder=200)

            # Useful for testing getCmap changes
            # plt.colorbar()

            print("Saving...")
            plt.savefig(outpname, dpi=100, facecolor='black', frameon=True)
            print("Saved as %s." % (outpname))
            plt.close()

            i += 1
            print("%d plots complete" % (i))

    return i
