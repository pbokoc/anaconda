# Custom partitioning classes.
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
# Red Hat Author(s): Chris Lumens <clumens@redhat.com>
#

import gettext
_ = lambda x: gettext.ldgettext("anaconda", x)
N_ = lambda x: x
P_ = lambda x, y, z: gettext.ldngettext("anaconda", x, y, z)

from pyanaconda.product import productName, productVersion
from pyanaconda.storage.formats import device_formats
from pyanaconda.storage.size import Size

from pyanaconda.ui.gui.spokes import NormalSpoke
from pyanaconda.ui.gui.utils import setViewportBackground
from pyanaconda.ui.gui.categories.storage import StorageCategory

from gi.repository.AnacondaWidgets import MountpointSelector
from gi.repository import Gtk

__all__ = ["CustomPartitioningSpoke"]

DATA_DEVICE = 0
SYSTEM_DEVICE = 1

# An Accordion is a box that goes on the left side of the custom partitioning spoke.  It
# stores multiple expanders which are here called Pages.  These Pages correspond to
# individual installed OSes on the system plus some special ones.  When one Page is
# expanded, all others are collapsed.
class Accordion(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._expanders = []

    def addPage(self, pageTitle, contents):
        label = Gtk.Label()
        label.set_markup("""<span size='large' weight='bold' fgcolor='black'>%s</span>""" % pageTitle)
        label.set_alignment(0, 0.5)
        label.set_line_wrap(True)

        expander = Gtk.Expander()
        expander.set_label_widget(label)
        expander.add(contents)
        expander.set_expanded(isinstance(contents, CreateNewPage))

        self.add(expander)
        self._expanders.append(expander)
        expander.connect("activate", self._onExpanded)
        expander.show_all()

    def currentPage(self):
        for e in self._expanders:
            if e.get_expanded():
                return e.get_child()

        return None

    def removePage(self, pageTitle):
        # First, remove the expander from the list of expanders we maintain.
        target = None
        for e in self._expanders:
            if e.get_label_widget().get_text() == pageTitle:
                target = e
                break

        if not target:
            return

        self._expanders.remove(target)

        # Then, remove it from the box.
        self.remove(target)

    def removeAllPages(self):
        for e in self._expanders:
            self.remove(e)

        self._expanders = []

    def _onExpanded(self, obj):
        # Currently is expanded, but clicking it this time means it will be
        # un-expanded.  So we want to return.
        if obj.get_expanded():
            return

        for expander in self._expanders:
            if expander is not obj:
                expander.set_expanded(False)

# A Page is a box that is stored in an Accordion.  It breaks down all the filesystems that
# comprise a single installed OS into two categories - Data filesystems and System filesystems.
# Each filesystem is described by a single MountpointSelector.
class Page(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Create the Data label and a box to store all its members in.
        self._dataBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._dataBox.add(self._make_category_label(_("DATA")))
        self.add(self._dataBox)

        # Create the System label and a box to store all its members in.
        self._systemBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._systemBox.add(self._make_category_label(_("SYSTEM")))
        self.add(self._systemBox)

        self._members = []
        self._currentSelector = None

    def _make_category_label(self, name):
        label = Gtk.Label()
        label.set_markup("""<span fgcolor='dark grey' size='large' weight='bold'>%s</span>""" % name)
        label.set_halign(Gtk.Align.START)
        label.set_margin_left(24)
        return label

    def addDevice(self, name, size, mountpoint, cb):
        selector = MountpointSelector()
        selector = MountpointSelector(name, str(Size(spec="%s MB" % size)), mountpoint or "")
        selector.connect("button-press-event", self._onClicked, cb)
        selector.connect("key-release-event", self._onClicked, cb)
        self._members.append(selector)

        if self._mountpointType(mountpoint) == DATA_DEVICE:
            self._dataBox.add(selector)
        else:
            self._systemBox.add(selector)

        return selector

    def currentSelector(self):
        return self._currentSelector

    def _mountpointType(self, mountpoint):
        if not mountpoint:
            # This catches things like swap.
            return SYSTEM_DEVICE
        elif mountpoint in ["/", "/boot", "/boot/efi", "/tmp", "/usr", "/var"]:
            return SYSTEM_DEVICE
        else:
            return DATA_DEVICE

    def _onClicked(self, selector, event, cb):
        from gi.repository import Gdk

        # This handler only runs for these two kinds of events, and only for
        # activate-type keys (space, enter) in the latter event's case.
        if event and not event.type in [Gdk.EventType.BUTTON_PRESS, Gdk.EventType.KEY_RELEASE]:
            return

        if event and event.type == Gdk.EventType.KEY_RELEASE and \
           event.keyval not in [Gdk.KEY_space, Gdk.KEY_Return, Gdk.KEY_ISO_Enter, Gdk.KEY_KP_Enter, Gdk.KEY_KP_Space]:
              return

        # Then, this callback will set up the right hand side of the screen to
        # show the details for the newly selected object.
        self._currentSelector = selector
        cb(selector)

class UnknownPage(Page):
    def __init__(self):
        # For this type of page, there's only one place to store members.
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._members = []
        self._currentSelector = None

    def addDevice(self, name, size, mountpoint, cb):
        selector = MountpointSelector()
        selector = MountpointSelector(name, str(Size(spec="%s MB" % size)), mountpoint or "")
        selector.connect("button-press-event", self._onClicked, cb)
        selector.connect("key-release-event", self._onClicked, cb)

        self._members.append(selector)
        self.add(selector)

        return selector

# This is a special Page that is displayed when no new installation has been automatically
# created, and shows the user how to go about doing that.  The intention is that an instance
# of this class will be packed into the Accordion first and then when the new installation
# is created, it will be removed and replaced with a Page for it.
class CreateNewPage(Page):
    def __init__(self, cb):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Create a box where we store the "Here's how you create a new blah" info.
        self._createBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._createBox.set_margin_left(16)

        label = Gtk.Label(_("You haven't created any mount points for your %s %s installation yet:") % (productName, productVersion))
        label.set_alignment(0, 0.5)
        label.set_line_wrap(True)
        self._createBox.add(label)

        self._createNewButton = Gtk.Button("")
        label = self._createNewButton.get_children()[0]
        label.set_line_wrap(True)
        label.set_use_markup(True)
        label.set_markup("""<span foreground='blue'><u>Click here to create them automatically.</u></span>""")

        self._createNewButton.set_halign(Gtk.Align.START)
        self._createNewButton.connect("clicked", cb)
        self._createBox.add(self._createNewButton)

        label = Gtk.Label(_("Or, create new mount points below with the '+' icon."))
        label.set_alignment(0, 0.5)
        label.set_line_wrap(True)
        self._createBox.add(label)

        self.add(self._createBox)

class CustomPartitioningSpoke(NormalSpoke):
    builderObjects = ["customStorageWindow", "sizeAdjustment",
                      "partitionStore",
                      "addImage", "removeImage", "settingsImage"]
    mainWidgetName = "customStorageWindow"
    uiFile = "spokes/custom.ui"

    category = StorageCategory
    title = N_("MANUAL PARTITIONING")

    def __init__(self, data, storage, payload, instclass):
        NormalSpoke.__init__(self, data, storage, payload, instclass)

        self._current_selector = None
        self._ran_autopart = False

    def apply(self):
        pass

    @property
    def indirect(self):
        return True

    def _grabObjects(self):
        self._configureBox = self.builder.get_object("configureBox")
        self._availableSpaceLabel = self.builder.get_object("availableSpaceLabel")
        self._totalSpaceLabel = self.builder.get_object("totalSpaceLabel")

        self._summaryButton = self.builder.get_object("summary_button")

        self._viewport = self.builder.get_object("partitionsViewport")
        self._partitionsNotebook = self.builder.get_object("partitionsNotebook")

    def initialize(self):
        from pyanaconda.storage.devices import DiskDevice
        from pyanaconda.storage.formats.fs import FS

        NormalSpoke.initialize(self)

        self._grabObjects()
        setViewportBackground(self.builder.get_object("availableSpaceViewport"), "#db3279")
        setViewportBackground(self.builder.get_object("totalSpaceViewport"), "#60605b")
        setViewportBackground(self._viewport)

        self._accordion = Accordion()
        self._viewport.add(self._accordion)

        # Populate the list of valid filesystem types from the format classes.
        # Unfortunately, we have to narrow them down a little bit more because
        # this list will include things like PVs and RAID members.
        combo = self.builder.get_object("fileSystemTypeCombo")
        for cls in device_formats.itervalues():
            obj = cls()
            if obj.supported and obj.formattable and \
               (isinstance(obj, FS) or obj.type in ["biosboot", "prepboot", "swap"]):
                combo.append_text(obj.name)

    def _mountpointName(self, mountpoint):
        # If there's a mount point, apply a kind of lame scheme to it to figure
        # out what the name should be.  Basically, just look for the last directory
        # in the mount point's path and capitalize the first letter.  So "/boot"
        # becomes "Boot", and "/usr/local" becomes "Local".
        if mountpoint == "/":
            return "Root"
        elif mountpoint != None:
            try:
                lastSlash = mountpoint.rindex("/")
            except ValueError:
                # No slash in the mount point?  I suppose that's possible.
                return None

            return mountpoint[lastSlash+1:].capitalize()
        else:
            return None

    def _clearpartDevices(self):
        return [d for d in self.storage.devicetree.devices if d.name in self.data.clearpart.drives]

    def _unusedDevices(self):
        from pyanaconda.storage.devices import DiskDevice
        return [d for d in self.storage.unusedDevices if d.disks and not isinstance(d, DiskDevice)]

    def _currentFreeSpace(self):
        """Add up all the free space on selected disks and return it as a Size."""
        totalFree = 0

        freeDisks = self.storage.getFreeSpace(disks=self._clearpartDevices())
        for tup in freeDisks.values():
            for chunk in tup:
                totalFree += chunk

        return Size(totalFree)

    def _currentTotalSpace(self):
        """Add up the sizes of all selected disks and return it as a Size."""
        totalSpace = 0

        for disk in self._clearpartDevices():
            totalSpace += disk.size

        return Size(spec="%s MB" % totalSpace)

    def refresh(self):
        NormalSpoke.refresh(self)

        # Make sure we start with a clean slate.
        self._accordion.removeAllPages()

        # Set up the free space/available space displays in the bottom left.
        self._availableSpaceLabel.set_text(str(self._currentFreeSpace()))
        self._totalSpaceLabel.set_text(str(self._currentTotalSpace()))

        summaryLabel = self._summaryButton.get_children()[0]
        count = len(self.data.clearpart.drives)
        summary = P_("%d storage device selected",
                     "%d storage devices selected",
                     count) % count

        summaryLabel.set_use_markup(True)
        summaryLabel.set_markup("<span foreground='blue'><u>%s</u></span>" % summary)

        # Now it's time to populate the accordion.

        # If we've not yet run autopart, add an instance of CreateNewPage.  This
        # ensures it's only added once.
        if not self._ran_autopart:
            page = CreateNewPage(self.on_create_clicked)
            self._accordion.addPage(_("New %s %s Installation") % (productName, productVersion), page)

            self._partitionsNotebook.set_current_page(0)
            label = self.builder.get_object("whenCreateLabel")
            label.set_text(label.get_text() % (productName, productVersion))

        # Add in all the existing (or autopart-created) operating systems.
        for i in self.storage.roots:
            page = Page()

            for swap in i.swaps:
                selector = page.addDevice("Swap", swap.size, None, self.on_selector_clicked)
                selector._device = swap

            for (mountpoint, device) in i.mounts.iteritems():
                selector = page.addDevice(self._mountpointName(mountpoint) or device.format.name, device.size, mountpoint, self.on_selector_clicked)
                selector._device = device

            page.show_all()
            self._accordion.addPage(i.name, page)

        # Anything that doesn't go with an OS we understand?  Put it in the Other box.
        unused = self._unusedDevices()
        if unused:
            page = UnknownPage()

            for u in unused:
                selector = page.addDevice(u.format.name, u.size, None, self.on_selector_clicked)
                selector._device = u

            page.show_all()
            self._accordion.addPage(_("Unknown"), page)

    ###
    ### RIGHT HAND SIDE METHODS
    ###

    def _description(self, name):
        if name == "Swap":
            return _("The 'swap' area on your computer is used by the operating\n" \
                     "system when running low on memory.")
        elif name == "Boot":
            return _("The 'boot' area on your computer is where files needed\n" \
                     "to start the operating system are stored.")
        elif name == "Root":
            return _("The 'root' area on your computer is where core system\n" \
                     "files and applications are stored.")
        elif name == "Home":
            return _("The 'home' area on your computer is where all your personal\n" \
                     "data is stored.")
        elif name == "BIOS Boot":
            return _("No one knows what this could possibly be for.")
        else:
            return ""

    def _save_right_side(self, selector):
        if not selector:
            return

        labelEntry = self.builder.get_object("labelEntry")

        device = selector._device

        if hasattr(device.format, "label") and labelEntry.get_text():
            device.format.label = labelEntry.get_text()

    def _populate_right_side(self, selector):
        encryptCheckbox = self.builder.get_object("encryptCheckbox")
        labelEntry = self.builder.get_object("labelEntry")
        selectedDeviceLabel = self.builder.get_object("selectedDeviceLabel")
        selectedDeviceDescLabel = self.builder.get_object("selectedDeviceDescLabel")
        sizeSpinner = self.builder.get_object("sizeSpinner")
        typeCombo = self.builder.get_object("deviceTypeCombo")
        fsCombo = self.builder.get_object("fileSystemTypeCombo")

        device = selector._device

        selectedDeviceLabel.set_text(selector.props.name)
        selectedDeviceDescLabel.set_text(self._description(selector.props.name))

        labelEntry.set_text(getattr(device.format, "label", "") or "")
        labelEntry.set_sensitive(getattr(device.format, "labelfsProg", "") != "")

        if labelEntry.get_sensitive():
            labelEntry.props.has_tooltip = False
        else:
            labelEntry.set_tooltip_text(_("This file system does not support labels."))

        sizeSpinner.set_range(device.minSize, device.maxSize)
        sizeSpinner.set_value(device.size)
        sizeSpinner.set_sensitive(device.resizable)

        if sizeSpinner.get_sensitive():
            sizeSpinner.props.has_tooltip = False
        else:
            sizeSpinner.set_tooltip_text(_("This file system may not be resized."))

        encryptCheckbox.set_active(device.encrypted)

        # FIXME:  What do we do if we can't figure it out?
        if device.type == "lvmlv":
            typeCombo.set_active(1)
        elif device.type in ["dm-raid array", "mdarray"]:
            typeCombo.set_active(2)
        elif device.type == "partition":
            typeCombo.set_active(3)

        # FIXME:  What do we do if we can't figure it out?
        model = fsCombo.get_model()
        for i in range(0, len(model)):
            if model[i][0] == device.format.name:
                fsCombo.set_active(i)
                break

        self._current_selector = selector

    ###
    ### SIGNAL HANDLERS
    ###

    def on_back_clicked(self, button):
        self.skipTo = "StorageSpoke"
        NormalSpoke.on_back_clicked(self, button)

    # Use the default back action here, since the finish button takes the user
    # to the install summary screen.
    def on_finish_clicked(self, button):
        self._save_right_side(self._current_selector)
        NormalSpoke.on_back_clicked(self, button)

    def on_add_clicked(self, button):
        pass

    def on_remove_clicked(self, button):
        pass

    def on_summary_clicked(self, button):
        pass

    def on_configure_clicked(self, button):
        pass

    def on_selector_clicked(self, selector):
        # Make sure we're showing details instead of the "here's how you create
        # a new OS" label.
        self._partitionsNotebook.set_current_page(1)

        self._save_right_side(self._current_selector)
        self._populate_right_side(selector)

    def on_create_clicked(self, button):
        from pyanaconda.storage import Root
        from pyanaconda.storage.devices import DiskDevice
        from pyanaconda.storage.partitioning import doAutoPartition

        # Pick the first disk to be the destination device for the bootloader.
        # This appears to be the minimum amount of configuration required to
        # make autopart happy with the bootloader settings.
        if not self.data.bootloader.bootDrive:
            self.data.bootloader.bootDrive = self.storage.bootloader.disks[0].name

        # Then do autopartitioning.  We do not do any clearpart first.  This is
        # custom partitioning, so you have to make your own room.
        # FIXME:  Handle all the autopart exns here.
        self.data.autopart.autopart = True
        self.data.autopart.execute(self.storage, self.data, self.instclass)

        # Create a new Root object for the new installation and put it into
        # the storage object.  This means any boot-related devices we make for
        # this new install (biosboot, etc.) will show up as unused and therefore
        # be put into the Unknown page.
        mounts = {}
        swaps = []

        # Devices just created by autopartitioning will be listed as unused
        # since they are not yet a part of any known Root.
        for device in self._unusedDevices():
            if device.format.type == "swap":
                swaps.append(device)

            if hasattr(device.format, "mountpoint"):
                mounts[device.format.mountpoint] = device

        newName = _("New %s %s Installation") % (productName, productVersion)
        root = Root(mounts=mounts, swaps=swaps, name=newName)
        self.storage.roots.append(root)

        # Setting this ensures the CreateNewPage instance does not reappear when
        # refresh is called.
        self._ran_autopart = True

        # And refresh the spoke to make the new partitions appear.
        self.refresh()