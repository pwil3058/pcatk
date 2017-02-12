# Copyright: Peter Williams (2012) - All rights reserved
#
# This software is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License only.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; if not, write to:
#  The Free Software Foundation, Inc., 51 Franklin Street,
#  Fifth Floor, Boston, MA 02110-1301 USA

"""Mix paint colours
"""

import os
import cgi
import time
import collections

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

from .bab import mathx

from .epaint import gpaint
from .epaint import lexicon
from .epaint import pmix
from .epaint import vpaint

from .gtx import actions
from .gtx import coloured
from .gtx import dialogue
from .gtx import entries
from .gtx import gutils
from .gtx import printer
from .gtx import recollect
from .gtx import screen
from .gtx import tlview

from .pixbufx import iview

from . import icons
from . import analyser
from . import utils

def pango_rgb_str(rgb, bits_per_channel=16):
    """
    Convert an rgb to a Pango colour description string
    """
    string = "#"
    for i in range(3):
        string += "{0:02X}".format(rgb[i] >> (bits_per_channel - 8))
    return string

class ArtMixture(pmix.Mixture):
    PAINT = vpaint.ArtPaint

class MixedArtPaint(pmix.MixedPaint):
    MIXTURE = ArtMixture

class MixedArtPaintInformationDialogue(pmix.MixedPaintInformationDialogue):
    class COMPONENT_LIST_VIEW(pmix.MixedPaintComponentsListView):
        class MODEL(pmix.MixedPaintComponentsListStore):
            COLUMN_DEFS = gpaint.ArtPaintListStore.COLUMN_DEFS[1:]
        def _show_paint_details_cb(self, _action):
            paint = self.get_selected_paints()[0]
            if hasattr(paint, "blobs"):
                MixedArtPaintInformationDialogue(paint).show()
            else:
                gpaint.PaintColourInformationDialogue(paint).show()

class MatchedArtPaintListStore(gpaint.PaintListStore):
    COLUMN_DEFS = gpaint.ArtPaintListStore.COLUMN_DEFS[1:]
    TYPES = [object, int]
    def __init__(self):
        gpaint.PaintListStore.__init__(self, int)
    def append_paint(self, paint, parts=0):
        self.append([paint, parts])
    def get_parts(self, paint):
        """
        Return the number of parts selected for the given paint
        """
        model_iter = self.get_paint_iter(paint)
        if model_iter is None:
            raise LookupError()
        return self[model_iter][1]
    def reset_parts(self):
        """
        Reset the number of parts for all colours to zero
        """
        model_iter = self.get_iter_first()
        while model_iter is not None:
            self[model_iter][1] = 0
            model_iter = self.iter_next(model_iter)
        self.emit("contributions-changed", [])
    def divide_parts(self, divisor):
        """
        Reset the number of parts for all colours to zero
        """
        if divisor is not None and divisor > 1:
            model_iter = self.get_iter_first()
            while model_iter is not None:
                parts = self.get_value_named(model_iter, "parts")
                self.set_value_named(model_iter, "parts", parts / divisor)
                model_iter = self.iter_next(model_iter)
            self.emit("contributions-changed", self.get_contributions())
    def get_contributions(self):
        """
        Return a list of MODEL.ROW() tuples where parts is greater than zero
        """
        return [pmix.BLOB(row[0], row[1]) for row in self if row[1] > 0]
    def get_paint_users(self, paint):
        return [row[0] for row in self if row[0].contains_paint(paint)]
    def process_parts_change(self, contribution):
        """
        Work out contributions with modifications in contribution.
        This is necessary because the parts field in the model hasn't
        been updated yet as it causes a "jerky" appearance in the
        CellRendererSpin due to SpinButton being revreated every time
        an edit starts and updating the model causes restart of edit.
        """
        contributions = []
        for row in self:
            if row[0] == contribution.paint:
                if contribution.parts > 0:
                    contributions.append(contribution)
            elif row[1] > 0:
                contributions.append(pmix.BLOB(row[0], row[1]))
        self.emit("contributions-changed", contributions)
    def _parts_value_changed_cb(self, cell, path, spinbutton):
        """Change the model for a change to a spinbutton value
        """
        new_parts = spinbutton.get_value_as_int()
        paint = self[self.get_iter(path)][0]
        self.process_parts_change(pmix.BLOB(paint=paint, parts=new_parts))
    def _notes_edited_cb(self, cell, path, new_text):
        self[path][0].notes = new_text
