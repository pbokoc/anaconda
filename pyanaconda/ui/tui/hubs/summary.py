# Summary text hub
#
# Copyright (C) 2012  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): Martin Sivak <msivak@redhat.com>
#                    Jesse Keating <jkeating@redhat.com>
#

from pyanaconda.ui.tui.hubs import TUIHub
from pyanaconda.flags import flags
import sys
import time

import gettext
_ = lambda x: gettext.ldgettext("anaconda", x)

class SummaryHub(TUIHub):
    title = _("Install hub")
    categories = ["source", "localization", "destination", "password"]

    def __init__(self, app, data, storage, payload, instclass):
        TUIHub.__init__(self, app, data, storage, payload, instclass)
        if flags.automatedInstall:
            sys.stdout.write(_("Starting automated install"))
            sys.stdout.flush()
            spokes = self._keys.values()
            while not all(spoke.ready for spoke in spokes):
                sys.stdout.write('.')
                sys.stdout.flush()
                time.sleep(1)

            print('')
            for spoke in spokes:
                spoke.execute()

    # override the prompt so that we can skip user input on kickstarts
    # where all the data is in hand.  If not in hand, do the actual prompt.
    def prompt(self, args=None):
        if flags.automatedInstall and \
        all(spoke.completed for spoke in self._keys.values()):
            self.close()
            return None
        return TUIHub.prompt(self, args)