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
import pyresample as pr
from netCDF4 import Dataset
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import cartopy.crs as ccrs
import cartopy.feature as cfeat


def readNC(filename):
    """
    """
    print("Reading: %s" % (filename))
    dat = Dataset(filename)

    return dat


def G16_ABI_L2_ProjDef(nc):
    """
    """
    # The key is that the GOES-16 data are in a geostationary projection
    #   and those details are available in:
    #     dat.variables['goes_imager_projection']
    # See also:
    #     https://proj4.org/operations/projections/geos.html
    proj_var = nc.variables['goes_imager_projection']
    print(proj_var)

    # Since scanning_angle (radians) = projection_coordinate / h,
    #   the projection coordinates are now easy to get.
    satH = proj_var.perspective_point_height
    satLat = proj_var.latitude_of_projection_origin
    satLon = proj_var.longitude_of_projection_origin
    satSweep = proj_var.sweep_angle_axis
    semi_major = proj_var.semi_major_axis
    semi_minor = proj_var.semi_minor_axis

    x = (nc.variables['x'][:])*satH
    y = (nc.variables['y'][:])*satH

    nx = len(x)
    ny = len(y)

    min_x = x.min()
    max_x = x.max()
    min_y = y.min()
    max_y = y.max()

    # NOTE:
    #   Currently don't know why the google example offsets by half_x/y...
    half_x = (max_x - min_x) / nx / 2.
    half_y = (max_y - min_y) / ny / 2.
    extents = (min_x - half_x, min_y - half_y, max_x + half_x, max_y + half_y)

    # Props to
    #  https://groups.google.com/forum/#!topic/pytroll/EIl0voQDqiI
    #  for pointing out that 'sweep' definition is important!!!
    old_grid = pr.geometry.AreaDefinition('geos', 'goes_conus', 'geos',
                                          {'proj': 'geos',
                                           'h': str(satH),
                                           'lon_0': str(satLon),
                                           'lat_0': str(satLat),
                                           'a': str(semi_major),
                                           'b': str(semi_minor),
                                           'units': 'm',
                                           'ellps': 'GRS80',
                                           'sweep': satSweep},
                                          nx, ny, extents)

    return old_grid


def crop_image(nc, data, clat, clon, latWid=3.5, lonWid=3.5):
    # Parse/grab the existing projection information
    old_grid = G16_ABI_L2_ProjDef(nc)

    # pr.plot.show_quicklook(old_grid, data, coast_res='10m')

    # Output grid centered on clat, clon. Symmetric in each extent
    #   though not necessarily symmetric in Lat/Lon
    lonMin = clon - lonWid
    lonMax = clon + lonWid
    latMin = clat - latWid
    latMax = clat + latWid

    lats = np.arange(latMin, latMax, 0.005)
    lons = np.arange(lonMin, lonMax, 0.005)
    lons, lats = np.meshgrid(lons, lats)

    swath_def = pr.geometry.SwathDefinition(lons=lons, lats=lats)

    area_def = swath_def.compute_optimal_bb_area({'proj': 'lcc',
                                                  'lon_0': clon,
                                                  'lat_0': clat,
                                                  'lat_1': clat,
                                                  'lat_2': clat})

    # now do remapping
    print('Remapping from {}'.format(old_grid))

    pData = pr.kd_tree.resample_nearest(old_grid, data, area_def,
                                        radius_of_influence=5000)

    return old_grid, area_def, pData


def add_map_features(ax):
    ax.add_feature(cfeat.COASTLINE.with_scale('10m'))
    ax.add_feature(cfeat.BORDERS.with_scale('10m'))

    # Slightly transparent rivers
    ax.add_feature(cfeat.RIVERS.with_scale('10m'),
                   alpha=0.75, edgecolor='aqua')

    # Dotted lines for state borders
    ax.add_feature(cfeat.STATES.with_scale('10m'),
                   linestyle=":", edgecolor='black')

    return ax


def add_AZObs(ax):
    """
    Hardcoded this for now, with a Lowell/Mars Hill getting a "*" marker
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


if __name__ == "__main__":
    cLat = 34.7443
    cLon = -111.4223
    dctAlt = 2361
    gamma = 2.2
    forceRegen = False
    inloc = './GOESMcGOESface/data/'

    # Additional shapefiles (if desired)


    flist = sorted(glob.glob(inloc + "*.nc"))

    for each in flist:
        outpname = "./GOESMcGOESface/pngs/%s.png" % (os.path.basename(each))

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
            dat = readNC(each)

            # Pull out the channel/band and other identifiers
            chan = dat.variables['band_id'][0]
            plat = "%s (%s)" % (dat.orbital_slot, dat.platform_ID)
            dprod = dat.title

            # Pull out the time stamp
            tend = dt.strptime(dat.time_coverage_end,
                               "%Y-%m-%dT%H:%M:%S.%fZ")

            # Grab just the image data & quickly gamma correct
            img = dat['CMI'][:]
            img = np.power(img, 1./gamma)

            ogrid, ngrid, ndat = crop_image(dat, img, cLat, cLon)

            # Get the new projection/transformation info for the plot axes
            crs = ngrid.to_cartopy_crs()

            fig = plt.figure(figsize=(8, 10))
            ax = plt.axes(projection=crs)

            # Some custom stuff
            ax = add_map_features(ax)
            ax = add_AZObs(ax)

            plt.imshow(ndat, transform=crs, extent=crs.bounds, origin='upper',
                       vmin=11., vmax=14., interpolation='none')
            # plt.colorbar()

            # Add the informational bar at the top, using info directly
            #   from the original datafiles that we opened at the top
            line1 = "%s  %s" % (plat, dprod)
            line1 = line1.upper()

            # We don't need microseconds shown on this plot
            tendstr = tend.strftime("%Y-%m-%d  %H:%M:%SZ")
            line2 = "Band %02d  %s" % (chan, tendstr)
            line2 = line2.upper()

            # Black background for top label text
            #   NOTE: Z order is important! Text should be higher than trect
            trect = mpatches.Rectangle((0.0, 0.955), width=1.0, height=0.045,
                                       edgecolor=None, facecolor='black',
                                       fill=True, alpha=0.75, zorder=100,
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

            plt.savefig(outpname, pad_inches=0, bbox_inches='tight')
            plt.close()