GObject.signal_new("contributions-changed", MatchedArtPaintListStore, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT, ))

def notes_cell_data_func(column, cell, model, model_iter, *args):
    colour = model[model_iter][0]
    cell.set_property("text", colour.notes)
    cell.set_property("background-gdk", colour.gdk_color)
    cell.set_property("foreground-gdk", colour.best_foreground().gdk_color)

def generate_matched_art_paint_list_spec(view, model):
    """Generate the SPECIFICATION for a paint colour parts list
    """
    parts_col_spec = tlview.ColumnSpec(
        title =_("Parts"),
        properties={},
        sort_key_function=lambda row: row[1],
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=tlview.CellRendererSpin,
                    expand=None,
                    properties={"editable" : True, "adjustment" : pmix.paint_parts_adjustment(), "width-chars" : 8},
                    signal_handlers = {"value-changed" : model._parts_value_changed_cb},
                    start=False
                ),
                cell_data_function_spec=None,
                attributes={"text" : 1}
            ),
        ]
    )
    notes_col_spec = tlview.ColumnSpec(
        title =_("Notes"),
        properties={"resizable" : True, "expand" : True},
        sort_key_function=lambda row: row[0].notes,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties={"editable" : True, },
                    signal_handlers = {"edited" : model._notes_edited_cb},
                    start=False
                ),
                cell_data_function_spec=tlview.CellDataFunctionSpec(
                    function=notes_cell_data_func,
                ),
                attributes={}
            ),
        ]
    )
    name_col_spec = gpaint.tns_paint_list_column_spec(gpaint.TNS(_("Name"), "name", {}, lambda row: row[0].name))
    attr_cols_specs = gpaint.paint_list_column_specs(model)
    return tlview.ViewSpec(
        properties={},
        selection_mode=Gtk.SelectionMode.MULTIPLE,
        columns=[parts_col_spec, name_col_spec, notes_col_spec] + attr_cols_specs
    )

class MatchedArtPaintListView(pmix.MatchedPaintListView):
    UI_DESCR = """
    <ui>
        <popup name="paint_list_popup">
            <menuitem action="show_paint_details"/>
            <menuitem action="remove_selected_paints"/>
        </popup>
    </ui>
    """
    MODEL = MatchedArtPaintListStore
    MIXED_PAINT_INFORMATION_DIALOGUE = MixedArtPaintInformationDialogue
    SPECIFICATION = generate_matched_art_paint_list_spec
    def _show_paint_details_cb(self, _action):
        paint = self.get_selected_paints()[0]
        if hasattr(paint, "blobs"):
            MixedArtPaintInformationDialogue(paint).show()
        else:
            gpaint.PaintColourInformationDialogue(paint).show()

class ArtPaintSelector(pmix.PaintSelector):
    class SELECT_PAINT_LIST_VIEW (gpaint.ArtPaintListView):
        UI_DESCR = """
        <ui>
            <popup name="paint_list_popup">
                <menuitem action="show_paint_details"/>
                <menuitem action="add_paints_to_mixer"/>
            </popup>
        </ui>
        """
        def populate_action_groups(self):
            """
            Populate action groups ready for UI initialization.
            """
            self.action_groups[actions.AC_SELN_MADE].add_actions(
                [
                    ("add_paints_to_mixer", Gtk.STOCK_ADD, None, None,
                     _("Add the selected paints to the pallete."),),
                ]
            )

class ArtPaintSeriesManager(pmix.PaintSeriesManager):
    PAINT_SELECTOR = ArtPaintSelector

recollect.define("palette", "hpaned_position", recollect.Defn(int, -1))
recollect.define("palette", "vpaned_position", recollect.Defn(int, -1))

