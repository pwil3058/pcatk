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
Widgets the work with paint colours
'''

import collections
import math
import fractions
import sys
import cairo

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from . import options
from . import utils
from . import actions
from . import tlview
from . import gtkpwx
from . import paint
from . import recollect
from . import rgbh

if __name__ == '__main__':
    _ = lambda x: x
    import doctest

class MappedFloatChoice(gtkpwx.Choice):
    MFDC = None
    def __init__(self):
        choices = ['{0}\t- {1}'.format(item[0], item[1]) for item in self.MFDC.MAP]
        gtkpwx.Choice.__init__(self, choices=choices)
    def get_selection(self):
        return self.MFDC(self.MFDC.MAP[gtkpwx.Choice.get_selection(self)].abbrev)
    def set_selection(self, mapped_float):
        abbrev = str(mapped_float)
        for i, rating in enumerate(self.MFDC.MAP):
            if abbrev == rating.abbrev:
                gtkpwx.Choice.set_selection(self, i)
                return
        raise paint.MappedFloat.BadValue()

class TransparencyChoice(MappedFloatChoice):
    MFDC = paint.Transparency

class PermanenceChoice(MappedFloatChoice):
    MFDC = paint.Permanence

def get_colour(arg):
    if isinstance(arg, paint.Colour):
        return arg.rgb
    else:
        return arg

class ColouredRectangle(Gtk.DrawingArea):
    def __init__(self, colour, size_request=None):
        Gtk.DrawingArea.__init__(self)
        if size_request is not None:
            self.set_size_request(*size_request)
        self.colour = get_colour(paint.RGB_WHITE) if colour is None else get_colour(colour)
        self.connect("draw", self.expose_cb)
    def expose_cb(self, _widget, cairo_ctxt):
        cairo_ctxt.set_source_rgb(*self.colour)
        cairo_ctxt.paint()
        return True

class ColourSampleArea(Gtk.DrawingArea, actions.CAGandUIManager):
    """
    A coloured drawing area onto which samples can be dropped.
    """
    UI_DESCR = '''
    <ui>
        <popup name='colour_sample_popup'>
            <menuitem action='paste_sample_image'/>
            <menuitem action='remove_sample_images'/>
        </popup>
    </ui>
    '''
    AC_SAMPLES_PASTED, AC_MASK = actions.ActionCondns.new_flags_and_mask(1)
    def __init__(self, single_sample=False, default_bg=None):
        Gtk.DrawingArea.__init__(self)

        self.set_size_request(200, 200)
        self._ptr_x = self._ptr_y = 100
        self._sample_images = []
        self._single_sample = single_sample
        self.default_bg_colour = self.bg_colour = get_colour(paint.RGB_WHITE) if default_bg is None else get_colour(default_bg)

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("draw", self.expose_cb)
        self.connect('motion_notify_event', self._motion_notify_cb)

        actions.CAGandUIManager.__init__(self, popup='/colour_sample_popup')
    def populate_action_groups(self):
        self.action_groups[actions.AC_DONT_CARE].add_actions(
            [
                ('paste_sample_image', Gtk.STOCK_PASTE, None, None,
                 _('Paste an image from clipboard at this position.'), self._paste_fm_clipboard_cb),
            ])
        self.action_groups[self.AC_SAMPLES_PASTED].add_actions(
            [
                ('remove_sample_images', Gtk.STOCK_REMOVE, None, None,
                 _('Remove all sample images from from the sample area.'), self._remove_sample_images_cb),
            ])
    def get_masked_condns(self):
        if len(self._sample_images) > 0:
            return actions.MaskedCondns(self.AC_SAMPLES_PASTED, self.AC_MASK)
        else:
            return actions.MaskedCondns(0, self.AC_MASK)
    def _motion_notify_cb(self, widget, event):
        if event.type == Gdk.EventType.MOTION_NOTIFY:
            self._ptr_x = event.x
            self._ptr_y = event.y
            return True
        return False
    def _remove_sample_images_cb(self, action):
        """
        Remove all samples.
        """
        self.erase_samples()
    def _paste_fm_clipboard_cb(self, _action):
        """
        Paste from the clipboard
        """
        cbd = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        # WORKAROUND: clipboard bug on Windows
        if sys.platform.startswith("win"): cbd.request_targets(lambda a, b, c: None)
        cbd.request_image(self._image_from_clipboard_cb, (self._ptr_x, self._ptr_y))
    def _image_from_clipboard_cb(self, cbd, img, posn):
        if img is None:
            dlg = Gtk.MessageDialog(
                parent=self.get_toplevel(),
                flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
                buttons=Gtk.ButtonsType.OK,
                message_format=_('No image data on clipboard.')
            )
            dlg.run()
            dlg.destroy()
        else:
            if self._single_sample and len(self._sample_images) == 1:
                self._sample_images[0] = (int(posn[0]), int(posn[1]), img)
            else:
                self._sample_images.append((int(posn[0]), int(posn[1]), img))
            self.queue_draw()
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_SAMPLES_PASTED, self.AC_MASK))
            self.emit('samples-changed', len(self._sample_images))
    def erase_samples(self):
        """
        Erase all samples from the drawing area
        """
        self._sample_images = []
        self.queue_draw()
        self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_MASK))
        self.emit('samples-changed', len(self._sample_images))
    def get_samples(self):
        """
        Return a list containing all samples from the drawing area
        """
        return [sample[2] for sample in self._sample_images]
    def set_bg_colour(self, colour):
        """
        Set the drawing area to the specified colour
        """
        self.bg_colour = get_colour(colour)
        self.queue_draw()
    def expose_cb(self, _widget, cairo_ctxt):
        """
        Repaint the drawing area
        """
        cairo_ctxt.set_source_rgb(*self.bg_colour.converted_to(rgbh.RGBPN))
        cairo_ctxt.paint()
        for sample in self._sample_images:
            sfc = Gdk.cairo_surface_create_from_pixbuf(sample[2], 0, None)
            cairo_ctxt.set_source_surface(sfc, sample[0], sample[1])
            cairo_ctxt.paint()
        return True
GObject.signal_new('samples-changed', ColourSampleArea, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_INT,))

def generate_spectral_rgb_buf(hue, spread, width, height, backwards=False):
    """
    Generate a rectangular RGB buffer filled with the specified spectrum

    hue: the central hue
    spread: the total spread in radians (max. 2 * pi)
    width: the required width of the rectangle in pixels
    height: the required height of the rectangle in pixels
    backwards: whether to go clockwise from red to yellow instead of antilcockwise
    """
    row = bytearray()
    if backwards:
        start_hue_angle = hue.angle - spread / 2
        delta_hue_angle = spread / width
    else:
        start_hue_angle = hue.angle + spread / 2
        delta_hue_angle = -spread / width
    for i in range(width):
        hue = paint.Hue.from_angle(start_hue_angle + delta_hue_angle * i)
        for j in range(3):
            row.append(hue.rgb[j] >> 8)
    buf = row * height
    return buffer(buf)

def gdk_color_to_rgb(colour):
    return paint.RGB(*gtkpwx.gdk_color_to_rgb(colour))

def get_rgb(colour):
    if isinstance(colour, Gdk.Color):
        return gdk_color_to_rgb(colour)
    elif isinstance(colour, paint.Colour) or isinstance(colour, paint.HCV):
        return colour.rgb
    elif isinstance(colour, paint.RGB):
        return colour
    else:
        return paint.RGB(*colour)

def generate_graded_rgb_buf(start_colour, end_colour, width, height):
    # TODO: deprecate this function in favour of the one in pixbuf
    """
    Generate a rectangular RGB buffer whose RGB values change linearly

    start_colour: the start colour
    end_colour: the end colour
    width: the required width of the rectangle in pixels
    height: the required height of the rectangle in pixels
    """
    start_rgb = get_rgb(start_colour)
    end_rgb = get_rgb(end_colour)
    # Use Fraction() to eliminate rounding errors causing chr() range problems
    delta_rgb = [fractions.Fraction(end_rgb[i] - start_rgb[i], width) for i in range(3)]
    row = bytearray()
    for i in range(width):
        for j in range(3):
            row.append(chr((start_rgb[j] + int(delta_rgb[j] * i)) >> 8))
    buf = row * height
    return buffer(buf)

def draw_line(cairo_ctxt, x0, y0, x1, y1):
    cairo_ctxt.move_to(x0, y0)
    cairo_ctxt.line_to(x1, y1)
    cairo_ctxt.stroke()

def draw_polygon(cairo_ctxt, polygon, filled=True):
    cairo_ctxt.move_to(*polygon[0])
    for index in range(1, len(polygon)):
        cairo_ctxt.line_to(*polygon[index])
    cairo_ctxt.close_path()
    if filled:
        cairo_ctxt.fill()
    else:
        cairo_ctxt.stroke()

def draw_circle(cairo_ctxt, cx, cy, radius, filled=False):
    cairo_ctxt.arc(cx, cy, radius, 0.0, 2 * math.pi)
    if filled:
        cairo_ctxt.fill()
    else:
        cairo_ctxt.stroke()

class GenericAttrDisplay(Gtk.DrawingArea):
    LABEL = None

    def __init__(self, colour=None, size=(100, 15)):
        Gtk.DrawingArea.__init__(self)
        self.set_size_request(size[0], size[1])
        self.colour = colour
        self.fg_colour = gtkpwx.best_foreground_rgb(colour)
        self.indicator_val = 0.5
        self._set_colour(colour)
        self.connect('draw', self.expose_cb)
        self.show()
    @staticmethod
    def indicator_top(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, 5), (-5, 0), (5, 0))]
    @staticmethod
    def indicator_bottom(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, -5), (-5, 0), (5, 0))]
    def draw_indicators(self, cairo_ctxt):
        if self.indicator_val is None:
            return
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        indicator_x = int(width * self.indicator_val)
        cairo_ctxt.set_source_rgb(*self.fg_colour)
        draw_polygon(cairo_ctxt, self.indicator_top(indicator_x, 0), True)
        draw_polygon(cairo_ctxt, self.indicator_bottom(indicator_x, height - 1), True)
    def draw_label(self, cairo_ctxt):
        if self.LABEL is None:
            return
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        cairo_ctxt.set_font_size(15)
        tw, th = cairo_ctxt.text_extents(self.LABEL)[2:4]
        x = (width - tw + 0.5) / 2
        y = (height + th - 0.5) / 2
        cairo_ctxt.move_to(x, y)
        cairo_ctxt.set_source_rgb(*self.fg_colour)
        cairo_ctxt.show_text(self.LABEL)
    def expose_cb(self, _widget, _cr):
        pass
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes.
        Such as the location of the indicators.
        """
        pass
    def set_colour(self, colour):
        self.colour = colour
        self._set_colour(colour)
        self.queue_draw()

class HueDisplay(GenericAttrDisplay):
    LABEL = _('Hue')

    def expose_cb(self, widget, cairo_ctxt):
        if self.colour is None and self.target_val is None:
            cairo_ctxt.set_source_rgb(0, 0, 0)
            cairo_ctxt.paint()
            return
        #
        if self.colour.hue.is_grey():
            cairo_ctxt.set_source_rgb(*self.colour.hue_rgb)
            self.draw_label(cairo_ctxt)
            return
        #
        backwards = options.get('colour_wheel', 'red_to_yellow_clockwise')
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        spread = 2 * math.pi
        if backwards:
            start_hue_angle = self.colour.hue.angle - spread / 2
            delta_hue_angle = spread / width
        else:
            start_hue_angle = self.colour.hue.angle + spread / 2
            delta_hue_angle = -spread / width
        linear_gradient = cairo.LinearGradient(0, 0, width, height)
        for i in range(width):
            hue = paint.Hue.from_angle(start_hue_angle + delta_hue_angle * i)
            linear_gradient.add_color_stop_rgb(float(i) / width, *hue.rgb_converted_to(rgbh.RGBPN))
        cairo_ctxt.rectangle(0, 0, width, height)
        cairo_ctxt.set_source(linear_gradient)
        cairo_ctxt.fill()

        self.draw_indicators(cairo_ctxt)
        self.draw_label(cairo_ctxt)
    def _set_colour(self, colour):
        self.fg_colour = gtkpwx.best_foreground_rgb(colour.hue_rgb)

class ValueDisplay(GenericAttrDisplay):
    LABEL = _('Value')
    def __init__(self, colour=None, size=(100, 15)):
        self.start_colour = paint.BLACK
        self.end_colour = paint.WHITE
        GenericAttrDisplay.__init__(self, colour=colour, size=size)
    def expose_cb(self, widget, cairo_ctxt):
        if self.colour is None:
            cairo_ctxt.set_source_rgb(0, 0, 0)
            cairo_ctxt.paint()
            return
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        linear_gradient = cairo.LinearGradient(0, 0, width, height)
        linear_gradient.add_color_stop_rgb(0.0, *self.start_colour)
        linear_gradient.add_color_stop_rgb(1.0, *self.end_colour)
        cairo_ctxt.rectangle(0, 0, width, height)
        cairo_ctxt.set_source(linear_gradient)
        cairo_ctxt.fill()

        self.draw_indicators(cairo_ctxt)
        self.draw_label(cairo_ctxt)
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.fg_colour = gtkpwx.best_foreground_rgb(colour)
        self.indicator_val = colour.value

class ChromaDisplay(ValueDisplay):
    LABEL = _('Chroma')
    def __init__(self, colour=None, size=(100, 15)):
        ValueDisplay.__init__(self, colour=colour, size=size)
        if colour is not None:
            self._set_colour(colour)
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.start_colour = self.colour.hcvw.chroma_side()
        self.end_colour = colour.hue_rgb
        self.fg_colour = self.start_colour
        self.indicator_val = colour.chroma

class WarmthDisplay(ValueDisplay):
    LABEL = _('Warmth')
    def __init__(self, colour=None, size=(100, 15)):
        GenericAttrDisplay.__init__(self, colour=colour, size=size)
        self.start_colour = paint.CYAN
        self.end_colour = paint.RED
    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.fg_colour = gtkpwx.best_foreground_rgb(colour.warmth_rgb())
        self.indicator_val = (1 + colour.warmth) / 2

class HCVDisplay(Gtk.VBox):
    def __init__(self, colour=paint.WHITE, size=(256, 120), stype = Gtk.ShadowType.ETCHED_IN):
        Gtk.VBox.__init__(self)
        #
        w, h = size
        self.hue = HueDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.hue, stype), expand=False, fill=True, padding=0)
        self.value = ValueDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.value, stype), expand=False, fill=True, padding=0)
        self.chroma = ChromaDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.chroma, stype), expand=False, fill=True, padding=0)
        self.show()
    def set_colour(self, new_colour):
        self.chroma.set_colour(new_colour)
        self.hue.set_colour(new_colour)
        self.value.set_colour(new_colour)

class HCVWDisplay(HCVDisplay):
    def __init__(self, colour=paint.WHITE, size=(256, 120), stype = Gtk.ShadowType.ETCHED_IN):
        HCVDisplay.__init__(self, colour=colour, size=size, stype=stype)
        w, h = size
        self.warmth = WarmthDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.warmth, stype), expand=False, fill=True, padding=0)
        self.show()
    def set_colour(self, new_colour):
        HCVDisplay.set_colour(self, new_colour)
        self.warmth.set_colour(new_colour)

class HueWheelNotebook(Gtk.Notebook):
    def __init__(self):
        Gtk.Notebook.__init__(self)
        self.hue_chroma_wheel = HueChromaWheel(nrings=5)
        self.hue_value_wheel = HueValueWheel()
        self.append_page(self.hue_chroma_wheel, Gtk.Label(_('Hue/Chroma Wheel')))
        self.append_page(self.hue_value_wheel, Gtk.Label(_('Hue/Value Wheel')))
    def add_colour(self, new_colour):
        self.hue_chroma_wheel.add_colour(new_colour)
        self.hue_value_wheel.add_colour(new_colour)
    def del_colour(self, colour):
        self.hue_chroma_wheel.del_colour(colour)
        self.hue_value_wheel.del_colour(colour)

class ColourWheel(Gtk.DrawingArea, actions.CAGandUIManager):
    UI_DESCR = '''
        <ui>
            <popup name='colour_wheel_I_popup'>
                <menuitem action='colour_info'/>
            </popup>
            <popup name='colour_wheel_AI_popup'>
                <menuitem action='add_colour'/>
                <menuitem action='colour_info'/>
            </popup>
        </ui>
        '''
    AC_HAVE_POPUP_COLOUR, _DUMMY = actions.ActionCondns.new_flags_and_mask(1)
    def __init__(self, nrings=9, popup='/colour_wheel_I_popup'):
        Gtk.DrawingArea.__init__(self)
        actions.CAGandUIManager.__init__(self, popup=popup)
        self.__popup_colour = None
        self.BLACK = get_colour([0, 0, 0])
        self.set_size_request(400, 400)
        self.scale = 1.0
        self.zoom = 1.0
        self.one = 100 * self.scale
        self.size = 3
        self.scaled_size = self.size * self.scale
        self.centre = gtkpwx.XY(0, 0)
        self.offset = gtkpwx.XY(0, 0)
        self.__last_xy = gtkpwx.XY(0, 0)
        self.tube_colours = {}
        self.mixed_colours = {}
        self.nrings = nrings
        self.connect("draw", self.expose_cb)
        self.set_has_tooltip(True)
        self.connect('query-tooltip', self.query_tooltip_cb)
        self.add_events(Gdk.EventMask.SCROLL_MASK|Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('scroll-event', self.scroll_event_cb)
        self.__press_cb_id = self.connect('button_press_event', self._button_press_cb)
        self.__cb_ids = []
        self.__cb_ids.append(self.connect('button_release_event', self._button_release_cb))
        self.__cb_ids.append(self.connect('motion_notify_event', self._motion_notify_cb))
        self.__cb_ids.append(self.connect('leave_notify_event', self._leave_notify_cb))
        for cb_id in self.__cb_ids:
            self.handler_block(cb_id)
        self.show()
    @property
    def popup_colour(self):
        return self.__popup_colour
    def populate_action_groups(self):
        self.action_groups[self.AC_HAVE_POPUP_COLOUR].add_actions([
            ('colour_info', Gtk.STOCK_INFO, None, None,
             _('Detailed information for this colour.'),
            ),
            ('add_colour', Gtk.STOCK_ADD, None, None,
             _('Add this colour to the mixer.'),
            ),
        ])
        self.__ci_acbid = self.action_groups.connect_activate('colour_info', self._show_colour_details_acb)
        self.__ac_acbid = None
    def _show_colour_details_acb(self, _action):
        TubeColourInformationDialogue(self.__popup_colour).show()
    def do_popup_preliminaries(self, event):
        colour, rng = self.get_colour_nearest_to_xy(event.x, event.y)
        if colour is not None and rng <= self.scaled_size:
            self.__popup_colour = colour
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_HAVE_POPUP_COLOUR, self.AC_HAVE_POPUP_COLOUR))
        else:
            self.__popup_colour = None
            self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_HAVE_POPUP_COLOUR))
    def set_colour_info_acb(self, callback):
        self.action_groups.disconnect_action('colour_info', self.__ci_acbid)
        self.__ci_acbid = self.action_groups.connect_activate('colour_info', callback, self)
    def set_add_colour_acb(self, callback):
        if self.__ac_acbid is not None:
            self.action_groups.disconnect_action('add_colour', self.__ac_acbid)
        self.__ac_acbid = self.action_groups.connect_activate('add_colour', callback, self)
    def polar_to_cartesian(self, radius, angle):
        if options.get('colour_wheel', 'red_to_yellow_clockwise'):
            x = -radius * math.cos(angle)
        else:
            x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        return (int(self.centre.x + x), int(self.centre.y - y))
    def get_colour_nearest_to_xy(self, x, y):
        smallest = 0xFF
        nearest = None
        for colour_set in [self.tube_colours.values(), self.mixed_colours.values()]:
            for colour in colour_set:
                rng = colour.range_from(x, y)
                if rng < smallest:
                    smallest = rng
                    nearest = colour.colour
        return (nearest, smallest)
    def get_colour_at_xy(self, x, y):
        colour, rng = self.get_colour_nearest_to_xy(x, y)
        return colour if rng < self.scaled_size else None
    def query_tooltip_cb(self, widget, x, y, keyboard_mode, tooltip):
        # TODO: move location of tootip as mouse moves
        colour, rng = self.get_colour_nearest_to_xy(x, y)
        if colour is not None and rng <= self.scaled_size:
            tooltip.set_text(colour.name)
            return True
        else:
            tooltip.set_text("")
            return False
    def scroll_event_cb(self, _widget, event):
        # TODO: investigate strange zoom behaviour in colour wheel
        if event.device.get_source() == Gdk.InputSource.MOUSE:
            new_zoom = self.zoom + 0.025 * (-1 if event.direction == Gdk.ScrollDirection.UP else 1)
            if new_zoom > 1.0 and new_zoom < 5.0:
                self.zoom = new_zoom
                self.queue_draw()
            return True
        return False
    def add_colour(self, new_colour):
        if isinstance(new_colour, paint.MixedColour):
            self.mixed_colours[new_colour] = self.ColourCircle(self, new_colour)
        else:
            self.tube_colours[new_colour] = self.ColourSquare(self, new_colour)
        # The data has changed so do a redraw
        self.queue_draw()
    def del_colour(self, colour):
        if isinstance(colour, paint.MixedColour):
            self.mixed_colours.pop(colour)
        else:
            self.tube_colours.pop(colour)
        # The data has changed so do a redraw
        self.queue_draw()
    def new_colour(self, rgb):
        colour = Gdk.Color(*rgb)
        return colour
    def expose_cb(self, widget, cairo_ctxt):
        #
        spacer = 10
        scaledmax = 110.0
        #
        bg_colour = (paint.RGB_WHITE / 2).converted_to(rgbh.RGBPN)
        cairo_ctxt.set_source_rgb(*bg_colour)
        cairo_ctxt.paint()
        #
        dw = widget.get_allocated_width()
        dh = widget.get_allocated_height()
        self.centre = gtkpwx.XY(dw / 2, dh / 2) + self.offset
        #
        # calculate a scale factor to use for drawing the graph based
        # on the minimum available width or height
        mindim = min(self.centre.x, dh / 2)
        self.scale = mindim / scaledmax
        self.one = self.scale * 100
        self.scaled_size = self.size * self.scale
        #
        # Draw the graticule
        ring_colour = (paint.RGB_WHITE * 3 / 4).converted_to(rgbh.RGBPN)
        cairo_ctxt.set_source_rgb(*ring_colour)
        for radius in [100 * (i + 1) * self.scale / self.nrings for i in range(self.nrings)]:
            draw_circle(cairo_ctxt, self.centre.x, self.centre.y, int(round(radius * self.zoom)))
        #
        cairo_ctxt.set_line_width(2)
        for angle in [utils.PI_60 * i for i in range(6)]:
            hue = paint.Hue.from_angle(angle)
            cairo_ctxt.set_source_rgb(*hue.rgb_converted_to(rgbh.RGBPN))
            cairo_ctxt.move_to(self.centre.x, self.centre.y)
            cairo_ctxt.line_to(*self.polar_to_cartesian(self.one * self.zoom, angle))
            cairo_ctxt.stroke()
        for tube in self.tube_colours.values():
            tube.draw(cairo_ctxt)
        for mix in self.mixed_colours.values():
            mix.draw(cairo_ctxt)
        return True
    # Allow graticule to be moved using mouse (left button depressed)
    # Careful not to override CAGandUIManager method
    def _button_press_cb(self, widget, event):
        if event.button == 1:
            self.__last_xy = gtkpwx.XY(int(event.x), int(event.y))
            for cb_id in self.__cb_ids:
                widget.handler_unblock(cb_id)
            return True
        return actions.CAGandUIManager._button_press_cb(self, widget, event)
    def _motion_notify_cb(self, widget, event):
        this_xy = gtkpwx.XY(int(event.x), int(event.y))
        delta_xy = this_xy - self.__last_xy
        self.__last_xy = this_xy
        # TODO: limit offset values
        self.offset += delta_xy
        widget.queue_draw()
        return True
    def _button_release_cb(self, widget, event):
        if event.button != 1:
            return False
        for cb_id in self.__cb_ids:
            widget.handler_block(cb_id)
        return True
    def _leave_notify_cb(self, widget, event):
        for cb_id in self.__cb_ids:
            widget.handler_block(cb_id)
        return False
    class ColourShape(object):
        def __init__(self, parent, colour):
            self.parent = parent
            self.colour = colour
            self.x = 0
            self.y = 0
            self.pen_width = 2
            self.predraw_setup()
        def predraw_setup(self):
            """
            Set up colour values ready for drawing
            """
            self.colour_angle = self.colour.hue.angle if not self.colour.hue.is_grey() else utils.Angle(math.pi / 2)
            self.fg_colour = self.colour.rgb #self.parent.new_colour(self.colour.rgb)
            self.value_colour = paint.BLACK #self.parent.new_colour(paint.BLACK)
            self.chroma_colour = self.colour.hcvw.chroma_side() #self.parent.new_colour(self.colour.hcvw.chroma_side())
            self.choose_radius_attribute()
        def range_from(self, x, y):
            dx = x - self.x
            dy = y - self.y
            return math.sqrt(dx * dx + dy * dy)
    class ColourSquare(ColourShape):
        polypoints = ((-1, 1), (-1, -1), (1, -1), (1, 1))
        def draw(self, cairo_ctxt):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            square = tuple(tuple(pp[i] * self.parent.scaled_size for i in range(2)) for pp in self.polypoints)
            square_pts = [tuple((int(self.x + pt[0]), int(self.y +  pt[1]))) for pt in square]
            # draw the middle
            cairo_ctxt.set_source_rgb(*self.fg_colour.converted_to(rgbh.RGBPN))
            draw_polygon(cairo_ctxt, square_pts, filled=True)
            cairo_ctxt.set_source_rgb(*self.chroma_colour)
            draw_polygon(cairo_ctxt, square_pts, filled=False)
    class ColourDiamond(ColourSquare):
        polypoints = ((1.5, 0), (0, -1.5), (-1.5, 0), (0, 1.5))
    class ColourCircle(ColourShape):
        def draw(self, cairo_ctxt):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            cairo_ctxt.set_source_rgb(*self.fg_colour.converted_to(rgbh.RGBPN))
            draw_circle(cairo_ctxt, self.x, self.y, radius=self.parent.scaled_size, filled=True)
            cairo_ctxt.set_source_rgb(*self.chroma_colour)
            draw_circle(cairo_ctxt, self.x, self.y, radius=self.parent.scaled_size, filled=False)

class HueChromaWheel(ColourWheel):
    class ColourSquare(ColourWheel.ColourSquare):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma
    class ColourCircle(ColourWheel.ColourCircle):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma
    class ColourDiamond(ColourWheel.ColourDiamond):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma

class HueValueWheel(ColourWheel):
    class ColourSquare(ColourWheel.ColourSquare):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value
    class ColourCircle(ColourWheel.ColourCircle):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value
    class ColourDiamond(ColourWheel.ColourDiamond):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value

class ColourListStore(tlview.NamedListStore):
    ROW = collections.namedtuple('ROW', ['colour'])
    TYPES = ROW(colour=object)
    def append_colour(self, colour):
        self.append(self.ROW(colour))
    def remove_colour(self, colour):
        model_iter = self.find_named(lambda x: x.colour == colour)
        if model_iter is None:
            raise LookupError()
        # return the iter in case the client is interested
        self.emit('colour-removed', colour)
        return self.remove(model_iter)
    def remove_colours(self, colours):
        for colour in colours:
            self.remove_colour(colour)
    def get_colours(self):
        return [row.colour for row in self.named()]
    def get_colour_with_name(self, colour_name):
        """
        Return the colour with the specified name or None if not present
        """
        for row in self.named():
            if row.colour.name == colour_name:
                return row.colour
        return None
GObject.signal_new('colour-removed', ColourListStore, GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,))

def paint_cell_data_func(column, cell, model, model_iter, attribute):
    colour = model.get_value_named(model_iter, 'colour')
    if attribute == 'name':
        cell.set_property('text', colour.name)
        cell.set_property('background-gdk', Gdk.Color(*colour.rgb))
        cell.set_property('foreground-gdk', gtkpwx.best_foreground(colour.rgb))
    elif attribute == 'value':
        cell.set_property('text', str(float(round(colour.value, 2))))
        cell.set_property('background-gdk', Gdk.Color(*colour.value_rgb()))
        cell.set_property('foreground-gdk', gtkpwx.best_foreground(colour.value_rgb()))
    elif attribute == 'hue':
        cell.set_property('background-gdk', Gdk.Color(*colour.hue_rgb))
    elif attribute == 'warmth':
        cell.set_property('background-gdk', Gdk.Color(*colour.warmth_rgb()))
    elif attribute == 'permanence':
        cell.set_property('text', str(colour.permanence))
    elif attribute == 'transparency':
        cell.set_property('text', str(colour.transparency))

TNS = collections.namedtuple('TNS', ['title', 'attr', 'properties', 'sort_key_function'])

def colour_attribute_column_spec(tns):
    return tlview.ColumnSpec(
        title=tns.title,
        properties=tns.properties,
        sort_key_function=tns.sort_key_function,
        cells=[
            tlview.CellSpec(
                cell_renderer_spec=tlview.CellRendererSpec(
                    cell_renderer=Gtk.CellRendererText,
                    expand=None,
                    properties=None,
                    start=False
                ),
                cell_data_function_spec=tlview.CellDataFunctionSpec(
                    function=paint_cell_data_func,
                    user_data=tns.attr
                ),
                attributes={}
            ),
        ],
    )

COLOUR_ATTRS = [
    TNS(_('Colour Name'), 'name', {'resizable' : True, 'expand' : True}, lambda row: row.colour.name),
    TNS(_('Value'), 'value', {}, lambda row: row.colour.value),
    TNS(_('Hue'), 'hue', {}, lambda row: row.colour.hue),
    TNS(_('Warmth'), 'warmth', {}, lambda row: row.colour.warmth),
    TNS(_('T.'), 'transparency', {}, lambda row: row.colour.transparency),
    TNS(_('P.'), 'permanence', {}, lambda row: row.colour.permanence),
]

def colour_attribute_column_specs(model):
    """
    Generate the column specitications for colour attributes
    """
    return [colour_attribute_column_spec(tns) for tns in COLOUR_ATTRS]

def generate_colour_list_spec(model):
    """
    Generate the SPECIFICATION for a paint colour list
    """
    return tlview.ViewSpec(
        properties={},
        selection_mode=Gtk.SelectionMode.MULTIPLE,
        columns=colour_attribute_column_specs(model)
    )

class ColourListView(tlview.View, actions.CAGandUIManager):
    MODEL = ColourListStore
    SPECIFICATION = generate_colour_list_spec(ColourListStore)
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='remove_selected_colours'/>
        </popup>
    </ui>
    '''
    def __init__(self, *args, **kwargs):
        tlview.View.__init__(self, *args, **kwargs)
        actions.CAGandUIManager.__init__(self, selection=self.get_selection(), popup='/colour_list_popup')
    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[actions.AC_SELN_MADE].add_actions(
            [
                ('remove_selected_colours', Gtk.STOCK_REMOVE, None, None,
                 _('Remove the selected colours from the list.'), self._remove_selection_cb),
            ]
        )
    def _remove_selection_cb(self, _action):
        """
        Delete the currently selected colours
        """
        colours = self.get_selected_colours()
        if len(colours) == 0:
            return
        msg = _("The following colours are about to be deleted:\n")
        for colour in colours:
            msg += "\t{0}\n".format(colour.name)
        msg += _("and will not be recoverable. OK?")
        if gtkpwx.ask_user_to_confirm(msg):
            self.model.remove_colours(colours)
    def get_selected_colours(self):
        """
        Return the currently selected colours as a list.
        """
        return [row.colour for row in self.MODEL.get_selected_rows(self.get_selection())]

