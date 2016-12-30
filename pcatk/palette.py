### Copyright: Peter Williams (2012) - All rights reserved
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
Mix paint colours
'''

import collections
import os
import cgi
import time
#import glib

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import GLib as glib

from . import recollect
from . import actions
from . import tlview
from . import gtkpwx
from . import gpaint
from . import paint
from . import printer
from . import icons
from . import analyser
from . import utils

def pango_rgb_str(rgb, bits_per_channel=16):
    """
    Convert an rgb to a Pango colour description string
    """
    string = '#'
    for i in range(3):
        string += '{0:02X}'.format(rgb[i] >> (bits_per_channel - 8))
    return string

class Palette(Gtk.VBox, actions.CAGandUIManager):
    UI_DESCR = '''
    <ui>
        <menubar name='palette_menubar'>
            <menu action='palette_file_menu'>
                <menuitem action='print_palette'/>
                <menuitem action='quit_palette'/>
            </menu>
            <menu action='tube_series_menu'>
                <menuitem action='open_tube_series_selector'/>
            </menu>
            <menu action='reference_resource_menu'>
                <menuitem action='open_analysed_image_viewer'/>
            </menu>
        </menubar>
    </ui>
    '''
    AC_HAVE_MIXTURE, AC_MASK = actions.ActionCondns.new_flags_and_mask(1)
    def __init__(self):
        Gtk.VBox.__init__(self)
        actions.CAGandUIManager.__init__(self)
        # Components
        self.notes = Gtk.Entry()
        self.mixpanel = gpaint.ColourSampleArea()
        self.mixpanel.set_size_request(360, 240)
        self.hcvw_display = gpaint.HCVWDisplay()
        self.tube_colours = ColourPartsSpinButtonBox()
        self.tube_colours.connect('remove-colour', self._remove_tube_colour_cb)
        self.tube_colours.connect('contributions-changed', self._contributions_changed_cb)
        self.mixed_colours = PartsColourListStore()
        self.mixed_colours.connect('contributions-changed', self._mixed_contributions_changed_cb)
        self.mixed_colours_view = PartsColourListView(self.mixed_colours)
        self.mixed_colours_view.action_groups.connect_activate('remove_selected_colours', self._remove_mixed_colours_cb)
        self.mixed_count = 0
        self.wheels = gpaint.HueWheelNotebook()
        self.wheels.set_size_request(360, 360)
        self.buttons = self.action_groups.create_action_button_box([
            'add_mixed_colour',
            'simplify_contributions',
            'reset_contributions',
            'remove_unused_tubes',
            'take_screen_sample'
        ])
        menubar = self.ui_manager.get_widget('/palette_menubar')
        # Lay out components
        self.pack_start(menubar, expand=False, fill=True, padding=0)
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_('Notes:')), expand=False, fill=True, padding=0)
        hbox.pack_start(self.notes, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        hbox = Gtk.HBox()
        hbox.pack_start(self.wheels, expand=False, fill=True, padding=0)
        vbox = Gtk.VBox()
        vbox.pack_start(self.hcvw_display, expand=False, fill=True, padding=0)
        vbox.pack_start(gtkpwx.wrap_in_frame(self.mixpanel, Gtk.ShadowType.ETCHED_IN), expand=True, fill=True, padding=0)
        hbox.pack_start(vbox, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_('Tubes:')), expand=False, fill=True, padding=0)
        hbox.pack_start(self.tube_colours, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        self.pack_start(self.buttons, expand=False, fill=True, padding=0)
        self.pack_start(gtkpwx.wrap_in_scrolled_window(self.mixed_colours_view), expand=True, fill=True, padding=0)
        self.show_all()
        self.recalculate_colour([])
    def populate_action_groups(self):
        """
        Set up the actions for this component
        """
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ('palette_file_menu', None, _('File')),
            ('tube_series_menu', None, _('Tube Colour Series')),
            ('reference_resource_menu', None, _('Reference Resources')),
            ('remove_unused_tubes', None, _('Remove Unused Tubes'), None,
            _('Remove all unused tube colours from the palette.'),
            self._remove_unused_tubes_cb),
            ('open_tube_series_selector', Gtk.STOCK_OPEN, None, None,
            _('Open a tube colour series paint selector.'),
            self._open_tube_series_selector_cb),
            ('quit_palette', Gtk.STOCK_QUIT, None, None,
            _('Quit this program.'),
            self._quit_palette_cb),
            ('open_analysed_image_viewer', None, _('Open Analysed Image Viewer'), None,
            _('Open a tool for viewing analysed reference images.'),
            self._open_analysed_image_viewer_cb),
            ('print_palette', Gtk.STOCK_PRINT, None, None,
            _('Print a text description of the palette.'),
            self._print_palette_cb),
            ('take_screen_sample', None, _('Take Screen Sample'), None,
            _('Take a sample of an arbitrary selected section of the screen and add it to the clipboard.'),
            gtkpwx.take_screen_sample),
        ])
        self.action_groups[self.AC_HAVE_MIXTURE].add_actions([
            ('simplify_contributions', None, _('Simplify'), None,
            _('Simplify all colour contributions (by dividing by their greatest common divisor).'),
            self._simplify_contributions_cb),
            ('reset_contributions', None, _('Reset'), None,
            _('Reset all colour contributions to zero.'),
            self._reset_contributions_cb),
            ('add_mixed_colour', None, _('Add'), None,
            _('Add this colour to the palette as a mixed colour.'),
            self._add_mixed_colour_cb),
        ])
    def __str__(self):
        tube_colours = self.tube_colours.get_colours()
        if len(tube_colours) == 0:
            return _('Empty Palette')
        string = _('Tube Colours:\n')
        for tc in tube_colours:
            string += '{0}: {1}: {2}\n'.format(tc.name, tc.series.series_id.maker, tc.series.series_id.name)
        num_mixed_colours = len(self.mixed_colours)
        if num_mixed_colours == 0:
            return string
        # Print the list in the current order chosen by the user
        string += _('Mixed Colours:\n')
        for mc in self.mixed_colours.get_colours():
            string += '{0}: {1}\n'.format(mc.name, round(mc.value, 2))
            for cc, parts in mc.blobs:
                if isinstance(cc, paint.TubeColour):
                    string += '\t {0}:\t{1}: {2}: {3}\n'.format(parts, cc.name, cc.series.series_id.maker, cc.series.series_id.name)
                else:
                    string += '\t {0}:\t{1}\n'.format(parts, cc.name)
        return string
    def pango_markup_chunks(self):
        """
        Format the palette description as a list of Pango markup chunks
        """
        tube_colours = self.tube_colours.get_colours()
        if len(tube_colours) == 0:
            return [cgi.escape(_('Empty Palette'))]
        # TODO: add tube series data in here
        string = '<b>' + cgi.escape(_('Palette:')) + '</b> '
        string += cgi.escape(time.strftime('%X: %A %x')) + '\n'
        if self.notes.get_text_length() > 0:
            string += '\n{0}\n'.format(cgi.escape(self.notes.get_text()))
        chunks = [string]
        string = '<b>' + cgi.escape(_('Tube Colours:')) + '</b>\n\n'
        for tc in tube_colours:
            string += '<span background="{0}">\t</span> '.format(pango_rgb_str(tc))
            string += '{0}\n'.format(cgi.escape(tc.name))
        chunks.append(string)
        string = '<b>' + cgi.escape(_('Mixed Colours:')) + '</b>\n\n'
        for mc in self.mixed_colours.get_colours():
            string += '<span background="{0}">\t</span> {1}: {2}\n'.format(pango_rgb_str(mc), cgi.escape(mc.name), cgi.escape(mc.notes))
            string += '<span background="{0}">\t</span>'.format(pango_rgb_str(mc.value_rgb()))
            string += '<span background="{0}">\t</span>'.format(pango_rgb_str(mc.hue_rgb))
            string += '<span background="{0}">\t</span>\n'.format(pango_rgb_str(mc.warmth_rgb()))
            for blob in mc.blobs:
                string += '{0: 7d}:'.format(blob.parts)
                string += '<span background="{0}">\t</span>'.format(pango_rgb_str(blob.colour))
                string += ' {0}\n'.format(cgi.escape(blob.colour.name))
            chunks.append(string)
            string = '' # Necessary because we put header in the first chunk
        return chunks
    def _contributions_changed_cb(self, _widget, contributions):
        self.recalculate_colour(contributions + self.mixed_colours.get_contributions())
    def _mixed_contributions_changed_cb(self, _treemodel, contributions):
        self.recalculate_colour(contributions + self.tube_colours.get_contributions())
    def recalculate_colour(self, contributions):
        new_colour = paint.MixedColour(contributions)
        self.mixpanel.set_bg_colour(new_colour.rgb)
        self.hcvw_display.set_colour(new_colour)
        if len(contributions) > 1:
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_HAVE_MIXTURE, self.AC_MASK))
        else:
            self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_MASK))
    def _add_mixed_colour_cb(self,_action):
        # TODO: think about just doing self.simplify_parts() to do simplification
        tube_contribs = self.tube_colours.get_contributions()
        mixed_contribs = self.mixed_colours.get_contributions()
        if len(tube_contribs) + len(mixed_contribs) < 2:
            return
        gcd = utils.gcd(*[b.parts for b in tube_contribs + mixed_contribs])
        if gcd is not None and gcd > 1:
            tube_contribs = [paint.BLOB(colour=tc.colour, parts=tc.parts / gcd) for tc in tube_contribs]
            mixed_contribs = [paint.BLOB(colour=mc.colour, parts=mc.parts / gcd) for mc in mixed_contribs]
        name = _('Mix #{:03d}').format(self.mixed_count + 1)
        dlg = gtkpwx.TextEntryDialog(title='', prompt= _('Notes for "{0}" :').format(name))
        if dlg.run() == Gtk.ResponseType.OK:
            self.mixed_count += 1
            notes = dlg.entry.get_text()
            new_colour = paint.NamedMixedColour(blobs=tube_contribs + mixed_contribs, name=name, notes=notes)
            self.mixed_colours.append_colour(new_colour)
            self.wheels.add_colour(new_colour)
            self.reset_parts()
        dlg.destroy()
    def reset_parts(self):
        self.tube_colours.reset_parts()
        self.mixed_colours.reset_parts()
    def _reset_contributions_cb(self, _action):
        self.reset_parts()
    def simplify_parts(self):
        tube_parts = [blob.parts for blob in self.tube_colours.get_contributions()]
        mixed_parts = [blob.parts for blob in self.mixed_colours.get_contributions()]
        gcd = utils.gcd(*(tube_parts + mixed_parts))
        self.tube_colours.divide_parts(gcd)
        self.mixed_colours.divide_parts(gcd)
    def _simplify_contributions_cb(self, _action):
        self.simplify_parts()
    def add_tube(self, tube):
        self.tube_colours.add_colour(tube)
        self.wheels.add_colour(tube)
    def del_tube(self, tube):
        self.tube_colours.del_colour(tube)
        self.wheels.del_colour(tube)
    def del_mixed(self, mixed):
        self.mixed_colours.remove_colour(mixed)
        self.wheels.del_colour(mixed)
    def _add_colours_to_palette_cb(self, selector, colours):
        for tc in colours:
            if not self.tube_colours.has_colour(tc):
                self.add_tube(tc)
    def _remove_tube_colour_cb(self, widget, colour):
        """
        Respond to a request from a tube colour to be removed
        """
        users = self.mixed_colours.get_colour_users(colour)
        if len(users) > 0:
            string = _('Colour: "{0}" is used in:\n').format(colour)
            for user in users:
                string += '\t{0}\n'.format(user.name)
            dlg = gtkpwx.ScrolledMessageDialog(message_format=string)
            Gdk.beep()
            dlg.run()
            dlg.destroy()
        else:
            self.del_tube(colour)
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
            string = ''
            for colour, users in being_used.items():
                string += _('Colour: "{0}" is used in:\n').format(colour.name)
                for user in users:
                    string += '\t{0}\n'.format(user.name)
            dlg = gtkpwx.ScrolledMessageDialog(message_format=string)
            Gdk.beep()
            dlg.run()
            dlg.destroy()
    def _remove_unused_tubes_cb(self, _action):
        colours = self.tube_colours.get_colours()
        for colour in colours:
            if len(self.mixed_colours.get_colour_users(colour)) == 0:
                self.del_tube(colour)
    def report_io_error(self, edata):
        msg = '{0}: {1}'.format(edata.strerror, edata.filename)
        Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.BUTTONS_CLOSE, message_format=msg).run()
        return False
    def report_format_error(self, msg):
        Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.BUTTONS_CLOSE, message_format=msg).run()
        return False
    def launch_selector(self, filepath):
        try:
            fobj = open(filepath, 'r')
            text = fobj.read()
            fobj.close()
        except IOError as edata:
            return self.report_io_error(edata)
        try:
            series = paint.Series.fm_definition(text)
        except paint.Series.ParseError as edata:
            return self.report_format_error(edata)
        # All OK so we can launch the selector
        selector = TubeColourSelector(series)
        selector.connect('add-tube-colours', self._add_colours_to_palette_cb)
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_icon_from_file(icons.APP_ICON_FILE)
        window.set_title(_('Tube Series: {}').format(os.path.relpath(filepath)))
        window.connect('destroy', lambda w: w.destroy())
        window.add(selector)
        window.show()
        return True
    def _open_tube_series_selector_cb(self, _action):
        """
        Open a tool for adding tube colours to the palette
        Ask the user for the name of the file then open it.
        """
        parent = self.get_toplevel()
        dlg = Gtk.FileChooserDialog(
            title='Open Tube Series Description File',
            parent=parent if isinstance(parent, Gtk.Window) else None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        last_paint_file = recollect.get('tube_series_selector', 'last_file')
        last_paint_dir = None if last_paint_file is None else os.path.dirname(last_paint_file)
        if last_paint_dir:
            dlg.set_current_folder(last_paint_dir)
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            if self.launch_selector(filepath):
                recollect.set('tube_series_selector', 'last_file', filepath)
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

def colour_parts_adjustment():
    return Gtk.Adjustment(0, 0, 999, 1, 10, 0)

class ColourPartsSpinButton(Gtk.EventBox, actions.CAGandUIManager):
    UI_DESCR = '''
        <ui>
            <popup name='colour_spinner_popup'>
                <menuitem action='tube_colour_info'/>
                <menuitem action='remove_me'/>
            </popup>
        </ui>
        '''
    def __init__(self, colour, *kwargs):
        Gtk.EventBox.__init__(self)
        actions.CAGandUIManager.__init__(self, popup='/colour_spinner_popup')
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.set_size_request(85, 40)
        self.colour = colour
        self.entry = Gtk.SpinButton()
        self.entry.set_adjustment(colour_parts_adjustment())
        self.entry.set_numeric(True)
        self.entry.connect('button_press_event', self._button_press_cb)
        self.set_tooltip_text(str(colour))
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        hbox = Gtk.HBox()
        hbox.pack_start(gpaint.ColouredRectangle(self.colour), expand=True, fill=True, padding=0)
        vbox = Gtk.VBox()
        vbox.pack_start(gpaint.ColouredRectangle(self.colour), expand=True, fill=True, padding=0)
        vbox.pack_start(self.entry, expand=False, fill=True, padding=0)
        vbox.pack_start(gpaint.ColouredRectangle(self.colour), expand=True, fill=True, padding=0)
        hbox.pack_start(vbox, expand=False, fill=True, padding=0)
        hbox.pack_start(gpaint.ColouredRectangle(self.colour, (5, -1)), expand=False, fill=True, padding=0)
        frame.add(hbox)
        self.add(frame)
        self.show_all()
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_DONT_CARE].add_actions(
            [
                ('tube_colour_info', Gtk.STOCK_INFO, None, None,
                 _('Detailed information for this tube colour.'),
                 self._tube_colour_info_cb
                ),
                ('remove_me', Gtk.STOCK_REMOVE, None, None,
                 _('Remove this tube colour from the palette.'),
                ),
            ]
        )
    def get_parts(self):
        return self.entry.get_value_as_int()
    def set_parts(self, parts):
        return self.entry.set_value(parts)
    def divide_parts(self, divisor):
        return self.entry.set_value(self.entry.get_value_as_int() / divisor)
    def get_blob(self):
        return paint.BLOB(self.colour, self.get_parts())
    def _tube_colour_info_cb(self, _action):
        TubeColourInformationDialogue(self.colour).show()

class ColourPartsSpinButtonBox(Gtk.VBox):
    """
    A dynamic array of coloured spinners
    """
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.__spinbuttons = []
        self.__hboxes = []
        self.__count = 0
        self.__ncols = 8
        self.__suppress_change_notification = False
    def add_colour(self, colour):
        """
        Add a spinner for the given colour to the box
        """
        spinbutton = ColourPartsSpinButton(colour)
        spinbutton.action_groups.connect_activate('remove_me', self._remove_me_cb, spinbutton)
        spinbutton.entry.connect('value-changed', self._spinbutton_value_changed_cb)
        self.__spinbuttons.append(spinbutton)
        self._pack_append(spinbutton)
        self.show_all()
    def _pack_append(self, spinbutton):
        if self.__count % self.__ncols == 0:
            self.__hboxes.append(Gtk.HBox())
            self.pack_start(self.__hboxes[-1], expand=False, fill=True, padding=0)
        self.__hboxes[-1].pack_start(spinbutton, expand=False, fill=True, padding=0)
        self.__count += 1
    def _unpack_all(self):
        """
        Unpack all the spinbuttons and hboxes
        """
        for hbox in self.__hboxes:
            for child in hbox.get_children():
                hbox.remove(child)
            self.remove(hbox)
        self.__hboxes = []
        self.__count = 0
    def _remove_me_cb(self, _action, spinbutton):
        """
        Signal anybody who cares that spinbutton.colour should be removed
        """
        self.emit('remove-colour', spinbutton.colour)
    def _spinbutton_value_changed_cb(self, spinbutton):
        """
        Signal those interested that our contributions have changed
        """
        if not self.__suppress_change_notification:
            self.emit('contributions-changed', self.get_contributions())
    def del_colour(self, colour):
        # do this the easy way by taking them all out and putting back
        # all but the one to be deleted
        self._unpack_all()
        for spinbutton in self.__spinbuttons[:]:
            if spinbutton.colour == colour:
                self.__spinbuttons.remove(spinbutton)
            else:
                self._pack_append(spinbutton)
        self.show_all()
    def get_colours(self):
        return [spinbutton.colour for spinbutton in self.__spinbuttons]
    def get_colours_with_zero_parts(self):
        return [spinbutton.colour for spinbutton in self.__spinbuttons if spinbutton.get_parts() == 0]
    def has_colour(self, colour):
        """
        Do we already contain the given colour?
        """
        for spinbutton in self.__spinbuttons:
            if spinbutton.colour == colour:
                return True
        return False
    def get_contributions(self):
        """
        Return a list of tube colours with non zero parts
        """
        return [spinbutton.get_blob() for spinbutton in self.__spinbuttons if spinbutton.get_parts() > 0]
    def divide_parts(self, divisor):
        if divisor is not None and divisor > 1:
            self.__suppress_change_notification = True
            for spinbutton in self.__spinbuttons:
                spinbutton.divide_parts(divisor)
            self.__suppress_change_notification = False
            self.emit('contributions-changed', self.get_contributions())
    def reset_parts(self):
        """
        Reset all spinbutton values to zero
        """
        self.__suppress_change_notification = True
        for spinbutton in self.__spinbuttons:
            spinbutton.set_parts(0)
        self.__suppress_change_notification = False
        self.emit('contributions-changed', self.get_contributions())
GObject.signal_new('remove-colour', ColourPartsSpinButtonBox, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))
GObject.signal_new('contributions-changed', ColourPartsSpinButtonBox, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

class PartsColourListStore(gpaint.ColourListStore):
    ROW = paint.BLOB
    TYPES = ROW(colour=object, parts=int)

    def append_colour(self, colour):
        self.append(self.ROW(parts=0, colour=colour))
    def get_parts(self, colour):
        """
        Return the number of parts selected for the given colour
        """
        model_iter = self.find_named(lambda x: x.colour == colour)
        if model_iter is None:
            raise LookupError()
        return self.get_value_named(model_iter, 'parts')
    def reset_parts(self):
        """
        Reset the number of parts for all colours to zero
        """
        model_iter = self.get_iter_first()
        while model_iter is not None:
            self.set_value_named(model_iter, 'parts', 0)
            model_iter = self.iter_next(model_iter)
        self.emit('contributions-changed', [])
    def divide_parts(self, divisor):
        """
        Reset the number of parts for all colours to zero
        """
        if divisor is not None and divisor > 1:
            model_iter = self.get_iter_first()
            while model_iter is not None:
                parts = self.get_value_named(model_iter, 'parts')
                self.set_value_named(model_iter, 'parts', parts / divisor)
                model_iter = self.iter_next(model_iter)
            self.emit('contributions-changed', self.get_contributions())
    def get_contributions(self):
        """
        Return a list of MODEL.ROW() tuples where parts is greater than zero
        """
        return [row for row in self.named() if row.parts > 0]
    def get_colour_users(self, colour):
        return [row.colour for row in self.named() if row.colour.contains_colour(colour)]
    def process_parts_change(self, blob):
        """
        Work out contributions with modifications in blob.
        This is necessary because the parts field in the model hasn't
        been updated yet as it causes a "jerky" appearance in the
        CellRendererSpin due to SpinButton being revreated every time
        an edit starts and updating the model causes restart of edit.
        """
        contributions = []
        for row in self.named():
            if row.colour == blob.colour:
                if blob.parts > 0:
                    contributions.append(blob)
            elif row.parts > 0:
                contributions.append(row)
        self.emit('contributions-changed', contributions)
    def _parts_value_changed_cb(self, cell, path, spinbutton):
        """
        Change the model for a change to a spinbutton value
        """
        new_parts = spinbutton.get_value_as_int()
        row = self.get_row(self.get_iter(path))
        self.process_parts_change(paint.BLOB(colour=row.colour, parts=new_parts))
    def _notes_edited_cb(self, cell, path, new_text):
        self[path][0].notes = new_text
GObject.signal_new('contributions-changed', PartsColourListStore, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT, ))

def notes_cell_data_func(column, cell, model, model_iter, *args):
    colour = model.get_value_named(model_iter, 'colour')
    cell.set_property('text', colour.notes)
    cell.set_property('background-gdk', Gdk.Color(*colour.rgb))
    cell.set_property('foreground-gdk', gtkpwx.best_foreground(colour.rgb))

def generate_colour_parts_list_spec(view, model):
    """
    Generate the SPECIFICATION for a paint colour parts list
    """
    parts_col_spec = tlview.ColumnSpec(
        title =_('Parts'),
        properties={},
        sort_key_function=lambda row: row.parts,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=tlview.CellRendererSpin,
                    expand=None,
                    properties={'editable' : True, 'adjustment' : colour_parts_adjustment(), 'width-chars' : 8},
                    signal_handlers = {"value-changed" : model._parts_value_changed_cb},
                    start=False
                ),
                cell_data_function_spec=None,
                attributes={'text' : model.col_index('parts')}
            ),
        ]
    )
    notes_col_spec = tlview.ColumnSpec(
        title =_('Notes'),
        properties={'resizable' : True, 'expand' : True},
        sort_key_function=lambda row: row.colour.notes,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties={'editable' : True, },
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
    name_col_spec = gpaint.colour_attribute_column_spec(gpaint.TNS(_('Name'), 'name', {}, lambda row: row.colour.name))
    attr_cols_specs = [gpaint.colour_attribute_column_spec(tns) for tns in gpaint.COLOUR_ATTRS[1:]]
    return tlview.ViewSpec(
        properties={},
        selection_mode=Gtk.SelectionMode.MULTIPLE,
        columns=[parts_col_spec, name_col_spec, notes_col_spec] + attr_cols_specs
    )

class PartsColourListView(gpaint.ColourListView):
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='show_colour_details'/>
            <menuitem action='remove_selected_colours'/>
        </popup>
    </ui>
    '''
    MODEL = PartsColourListStore
    SPECIFICATION = generate_colour_parts_list_spec
    def __init__(self, *args, **kwargs):
        gpaint.ColourListView.__init__(self, *args, **kwargs)
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
            [
                ('show_colour_details', Gtk.STOCK_INFO, None, None,
                 _('Show a detailed description of the selected colour.'),
                self._show_colour_details_cb),
            ],
        )
        self.action_groups[actions.AC_SELN_MADE].add_actions(
            [
                ('remove_selected_colours', Gtk.STOCK_REMOVE, None, None,
                 _('Remove the selected colours from the list.'), ),
            ]
        )
    def _show_colour_details_cb(self, _action):
        colour = self.get_selected_colours()[0]
        if isinstance(colour, paint.NamedMixedColour):
            MixedColourInformationDialogue(colour).show()
        else:
            TubeColourInformationDialogue(colour).show()

