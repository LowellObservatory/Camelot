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
import numpy as np
import pyresample as pr
from netCDF4 import Dataset
import matplotlib.pyplot as plt
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
    # satH = proj_var.perspective_point_height
    # satLon = proj_var.longitude_of_projection_origin
    # semi_major = proj_var.semi_major_axis
    # semi_minor = proj_var.semi_minor_axis

    # As I fiddled with this more, I noticed that I get a better result
    #   for registration of coastlines/boundaries if I use these specific ones
    # nom. sat height is in km
    satH = nc.variables['nominal_satellite_height'][0]*1000
    satLon = nc.variables['nominal_satellite_subpoint_lon'][0]
    satLat = nc.variables['nominal_satellite_subpoint_lat'][0]
    semi_major = proj_var.semi_major_axis
    semi_minor = proj_var.semi_minor_axis

    print("xoff: ", nc.variables['x'].add_offset/satH)
    print("yoff:", nc.variables['y'].add_offset/satH)

    x = (nc.variables['x'][:] + 0.00007)*satH
    y = (nc.variables['y'][:] - 0.0003)*satH

    nx = len(x)
    ny = len(y)

    min_x = x.min()
    max_x = x.max()
    min_y = y.min()
    max_y = y.max()

    # NOTE:
    #   Currently don't know why they're offsetting by half_x/y...
    half_x = (max_x - min_x) / nx / 2.
    half_y = (max_y - min_y) / ny / 2.
    extents = (min_x - half_x, min_y - half_y, max_x + half_x, max_y + half_y)

    old_grid = pr.geometry.AreaDefinition('geos', 'goes_conus', 'geos',
                                          {'proj': 'geos',
                                           'h': str(satH),
                                           'lon_0': str(satLon),
                                           'lat_0': str(satLat),
                                           'a': str(semi_major),
                                           'b': str(semi_minor),
                                           'units': 'm'},
                                          nx, ny, extents)

    return old_grid


def crop_image(nc, data, clat, clon, latWid=3.5, lonWid=3.5):
    # Parse/grab the existing projection information
    old_grid = G16_ABI_L2_ProjDef(nc)

    pr.plot.show_quicklook(old_grid, data, coast_res='10m')

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


if __name__ == "__main__":
    cLat = 34.7443
    cLon = -111.4223
    dctAlt = 2361
    gamma = 2.2
    forceRegen = True
    inloc = './GOESMcGOESface/data/'

    flist = sorted(glob.glob(inloc + "*.nc"))

    for each in flist:
        outpname = "./GOESMcGOESface/pngs/%s.png" % (os.path.basename(each))

        # Logic to skip stuff already completed, or just redo everything
        if forceRegen is True:
            save = True
        else:
            # Check to see if we're already done with this image
            #   (actual check is pending, this'll do for now)
            found = False

            if found is True:
                save = False
            else:
                save = True

        if save is True:
            dat = readNC(each)
            # Grab just the image data & quickly gamma correct
            img = dat['CMI'][:]
            img = np.power(img, 1./gamma)

            ogrid, ngrid, ndat = crop_image(dat, img, cLat, cLon)

            # Get the new projection/transformation info for the plot axes
            crs = ngrid.to_cartopy_crs()

            fig = plt.figure(figsize=(8, 10))
            ax = plt.axes(projection=crs)
            ax.add_feature(cfeat.COASTLINE.with_scale('10m'))
            ax.add_feature(cfeat.BORDERS.with_scale('10m'))
            ax.add_feature(cfeat.RIVERS.with_scale('10m'))
            ax.add_feature(cfeat.STATES.with_scale('10m'),
                           linestyle=":", edgecolor='r')

            ax.set_global()
            plt.imshow(ndat, transform=crs, extent=crs.bounds, origin='upper')
            plt.colorbar()
            plt.savefig(outpname)
            plt.close()

        break