class TubeColourInformationDialogue(Gtk.Dialog):
    """
    A dialog to display the detailed information for a paint colour
    """
    def __init__(self, colour, parent=None):
        Gtk.Dialog.__init__(self, title=_('Paint Colour: {}').format(colour.name), parent=parent)
        last_size = recollect.get("paint_colour_information", "last_size")
        if last_size:
            self.set_default_size(*eval(last_size))
        vbox = self.get_content_area()
        vbox.pack_start(gtkpwx.ColouredLabel(colour.name, colour), expand=False, fill=True, padding=0)
        if isinstance(colour, paint.TubeColour):
            vbox.pack_start(gtkpwx.ColouredLabel(colour.series.series_id.name, colour), expand=False, fill=True, padding=0)
            vbox.pack_start(gtkpwx.ColouredLabel(colour.series.series_id.maker, colour), expand=False, fill=True, padding=0)
        vbox.pack_start(HCVDisplay(colour=colour), expand=False, fill=True, padding=0)
        if isinstance(colour, paint.TubeColour):
            vbox.pack_start(Gtk.Label(colour.transparency.description()), expand=False, fill=True, padding=0)
            vbox.pack_start(Gtk.Label(colour.permanence.description()), expand=False, fill=True, padding=0)
        self.connect("configure-event", self._configure_event_cb)
        vbox.show_all()
    def _configure_event_cb(self, widget, allocation):
        recollect.set("paint_colour_information", "last_size", "({0.width}, {0.height})".format(allocation))

if __name__ == '__main__':
    doctest.testmod()
