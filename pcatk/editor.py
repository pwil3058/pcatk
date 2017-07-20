### Copyright: Peter Williams (2014) - All rights reserved
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 of the License only.
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

'''
Edit/create paint colours
'''

import math
import os
import hashlib
import fractions

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import GLib

from .bab import mathx
from .bab import options

from .epaint import gpaint
from .epaint import vpaint
from .epaint import pchar
from .epaint import pedit
from .epaint import pseries
from .epaint import rgbh

from .gtx import actions
from .gtx import coloured
from .gtx import dialogue
from .gtx import entries
from .gtx import gutils
from .gtx import icons
from .gtx import recollect
from .gtx import screen

from .pixbufx import iview

class UnsavedChangesDialogue(dialogue.Dialog):
    # TODO: make a better UnsavedChangesDialogue()
    SAVE_AND_CONTINUE, CONTINUE_UNSAVED = range(1, 3)
    def __init__(self, parent, message):
        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        buttons += (_("Save and Continue"), UnsavedChangesDialogue.SAVE_AND_CONTINUE)
        buttons += (_("Continue Without Saving"), UnsavedChangesDialogue.CONTINUE_UNSAVED)
        dialogue.Dialog.__init__(self,
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=buttons,
        )
        self.vbox.pack_start(Gtk.Label(message), expand=True, fill=True, padding=0)
        self.show_all()

class UnacceptedChangesDialogue(dialogue.Dialog):
    # TODO: make a better UnacceptedChangesDialogue()
    ACCEPT_CHANGES_AND_CONTINUE, CONTINUE_DISCARDING_CHANGES = range(1, 3)
    def __init__(self, parent, message):
        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        buttons += (_('Accept and Continue'), UnacceptedChangesDialogue.ACCEPT_CHANGES_AND_CONTINUE)
        buttons += (_('Continue (Discarding Changes)'), UnacceptedChangesDialogue.CONTINUE_DISCARDING_CHANGES)
        dialogue.Dialog.__init__(self,
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=buttons,
        )
        self.vbox.pack_start(Gtk.Label(message), expand=True, fill=True, padding=0)
        self.show_all()

class UnaddedNewColourDialogue(dialogue.Dialog):
    # TODO: make a better UnaddedNewColourDialogue()
    DISCARD_AND_CONTINUE = 1
    def __init__(self, parent, message):
        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        buttons += (_('Discard and Continue'), UnaddedNewColourDialogue.DISCARD_AND_CONTINUE)
        dialogue.Dialog.__init__(self,
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=buttons,
        )
        self.vbox.pack_start(Gtk.Label(message), expand=True, fill=True, padding=0)
        self.show_all()

recollect.define("editor", "last_geometry", recollect.Defn(str, ""))

class ArtPaintEditor(pedit.PaintEditor):
    PAINT = vpaint.ArtPaint
    PROVIDE_RGB_ENTRY = False

class ArtPaintListNotebook(gpaint.PaintListNotebook):
    class PAINT_LIST_VIEW(gpaint.ArtPaintListView):
        UI_DESCR = '''
            <ui>
                <popup name='paint_list_popup'>
                    <menuitem action='edit_clicked_paint'/>
                    <menuitem action='remove_selected_paints'/>
                </popup>
            </ui>
            '''
        def populate_action_groups(self):
            """
            Populate action groups ready for UI initialization.
            """
            self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
                [
                    ('edit_selected_paint', Gtk.STOCK_EDIT, None, None,
                     _('Load the selected paint into the paint editor.'), ),
                ]
            )
            self.action_groups[self.AC_CLICKED_ON_ROW].add_actions(
                [
                    ("edit_clicked_paint", Gtk.STOCK_EDIT, None, None,
                     _("Load the clicked paint into the paint editor."), ),
                ]
            )

class ArtPaintSeriesEditor(pseries.PaintSeriesEditor):
    PAINT_EDITOR = ArtPaintEditor
    PAINT_LIST_NOTEBOOK = ArtPaintListNotebook
    BUTTONS = [
            "add_colour_into_collection",
            "accept_colour_changes",
            "reset_colour_editor",
            "take_screen_sample",
            "automatch_sample_images_max_chroma",
            "automatch_sample_images_raw",
        ]

class TopLevelWindow(dialogue.MainWindow):
    """
    A top level window wrapper around a palette
    """
    def __init__(self):
        dialogue.MainWindow.__init__(self)
        self.parse_geometry(recollect.get("editor", "last_geometry"))
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_title('pcatk: Paint Series Editor')
        self.editor = ArtPaintSeriesEditor()
        self.editor.action_groups.get_action('close_colour_editor').set_visible(False)
        self.editor.connect("file_changed", self._file_changed_cb)
        self.editor.set_file_path(None)
        self._menubar = self.editor.ui_manager.get_widget('/paint_collection_editor_menubar')
        self.connect("destroy", self.editor._exit_colour_editor_cb)
        self.connect("configure-event", self._configure_event_cb)
        vbox = Gtk.VBox()
        vbox.pack_start(self._menubar, expand=False, fill=True, padding=0)
        vbox.pack_start(self.editor, expand=True, fill=True, padding=0)
        self.add(vbox)
        self.show_all()
    def _file_changed_cb(self, widget, file_path):
        self.set_title(_('pcatk: Paint Series Editor: {0}').format(file_path))
    def _configure_event_cb(self, widget, event):
        recollect.set("editor", "last_geometry", "{0.width}x{0.height}+{0.x}+{0.y}".format(event))
