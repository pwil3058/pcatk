### Copyright (C) 2005-2016 Peter Williams <pwil3058@gmail.com>
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

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GdkPixbuf

from .bab.decorators import singleton

from .gtx import actions
from .gtx import icons
from .gtx import dialogue
from .gtx import recollect

from .epaint import gpaint
from .epaint import pedit
from .epaint import pmix
from .epaint import pseries
from .epaint import vpaint

from . import APP_NAME

from . import apaint
from . import palette

APP_ICON_PIXBUF = GdkPixbuf.Pixbuf.new_from_file(icons.APP_ICON_FILE)

class ArtPaintMixer(pmix.PaintMixer):
    PAINT = apaint.ArtPaint
    MATCHED_PAINT_LIST_VIEW = apaint.MatchedArtPaintListView
    PAINT_SERIES_MANAGER = apaint.ArtPaintSeriesManager
    PAINT_STANDARDS_MANAGER = None
    MIXED_PAINT_INFORMATION_DIALOGUE = apaint.MixedArtPaintInformationDialogue
    MIXTURE = apaint.ArtMixture
    MIXED_PAINT = apaint.MixedArtPaint
    TARGET_COLOUR = None

class ArtPaintListNotebook(gpaint.PaintListNotebook):
    class PAINT_LIST_VIEW(apaint.ArtPaintListView):
        UI_DESCR = '''
            <ui>
                <popup name="paint_list_popup">
                    <menuitem action="edit_clicked_paint"/>
                    <menuitem action="show_paint_details"/>
                    <menuitem action="remove_selected_paints"/>
                </popup>
            </ui>
            '''
        def populate_action_groups(self):
            """
            Populate action groups ready for UI initialization.
            """
            self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
                [
                    ("edit_selected_paint", Gtk.STOCK_EDIT, None, None,
                     _("Load the selected paint into the paint editor."), ),
                ]
            )
            self.action_groups[self.AC_CLICKED_ON_ROW].add_actions(
                [
                    ("edit_clicked_paint", Gtk.STOCK_EDIT, None, None,
                     _("Load the clicked paint into the paint editor."), ),
                ]
            )

class ArtPaintEditor(pedit.PaintEditor):
    PAINT = apaint.ArtPaint
    RESET_CHARACTERISTICS = False

COLLN_EDITOR_UI_DESC = """
    <ui>
    <toolbar name="colln_editor_toolbar">
        <toolitem action="new_paint_collection"/>
        <toolitem action="open_paint_collection_file"/>
        <toolitem action="save_paint_collection_to_file"/>
        <toolitem action="save_paint_collection_as_file"/>
    </toolbar>
    </ui>
"""

class ArtPaintSeriesEditor(Gtk.VBox):
    class Editor(pseries.PaintSeriesEditor):
        PAINT_EDITOR = ArtPaintEditor
        PAINT_LIST_NOTEBOOK = ArtPaintListNotebook
        PAINT_COLLECTION = apaint.ArtPaintSeries
        UI_DESCR = COLLN_EDITOR_UI_DESC
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.pack_start(Gtk.HSeparator(), expand=False, fill=True, padding=0)
        self.editor = self.Editor(pack_current_file_box=False)
        self.editor.action_groups.get_action("close_colour_editor").set_visible(False)
        self.editor.set_file_path(None)
        hbox = Gtk.HBox()
        hbox.pack_start(self.editor.ui_manager.get_widget("/colln_editor_toolbar"), expand=False, fill=True, padding=0)
        hbox.pack_start(Gtk.VSeparator(), expand=False, fill=True, padding=0)
        hbox.pack_start(Gtk.Label("  "), expand=False, fill=True, padding=0)
        hbox.pack_start(self.editor.current_file_box, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        self.pack_start(Gtk.HSeparator(), expand=False, fill=True, padding=0)
        self.pack_start(self.editor, expand=True, fill=True, padding=0)
    def __getattr__(self, attr_name):
        return getattr(self.editor, attr_name)

class ArtPaintPalette(palette.Palette):
    UI_DESCR = """
    <ui>
        <toolbar name="palette_toolbar">
            <toolitem action="print_palette"/>
        </toolbar>
    </ui>
    """

@singleton
class MainWindow(dialogue.MainWindow, actions.CAGandUIManager):
    __g_type_name__ = "MainWindow"
    UI_DESCR = """
    <ui>
        <menubar name="pcatk_left_menubar">
            <menu action="pcatk_main_window_file_menu">
              <menuitem action="pcatk_main_window_quit"/>
            </menu>
            <menu action="pcatk_series_manager_menu">
                <menuitem action="mixer_load_paint_series"/>
            </menu>
            <menu action="pcatk_samples_menu">
              <menuitem action="take_screen_sample"/>
              <menuitem action="open_sample_viewer"/>
            </menu>
            <menu action="pcatk_reference_resource_menu">
              <menuitem action="open_reference_image_viewer"/>
            </menu>
        </menubar>
    </ui>
    """
    MIXER_LABEL = _("Palette")
    recollect.define("pcatk_main_window", "last_geometry", recollect.Defn(str, ""))
    def __init__(self):
        dialogue.MainWindow.__init__(self)
        self.set_title(APP_NAME)
        self.parse_geometry(recollect.get("pcatk_main_window", "last_geometry"))
        actions.CAGandUIManager.__init__(self)
        self.set_default_icon(APP_ICON_PIXBUF)
        self.set_icon(APP_ICON_PIXBUF)
        self.connect("delete_event", lambda _w, _e: self.quit())
        self.paint_series_manager = apaint.ArtPaintSeriesManager()
        vbox = Gtk.VBox()
        msm = self.ui_manager.get_widget("/pcatk_left_menubar/pcatk_series_manager_menu")
        if msm:
            msmm = msm.get_submenu()
            msmm.prepend(self.paint_series_manager.open_menu_item)
            msmm.append(self.paint_series_manager.remove_menu_item)
        lmenu_bar = self.ui_manager.get_widget("/pcatk_left_menubar")
        vbox.pack_start(lmenu_bar, expand=False, fill=True, padding=0)
        self._stack = Gtk.Stack()
        self._stack.add_titled(ArtPaintPalette(paint_series_manager=self.paint_series_manager), "palette", self.MIXER_LABEL)
        self._stack.add_titled(ArtPaintSeriesEditor(), "paint_series_editor", ArtPaintSeriesEditor.Editor.LABEL)
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self._stack)
        vbox.pack_start(stack_switcher, expand=False, fill=True, padding=0)
        vbox.pack_start(self._stack, expand=True, fill=True, padding=0)
        self.add(vbox)
        self.show_all()
        self.connect("configure-event", self._configure_event_cb)
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions(
            [
                ("pcatk_main_window_file_menu", None, _("File"), ),
                ("pcatk_series_manager_menu", None, _("Paint Series"), ),
                ("mixer_load_paint_series", None, _("Load"), None,
                 _("Load a paint series from a file."),
                 lambda _action: self.paint_series_manager.add_paint_series()
                ),
                ("pcatk_main_window_quit", Gtk.STOCK_QUIT, _("Quit"), None,
                 _("Close the application."),
                 lambda _action: self.quit()
                ),
            ])
    def _configure_event_cb(self, widget, event):
        recollect.set("pcatk_main_window", "last_geometry", "{0.width}x{0.height}+{0.x}+{0.y}".format(event))
    def quit(self):
        for name in ["paint_series_editor"]:
            child = self._stack.get_child_by_name(name)
            if child.has_unsaved_changes:
                self._stack.set_visible_child(child)
                if not child.unsaved_changes_ok():
                    return True
        Gtk.main_quit()