class Palette(Gtk.VBox, actions.CAGandUIManager, dialogue.AskerMixin):
    UI_DESCR = """
    <ui>
        <menubar name="palette_menubar">
            <menu action="palette_file_menu">
                <menuitem action="print_palette"/>
                <menuitem action="quit_palette"/>
            </menu>
            <menu action="reference_resource_menu">
                <menuitem action="open_analysed_image_viewer"/>
            </menu>
        </menubar>
    </ui>
    """
    AC_HAVE_MIXTURE, AC_MASK = actions.ActionCondns.new_flags_and_mask(1)
    def __init__(self):
        Gtk.VBox.__init__(self)
        actions.CAGandUIManager.__init__(self)
        # Components
        self.notes = entries.TextEntryAutoComplete(lexicon.GENERAL_WORDS_LEXICON)
        self.notes.connect("new-words", lexicon.new_general_words_cb)
        self.mixpanel = gpaint.ColourSampleArea()
        self.mixpanel.set_size_request(360, 240)
        self.hcvw_display = gpaint.HCVWDisplay()
        self.paint_colours = pmix.PaintPartsSpinButtonBox()
        self.paint_colours.connect("remove-paint", self._remove_paint_colour_cb)
        self.paint_colours.connect("contributions-changed", self._contributions_changed_cb)
        self.paint_colours.set_sensitive(True)
        self.mixed_colours = MatchedArtPaintListStore()
        self.mixed_colours.connect("contributions-changed", self._mixed_contributions_changed_cb)
        self.mixed_colours_view = MatchedArtPaintListView(self.mixed_colours)
        self.mixed_colours_view.action_groups.connect_activate("remove_selected_paints", self._remove_mixed_colours_cb)
        self.mixed_count = 0
        self.wheels = gpaint.HueWheelNotebook()
        self.wheels.set_size_request(360, 360)
        self.wheels.set_wheels_colour_info_acb(self._show_wheel_colour_details_cb)
        self.buttons = self.action_groups.create_action_button_box([
            "add_mixed_colour",
            "simplify_contributions",
            "reset_contributions",
            "remove_unused_paints",
            "take_screen_sample"
        ])
        menubar = self.ui_manager.get_widget("/palette_menubar")
        # Lay out components
        self.pack_start(menubar, expand=False, fill=True, padding=0)
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_("Notes:")), expand=False, fill=True, padding=0)
        hbox.pack_start(self.notes, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        hpaned = Gtk.HPaned()
        hpaned.pack1(self.wheels, resize=True, shrink=False)
        vbox = Gtk.VBox()
        vbox.pack_start(self.hcvw_display, expand=False, fill=True, padding=0)
        vbox.pack_start(gutils.wrap_in_frame(self.mixpanel, Gtk.ShadowType.ETCHED_IN), expand=True, fill=True, padding=0)
        hpaned.pack2(vbox, resize=True, shrink=False)
        vpaned = Gtk.VPaned()
        vpaned.pack1(hpaned, resize=True, shrink=False)
        vbox = Gtk.VBox()
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_("Paints:")), expand=False, fill=True, padding=0)
        hbox.pack_start(self.paint_colours, expand=True, fill=True, padding=0)
        vbox.pack_start(hbox, expand=False, fill=True, padding=0)
        vbox.pack_start(self.buttons, expand=False, fill=True, padding=0)
        vbox.pack_start(gutils.wrap_in_scrolled_window(self.mixed_colours_view), expand=True, fill=True, padding=0)
        vpaned.pack2(vbox, resize=True, shrink=False)
        self.pack_start(vpaned, expand=True, fill=True, padding=0)
        vpaned.set_position(recollect.get("palette", "vpaned_position"))
        hpaned.set_position(recollect.get("palette", "hpaned_position"))
        vpaned.connect("notify", self._paned_notify_cb)
        hpaned.connect("notify", self._paned_notify_cb)
        self.paint_series_manager = ArtPaintSeriesManager()
        self.paint_series_manager.connect("add-paint-colours", self._add_colours_to_palette_cb)
        menubar.insert(self.paint_series_manager.menu, 1)
        self.show_all()
        self.recalculate_colour([])
    def _paned_notify_cb(self, widget, parameter):
        if parameter.name == "position":
            if isinstance(widget, Gtk.HPaned):
                recollect.set("palette", "hpaned_position", str(widget.get_position()))
            else:
                recollect.set("palette", "vpaned_position", str(widget.get_position()))
    def populate_action_groups(self):
        """
        Set up the actions for this component
        """
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ("palette_file_menu", None, _("File")),
            ("reference_resource_menu", None, _("Reference Resources")),
            ("remove_unused_paints", None, _("Remove Unused Paints"), None,
            _("Remove all unused paint colours from the palette."),
            self._remove_unused_paints_cb),
            ("quit_palette", Gtk.STOCK_QUIT, None, None,
            _("Quit this program."),
            self._quit_palette_cb),
            ("open_analysed_image_viewer", None, _("Open Analysed Image Viewer"), None,
            _("Open a tool for viewing analysed reference images."),
            self._open_analysed_image_viewer_cb),
            ("print_palette", Gtk.STOCK_PRINT, None, None,
            _("Print a text description of the palette."),
            self._print_palette_cb),
            ("take_screen_sample", None, _("Take Screen Sample"), None,
            _("Take a sample of an arbitrary selected section of the screen and add it to the clipboard."),
            lambda _action: screen.take_screen_sample()),
        ])
        self.action_groups[self.AC_HAVE_MIXTURE].add_actions([
            ("simplify_contributions", None, _("Simplify"), None,
            _("Simplify all colour contributions (by dividing by their greatest common divisor)."),
            self._simplify_contributions_cb),
            ("reset_contributions", None, _("Reset"), None,
            _("Reset all colour contributions to zero."),
            self._reset_contributions_cb),
            ("add_mixed_colour", None, _("Add"), None,
            _("Add this colour to the palette as a mixed colour."),
            self._add_mixed_colour_cb),
        ])
    def _show_wheel_colour_details_cb(self, _action, wheel):
        colour = wheel.popup_colour
        if hasattr(colour, "blobs"):
            self.MIXED_PAINT_INFORMATION_DIALOGUE(colour, self.mixed_colours.get_target_colour(colour)).show()
        else:
            gpaint.PaintColourInformationDialogue(colour).show()
        return True
    def __str__(self):
        paint_colours = self.paint_colours.get_colours()
        if len(paint_colours) == 0:
            return _("Empty Palette")
        string = _("Paint Colours:\n")
        for tc in paint_colours:
            string += "{0}: {1}: {2}\n".format(tc.name, tc.series.series_id.maker, tc.series.series_id.name)
        num_mixed_colours = len(self.mixed_colours)
        if num_mixed_colours == 0:
            return string
        # Print the list in the current order chosen by the user
        string += _("Mixed Colours:\n")
        for mc in self.mixed_colours.get_colours():
            string += "{0}: {1}\n".format(mc.name, round(mc.value, 2))
            for cc, parts in mc.blobs:
                if isinstance(cc, vpaint.PaintColour):
                    string += "\t {0}:\t{1}: {2}: {3}\n".format(parts, cc.name, cc.series.series_id.maker, cc.series.series_id.name)
                else:
                    string += "\t {0}:\t{1}\n".format(parts, cc.name)
        return string
    def pango_markup_chunks(self):
        """
        Format the palette description as a list of Pango markup chunks
        """
        paint_colours = self.paint_colours.get_paints()
        if len(paint_colours) == 0:
            return [cgi.escape(_("Empty Palette"))]
        # TODO: add paint series data in here
        string = "<b>" + cgi.escape(_("Palette:")) + "</b> "
        string += cgi.escape(time.strftime("%X: %A %x")) + "\n"
        if self.notes.get_text_length() > 0:
            string += "\n{0}\n".format(cgi.escape(self.notes.get_text()))
        chunks = [string]
        string = "<b>" + cgi.escape(_("Paint Colours:")) + "</b>\n\n"
        for pcol in paint_colours:
            string += "<span background=\"{0}\">\t</span> ".format(pango_rgb_str(pcol.rgb16))
            string += "{0}\n".format(cgi.escape(pcol.name))
        chunks.append(string)
        string = "<b>" + cgi.escape(_("Mixed Colours:")) + "</b>\n\n"
        for tmc in self.mixed_colours:
            mc = tmc[0]
            tc = tmc[1]
            string += "<span background=\"{0}\">\t</span> {1}: {2}\n".format(pango_rgb_str(mc.rgb16), cgi.escape(mc.name), cgi.escape(mc.notes))
            string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(mc.value_rgb.rgb16))
            string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(mc.hue_rgb.rgb16))
            string += "<span background=\"{0}\">\t</span>\n".format(pango_rgb_str(mc.warmth_rgb.rgb16))
            for blob in mc.blobs:
                string += "{0: 7d}:".format(blob.parts)
                string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(blob.paint.rgb16))
                string += " {0}\n".format(cgi.escape(blob.paint.name))
            chunks.append(string)
            string = "" # Necessary because we put header in the first chunk
        return chunks
    def _contributions_changed_cb(self, _widget, contributions):
        self.recalculate_colour(contributions + self.mixed_colours.get_contributions())
    def _mixed_contributions_changed_cb(self, _treemodel, contributions):
        self.recalculate_colour(contributions + self.paint_colours.get_contributions())
    def recalculate_colour(self, contributions):
        if len(contributions) > 0:
            new_colour = ArtMixture(contributions)
            self.mixpanel.set_bg_colour(new_colour.rgb)
            self.hcvw_display.set_colour(new_colour)
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_HAVE_MIXTURE, self.AC_MASK))
        else:
            self.mixpanel.set_bg_colour(None)
            self.hcvw_display.set_colour(None)
            self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_MASK))
    def _add_mixed_colour_cb(self,_action):
        # TODO: think about just doing self.simplify_parts() to do simplification
        paint_contribs = self.paint_colours.get_contributions()
        mixed_contribs = self.mixed_colours.get_contributions()
        if len(paint_contribs) + len(mixed_contribs) < 2:
            return
        gcd = utils.gcd(*[b.parts for b in paint_contribs + mixed_contribs])
        if gcd is not None and gcd > 1:
            paint_contribs = [pmix.BLOB(colour=tc.colour, parts=tc.parts / gcd) for tc in paint_contribs]
            mixed_contribs = [pmix.BLOB(colour=mc.colour, parts=mc.parts / gcd) for mc in mixed_contribs]
        name = _("Mix #{:03d}").format(self.mixed_count + 1)
        notes = self.ask_text(prompt= _("Notes for \"{0}\" :").format(name))
        if notes is not None:
            self.mixed_count += 1
            new_paint = MixedArtPaint(blobs=paint_contribs + mixed_contribs, name=name, notes=notes)
            self.mixed_colours.append_paint(new_paint)
            self.wheels.add_paint(new_paint)
            self.reset_parts()
    def reset_parts(self):
        self.paint_colours.reset_parts()
        self.mixed_colours.reset_parts()
    def _reset_contributions_cb(self, _action):
        self.reset_parts()
    def simplify_parts(self):
        paint_parts = [blob.parts for blob in self.paint_colours.get_contributions()]
        mixed_parts = [blob.parts for blob in self.mixed_colours.get_contributions()]
        gcd = utils.gcd(*(paint_parts + mixed_parts))
        self.paint_colours.divide_parts(gcd)
        self.mixed_colours.divide_parts(gcd)
    def _simplify_contributions_cb(self, _action):
        self.simplify_parts()
    def add_paint(self, paint_colour):
        self.paint_colours.add_paint(paint_colour)
        self.wheels.add_paint(paint_colour)
    def del_paint(self, paint_colour):
        self.paint_colours.del_paint(paint_colour)
        self.wheels.del_paint(paint_colour)
    def del_mixed(self, mixed):
        self.mixed_colours.remove_colour(mixed)
        self.wheels.del_colour(mixed)
    def _add_colours_to_palette_cb(self, selector, colours):
        for pcol in colours:
            if not self.paint_colours.has_paint(pcol):
                self.add_paint(pcol)
    def _remove_paint_colour_cb(self, widget, colour):
        """
        Respond to a request from a paint colour to be removed
        """
        users = self.mixed_colours.get_paint_users(colour)
        if len(users) > 0:
            string = _("Colour: \"{0}\" is used in:\n").format(colour)
            for user in users:
                string += "\t{0}\n".format(user.name)
            dlg = dialogue.ScrolledMessageDialog(text=string)
            Gdk.beep()
            dlg.run()
            dlg.destroy()
        else:
            self.del_paint(colour)
    def _remove_mixed_colours_cb(self, _action):
        colours = self.mixed_colours_view.get_selected_colours()
        being_used = {}
        for colour in colours:
            users = self.mixed_colours.get_colour_users(colour)
            if len(users) > 0:
                being_used[colour] = users
            else:
                self.del_mixed(colour)
        if being_used:
            string = ""
            for colour, users in being_used.items():
                string += _("Colour: \"{0}\" is used in:\n").format(colour.name)
                for user in users:
                    string += "\t{0}\n".format(user.name)
            dlg = dialogue.ScrolledMessageDialog(message_format=string)
            Gdk.beep()
            dlg.run()
            dlg.destroy()
    def _remove_unused_paints_cb(self, _action):
        colours = self.paint_colours.get_colours()
        for colour in colours:
            if len(self.mixed_colours.get_colour_users(colour)) == 0:
                self.del_paint(colour)
    def report_io_error(self, edata):
        msg = "{0}: {1}".format(edata.strerror, edata.filename)
        Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.BUTTONS_CLOSE, message_format=msg).run()
        return False
    def report_format_error(self, msg):
        Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.BUTTONS_CLOSE, message_format=msg).run()
        return False
    def launch_selector(self, filepath):
        try:
            fobj = open(filepath, "r")
            text = fobj.read()
            fobj.close()
        except IOError as edata:
            return self.report_io_error(edata)
        try:
            series = vpaint.PaintSeries.fm_definition(text)
        except vpaint.PaintSeries.ParseError as edata:
            return self.report_format_error(edata)
        # All OK so we can launch the selector
        selector = ArtPaintSelector(series)
        selector.connect("add-paint-colours", self._add_colours_to_palette_cb)
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_icon_from_file(icons.APP_ICON_FILE)
        window.set_title(_("Paint Series: {}").format(os.path.relpath(filepath)))
        window.connect("destroy", lambda w: w.destroy())
        window.add(selector)
        window.show()
        return True
    def _open_paint_series_selector_cb(self, _action):
        """
        Open a tool for adding paint colours to the palette
        Ask the user for the name of the file then open it.
        """
        parent = self.get_toplevel()
        dlg = Gtk.FileChooserDialog(
            title="Open Paint Series Description File",
            parent=parent if isinstance(parent, Gtk.Window) else None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        last_paint_file = recollect.get("paint_series_selector", "last_file")
        last_paint_dir = None if last_paint_file is None else os.path.dirname(last_paint_file)
        if last_paint_dir:
            dlg.set_current_folder(last_paint_dir)
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            if self.launch_selector(filepath):
                recollect.set("paint_series_selector", "last_file", filepath)
        dlg.destroy()
    def _print_palette_cb(self, _action):
        """
        Print the palette as simple text
        """
        # TODO: make printing more exotic
        printer.print_markup_chunks(self.pango_markup_chunks())
    def _open_analysed_image_viewer_cb(self, _action):
        """
        Launch a window containing an analysed image viewer
        """
        AnalysedImageViewer(self.get_toplevel()).show()
    def _quit_palette_cb(self, _action):
        """
        Exit the program
        """
        # TODO: add checks for unsaved work in palette before exiting
        Gtk.main_quit()

recollect.define("palette", "last_geometry", recollect.Defn(str, ""))

class TopLevelWindow(dialogue.MainWindow):
    """
    A top level window wrapper around a palette
    """
    def __init__(self):
        dialogue.MainWindow.__init__(self)
        self.parse_geometry(recollect.get("palette", "last_geometry"))
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_title("pcatk: Palette")
        self.palette = Palette()
        self.connect("destroy", self.palette._quit_palette_cb)
        self.connect("configure-event", self._configure_event_cb)
        self.add(self.palette)
        self.show_all()
    def _configure_event_cb(self, widget, event):
        recollect.set("palette", "last_geometry", "{0.width}x{0.height}+{0.x}+{0.y}".format(event))

recollect.define("analysed_image_viewer", "last_geometry", recollect.Defn(str, ""))
recollect.define("analysed_image_viewer", 'last_file', recollect.Defn(str, ''))

class AnalysedImageViewer(Gtk.Window, actions.CAGandUIManager):
    """
    A top level window for a colour sample file
    """
    UI_DESCR = """
    <ui>
      <menubar name="analysed_image_menubar">
        <menu action="analysed_image_file_menu">
          <menuitem action="open_analysed_image_file"/>
          <menuitem action="close_analysed_image_viewer"/>
        </menu>
      </menubar>
    </ui>
    """
    TITLE_TEMPLATE = _("pcatk: Analysed Image: {}")
    def __init__(self, parent):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        actions.CAGandUIManager.__init__(self)
        self.parse_geometry(recollect.get("analysed_image_viewer", "last_geometry"))
        self.connect("configure-event", self._configure_event_cb)
        self.set_icon_from_file(icons.APP_ICON_FILE)
        last_image_file = recollect.get("analysed_image_viewer", "last_file")
        if os.path.isfile(last_image_file):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(last_image_file)
            except GLib.GError:
                pixbuf = None
                last_image_file = None
        else:
            pixbuf = None
            last_image_file = None
        self.set_title(self.TITLE_TEMPLATE.format(None if last_image_file is None else os.path.relpath(last_image_file)))
        self.analyser = analyser.Analyser()
        self._menubar = self.ui_manager.get_widget("/analysed_image_menubar")
        #self.buttons = self.analyser.action_groups.create_action_button_box([
            #"zoom_in",
            #"zoom_out",
        #])
        vbox = Gtk.VBox()
        vbox.pack_start(self._menubar, expand=False, fill=True, padding=0)
        vbox.pack_start(self.analyser, expand=True, fill=True, padding=0)
        #vbox.pack_start(self.buttons, expand=False, fill=True, padding=0)
        vbox.pack_start(self.analyser.progress_bar, expand=False, fill=True, padding=0)
        self.add(vbox)
        #self.set_transient_for(parent)
        self.show_all()
        if pixbuf is not None:
            self.analyser.set_pixbuf(pixbuf)
    def _configure_event_cb(self, widget, event):
        recollect.set("analysed_image_viewer", "last_geometry", "{0.width}x{0.height}+{0.x}+{0.y}".format(event))
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ("analysed_image_file_menu", None, _("File")),
            ("open_analysed_image_file", Gtk.STOCK_OPEN, None, None,
            _("Load and analyse an image file as for reference."),
            self._open_analysed_image_file_cb),
            ("close_analysed_image_viewer", Gtk.STOCK_CLOSE, None, None,
            _("Close this window."),
            self._close_analysed_image_viewer_cb),
        ])
    def _open_analysed_image_file_cb(self, _action):
        """
        Ask the user for the name of the file then open it.
        """
        parent = self.get_toplevel()
        dlg = Gtk.FileChooserDialog(
            title=_("Open Image File"),
            parent=parent if isinstance(parent, Gtk.Window) else None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        last_image_file = recollect.get("analysed_image_viewer", "last_file")
        last_samples_dir = None if last_image_file is None else os.path.dirname(last_image_file)
        if last_samples_dir:
            dlg.set_current_folder(last_samples_dir)
        gff = Gtk.FileFilter()
        gff.set_name(_("Image Files"))
        gff.add_pixbuf_formats()
        dlg.add_filter(gff)
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            dlg.destroy()
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(filepath)
            except GLib.GError:
                msg = _("{}: Problem extracting image from file.").format(filepath)
                Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, message_format=msg).run()
                return
            recollect.set("analysed_image_viewer", "last_file", filepath)
            self.set_title(self.TITLE_TEMPLATE.format(None if filepath is None else os.path.relpath(filepath)))
            self.analyser.set_pixbuf(pixbuf)
        else:
            dlg.destroy()
    def _close_analysed_image_viewer_cb(self, _action):
        self.get_toplevel().destroy()