class SelectColourListView(gpaint.ColourListView):
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='show_colour_details'/>
            <menuitem action='add_colours_to_palette'/>
        </popup>
    </ui>
    '''
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_SELN_UNIQUE].add_actions(
            [
                ('show_colour_details', Gtk.STOCK_INFO, None, None,
                 _('Show a detailed description of the selected colour.'),),
            ]
        )
        self.action_groups[actions.AC_SELN_MADE].add_actions(
            [
                ('add_colours_to_palette', Gtk.STOCK_ADD, None, None,
                 _('Add the selected colours to the palette.'),),
            ]
        )

class TubeColourSelector(Gtk.VBox):
    """
    A widget for adding tube colours to the palette
    """
    def __init__(self, tube_series):
        Gtk.VBox.__init__(self)
        # components
        wheels = gpaint.HueWheelNotebook()
        self.tube_colours_view = SelectColourListView()
        self.tube_colours_view.set_size_request(480, 360)
        model = self.tube_colours_view.get_model()
        for colour in tube_series.tube_colours.values():
            model.append_colour(colour)
            wheels.add_colour(colour)
        maker = Gtk.Label(_('Manufacturer: {0}'.format(tube_series.series_id.maker)))
        sname = Gtk.Label(_('Series Name: {0}'.format(tube_series.series_id.name)))
        # make connections
        self.tube_colours_view.action_groups.connect_activate('show_colour_details', self._show_colour_details_cb)
        self.tube_colours_view.action_groups.connect_activate('add_colours_to_palette', self._add_colours_to_palette_cb)
        # lay the components out
        self.pack_start(sname, expand=False, fill=True, padding=0)
        self.pack_start(maker, expand=False, fill=True, padding=0)
        hbox = Gtk.HBox()
        hbox.pack_start(wheels, expand=True, fill=True, padding=0)
        hbox.pack_start(gtkpwx.wrap_in_scrolled_window(self.tube_colours_view), expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=True, fill=True, padding=0)
        self.show_all()
    def _show_colour_details_cb(self, _action):
        colour = self.tube_colours_view.get_selected_colours()[0]
        TubeColourInformationDialogue(colour).show()
    def _add_colours_to_palette_cb(self, _action):
        """
        Add the currently selected colours to the palette.
        """
        self.emit('add-tube-colours', self.tube_colours_view.get_selected_colours())
GObject.signal_new('add-tube-colours', TubeColourSelector, GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))

class TopLevelWindow(Gtk.Window):
    """
    A top level window wrapper around a palette
    """
    def __init__(self):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_title('pcatk: Palette')
        self.palette = Palette()
        self.connect("destroy", self.palette._quit_palette_cb)
        self.add(self.palette)
        self.show_all()

class AnalysedImageViewer(Gtk.Window, actions.CAGandUIManager):
    """
    A top level window for a colour sample file
    """
    UI_DESCR = '''
    <ui>
      <menubar name='analysed_image_menubar'>
        <menu action='analysed_image_file_menu'>
          <menuitem action='open_analysed_image_file'/>
          <menuitem action='close_analysed_image_viewer'/>
        </menu>
      </menubar>
    </ui>
    '''
    TITLE_TEMPLATE = _('pcatk: Analysed Image: {}')
    def __init__(self, parent):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)
        actions.CAGandUIManager.__init__(self)
        self.set_icon_from_file(icons.APP_ICON_FILE)
        self.set_size_request(300, 200)
        last_image_file = recollect.get('analysed_image_viewer', 'last_file')
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
        self._menubar = self.ui_manager.get_widget('/analysed_image_menubar')
        #self.buttons = self.analyser.action_groups.create_action_button_box([
            #'zoom_in',
            #'zoom_out',
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
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ('analysed_image_file_menu', None, _('File')),
            ('open_analysed_image_file', Gtk.STOCK_OPEN, None, None,
            _('Load and analyse an image file as for reference.'),
            self._open_analysed_image_file_cb),
            ('close_analysed_image_viewer', Gtk.STOCK_CLOSE, None, None,
            _('Close this window.'),
            self._close_analysed_image_viewer_cb),
        ])
    def _open_analysed_image_file_cb(self, _action):
        """
        Ask the user for the name of the file then open it.
        """
        parent = self.get_toplevel()
        dlg = Gtk.FileChooserDialog(
            title=_('Open Image File'),
            parent=parent if isinstance(parent, Gtk.Window) else None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
        )
        last_image_file = recollect.get('analysed_image_viewer', 'last_file')
        last_samples_dir = None if last_image_file is None else os.path.dirname(last_image_file)
        if last_samples_dir:
            dlg.set_current_folder(last_samples_dir)
        gff = Gtk.FileFilter()
        gff.set_name(_('Image Files'))
        gff.add_pixbuf_formats()
        dlg.add_filter(gff)
        if dlg.run() == Gtk.ResponseType.OK:
            filepath = dlg.get_filename()
            dlg.destroy()
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(filepath)
            except GLib.GError:
                msg = _('{}: Problem extracting image from file.').format(filepath)
                Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, message_format=msg).run()
                return
            recollect.set('analysed_image_viewer', 'last_file', filepath)
            self.set_title(self.TITLE_TEMPLATE.format(None if filepath is None else os.path.relpath(filepath)))
            self.analyser.set_pixbuf(pixbuf)
        else:
            dlg.destroy()
    def _close_analysed_image_viewer_cb(self, _action):
        self.get_toplevel().destroy()

class TubeColourInformationDialogue(Gtk.Dialog):
    """
    A dialog to display the detailed information for a tube colour
    """
    def __init__(self, colour, parent=None):
        Gtk.Dialog.__init__(self, title=_('Tube Colour: {}').format(colour.name), parent=parent)
        vbox = self.get_content_area()
        vbox.pack_start(gtkpwx.ColouredLabel(colour.name, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(gtkpwx.ColouredLabel(colour.series.series_id.name, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(gtkpwx.ColouredLabel(colour.series.series_id.maker, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(gpaint.HCVWDisplay(colour), expand=False, fill=True, padding=0)
        vbox.pack_start(Gtk.Label(colour.transparency.description()), expand=False, fill=True, padding=0)
        vbox.pack_start(Gtk.Label(colour.permanence.description()), expand=False, fill=True, padding=0)
        vbox.show_all()

def generate_components_list_spec(view, model):
    """
    Generate the SPECIFICATION for a mixed colour components list
    """
    parts_col_spec = tlview.ColumnSpec(
        title =_('Parts'),
        properties={},
        sort_key_function=lambda row: row.parts,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties={'width-chars' : 8},
                    start=False
                ),
                cell_data_function_spec=None,
                attributes={'text' : model.col_index('parts')}
            ),
        ]
    )
    name_col_spec = gpaint.colour_attribute_column_spec(gpaint.TNS(_('Name'), 'name', {'expand' : True}, lambda row: row.colour.name))
    attr_cols_specs = [gpaint.colour_attribute_column_spec(tns) for tns in gpaint.COLOUR_ATTRS[1:]]
    return tlview.ViewSpec(
        properties={},
        selection_mode=Gtk.SelectionMode.SINGLE,
        columns=[parts_col_spec, name_col_spec] + attr_cols_specs
    )

class ComponentsListView(PartsColourListView):
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='show_colour_details'/>
        </popup>
    </ui>
    '''
    MODEL = PartsColourListStore
    SPECIFICATION = generate_components_list_spec

    def _set_cell_connections(self):
        pass

class MixedColourInformationDialogue(Gtk.Dialog):
    """
    A dialog to display the detailed information for a mixed colour
    """

    def __init__(self, colour, parent=None):
        Gtk.Dialog.__init__(self, title=_('Mixed Colour: {}').format(colour.name), parent=parent)
        vbox = self.get_content_area()
        vbox.pack_start(gtkpwx.ColouredLabel(colour.name, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(gtkpwx.ColouredLabel(colour.notes, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(gpaint.HCVWDisplay(colour), expand=False, fill=True, padding=0)
        vbox.pack_start(Gtk.Label(colour.transparency.description()), expand=False, fill=True, padding=0)
        vbox.pack_start(Gtk.Label(colour.permanence.description()), expand=False, fill=True, padding=0)
        self.cview = ComponentsListView()
        for component in colour.blobs:
            self.cview.model.append(component)
        vbox.pack_start(self.cview, expand=False, fill=True, padding=0)
        vbox.show_all()
    def unselect_all(self):
        self.cview.get_selection().unselect_all()
