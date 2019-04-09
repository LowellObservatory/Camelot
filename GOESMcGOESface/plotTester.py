# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 9 Apr 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import plotGOES as pg


if __name__ == "__main__":
    inloc = "./inputs/"
    outloc = "./outputs/pngs/"

    cmap = pg.getCmap()
    pg.makePlots(inloc, outloc, cmap=cmap, forceRegen=True)
