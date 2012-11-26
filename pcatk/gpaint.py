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

import gtk
import gobject

from pcatk import options
from pcatk import gtkpwx
from pcatk import paint

if __name__ == '__main__':
    _ = lambda x: x
    import doctest

class MappedFloatChoice(gtkpwx.Choice):
    MFDC = None
    def __init__(self):
        choices = ['{0}\t- {1}'.format(item[0], item[1]) for item in self.MFDC.MAP]
        gtkpwx.Choice.__init__(self, choices=choices)
    # END_DEF: __init__

    def get_selection(self):
        return self.MFDC(self.MFDC.MAP[gtkpwx.Choice.get_selection(self)].abbrev)
    # END_DEF: get_selection

    def set_selection(self, mapped_float):
        abbrev = str(mapped_float)
        for i, rating in enumerate(self.MFDC.MAP):
            if abbrev == rating.abbrev:
                gtkpwx.Choice.set_selection(self, i)
                return
        raise paint.MappedFloat.BadValue()
    # END_DEF: set_selection
# END_CLASS: MappedFloatChoice

class TransparencyChoice(MappedFloatChoice):
    MFDC = paint.Transparency
# END_CLASS: TransparencyChoice

class PermanenceChoice(MappedFloatChoice):
    MFDC = paint.Permanence
# END_CLASS: PermanenceChoice

class ColourSampleArea(gtk.DrawingArea, gtkpwx.CAGandUIManager):
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
    AC_SAMPLES_PASTED, AC_MASK = gtkpwx.ActionCondns.new_flags_and_mask(1)
    def __init__(self, single_sample=False, default_bg=None):
        gtk.DrawingArea.__init__(self)

        self.set_size_request(200, 200)
        self._ptr_x = self._ptr_y = 100
        self._sample_images = []
        self._single_sample = single_sample
        self.default_bg_colour = self.bg_colour = self.new_colour(paint.HCVW.WHITE) if default_bg is None else self.new_colour(default_bg)

        self.add_events(gtk.gdk.POINTER_MOTION_MASK|gtk.gdk.BUTTON_PRESS_MASK)
        self.connect('expose-event', self.expose_cb)
        self.connect('motion_notify_event', self._motion_notify_cb)

        gtkpwx.CAGandUIManager.__init__(self, popup='/colour_sample_popup')
    # END_DEF: __init__()

    def populate_action_groups(self):
        self.action_groups[gtkpwx.AC_DONT_CARE].add_actions(
            [
                ('paste_sample_image', gtk.STOCK_PASTE, None, None,
                 _('Paste an image from clipboard at this position.'), self._paste_fm_clipboard_cb),
            ])
        self.action_groups[self.AC_SAMPLES_PASTED].add_actions(
            [
                ('remove_sample_images', gtk.STOCK_REMOVE, None, None,
                 _('Remove all sample images from from the sample area.'), self._remove_sample_images_cb),
            ])
    # END_DEF: populate_action_groups

    def get_masked_condns(self):
        if len(self._sample_images) > 0:
            return gtkpwx.MaskedConds(self.AC_SAMPLES_PASTED, self.AC_MASK)
        else:
            return gtkpwx.MaskedConds(0, self.AC_MASK)
    # END_DEF: get_masked_condns

    def _motion_notify_cb(self, widget, event):
        if event.type == gtk.gdk.MOTION_NOTIFY:
            self._ptr_x = event.x
            self._ptr_y = event.y
            return True
        return False
    # END_DEF: _motion_notify_cb

    def _remove_sample_images_cb(self, action):
        """
        Remove all samples.
        """
        self.erase_samples()
    # END_DEF: _remove_sample_images_cb

    def _paste_fm_clipboard_cb(self, _action):
        """
        Paste from the clipboard
        """
        cbd = gtk.clipboard_get()
        cbd.request_image(self._image_from_clipboard_cb, (self._ptr_x, self._ptr_y))
    # END_DEF: _remove_selection_cb

    def _image_from_clipboard_cb(self, cbd, img, posn):
        if img is None:
            dlg = gtk.MessageDialog(
                parent=self.get_toplevel(),
                flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                buttons=gtk.BUTTONS_OK,
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
            self.action_groups.update_condns(gtkpwx.MaskedConds(self.AC_SAMPLES_PASTED, self.AC_MASK))
            self.emit('samples-changed', len(self._sample_images))
    # END_DEF: _image_from_clipboard_cb

    def erase_samples(self):
        """
        Erase all samples from the drawing area
        """
        self._sample_images = []
        self.queue_draw()
        self.action_groups.update_condns(gtkpwx.MaskedConds(0, self.AC_MASK))
        self.emit('samples-changed', len(self._sample_images))
    # END_DEF: erase_samples

    def get_samples(self):
        """
        Return a list containing all samples from the drawing area
        """
        return [sample[2] for sample in self._sample_images]
    # END_DEF: get_samples

    def new_colour(self, arg):
        if isinstance(arg, paint.Colour):
            colour = gtk.gdk.Color(*arg.rgb)
        else:
            colour = gtk.gdk.Color(*arg)
        return self.get_colormap().alloc_color(colour)
    # END_DEF: new_colour

    def set_bg_colour(self, colour):
        """
        Set the drawing area to the specified colour
        """
        self.bg_colour = self.new_colour(colour)
        self.queue_draw()
    # END_DEF: set_bg_colour

    def expose_cb(self, _widget, _event):
        """
        Repaint the drawing area
        """
        self.gc = self.window.new_gc()
        self.gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        self.gc.set_background(self.bg_colour)
        self.window.set_background(self.bg_colour)
        self.window.clear()
        for sample in self._sample_images:
            self.window.draw_pixbuf(self.gc, sample[2], 0, 0, sample[0], sample[1])
        return True
    # END_DEF: expose_cb
gobject.signal_new('samples-changed', ColourSampleArea, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT,))
# END_CLASS: ColourSampleArea

def generate_spectral_rgb_buf(hue, spread, width, height, backwards=False):
    # TODO: deprecate this function in favour of the one in pixbuf
    """
    Generate a rectangular RGB buffer filled with the specified spectrum

    hue: the central hue in radians from red
    spread: the total spread in radians (max. 2 * pi)
    width: the required width of the rectangle in pixels
    height: the required height of the rectangle in pixels
    backwards: whether to go clockwise from red to yellow instead of antilcockwise
    """
    row = bytearray()
    if backwards:
        start_hue = hue - spread / 2
        delta_hue = spread / width
    else:
        start_hue = hue + spread / 2
        delta_hue = -spread / width
    ONE = (1 << 8) - 1
    fraction_to_byte = lambda frac : chr(ONE * frac.numerator / frac.denominator)
    for i in range(width):
        hue = start_hue + delta_hue * i
        rgb = hue.get_rgb(hue).mapped(fraction_to_byte)
        row.extend(rgb)
    buf = row * height
    return buffer(buf)
# END_DEF: generate_spectral_rgb_buf

def generate_graded_rgb_buf(start_colour, end_colour, width, height):
    # TODO: deprecate this function in favour of the one in pixbuf
    """
    Generate a rectangular RGB buffer whose RGB values change linearly

    start_colour: the start colour
    end_colour: the end colour
    width: the required width of the rectangle in pixels
    height: the required height of the rectangle in pixels
    """
    def get_rgb(colour):
        if isinstance(colour, gtk.gdk.Color):
            return gdk_color_to_rgb(colour)
        elif isinstance(colour, paint.Colour):
            return colour.rgb
        else:
            return colour
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
# END_DEF: generate_graded_rgb_buf

class GenericAttrDisplay(gtk.DrawingArea):
    LABEL = None

    def __init__(self, colour=None, size=(100, 15)):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(size[0], size[1])
        self.colour = colour
        self.fg_colour = gtkpwx.best_foreground(colour)
        self.indicator_val = 0.5
        self._set_colour(colour)
        self.connect('expose-event', self.expose_cb)
        self.show()
    # END_DEF: __init__

    @staticmethod
    def indicator_top(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, 5), (-5, 0), (5, 0))]
    # END_DEF: indicator_top

    @staticmethod
    def indicator_bottom(x, y):
        return [(ind[0] + x, ind[1] + y) for ind in ((0, -5), (-5, 0), (5, 0))]
    # END_DEF: indicator_bottom

    def new_colour(self, arg):
        if isinstance(arg, paint.Colour):
            colour = gtk.gdk.Color(*arg.rgb)
        else:
            colour = gtk.gdk.Color(*arg)
        return self.get_colormap().alloc_color(colour)
    # END_DEF: new_colour

    def draw_indicators(self, gc):
        w, h = self.window.get_size()
        indicator_x = int(w * self.indicator_val)
        gc.set_foreground(self.fg_colour)
        gc.set_background(self.fg_colour)
        # TODO: fix bottom indicator
        self.window.draw_polygon(gc, True, self.indicator_top(indicator_x, 0))
        self.window.draw_polygon(gc, True, self.indicator_bottom(indicator_x, h - 1))
    # END_DEF: draw_indicators

    def draw_label(self, gc):
        if self.LABEL is None:
            return
        w, h = self.window.get_size()
        layout = self.create_pango_layout(self.LABEL)
        tw, th = layout.get_pixel_size()
        x, y = ((w - tw) / 2, (h - th) / 2)
        gc.set_foreground(self.fg_colour)
        self.window.draw_layout(gc, x, y, layout, self.fg_colour)
    # END_DEF: draw_label

    def expose_cb(self, _widget, _event):
        pass
    # END_DEF: expose_cb

    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes.
        Such as the location of the indicators.
        """
        pass
    # END_DEF: _set_colour

    def set_colour(self, colour):
        self.colour = colour
        self._set_colour(colour)
        self.queue_draw()
    # END_DEF: set_colour
# END_CLASS: GenericAttrDisplay

class HueDisplay(GenericAttrDisplay):
    LABEL = _('Hue')

    def expose_cb(self, _widget, _event):
        if self.colour is None:
            self.window.set_background(gtk.gdk.Color(0, 0, 0))
            return
        gc = self.window.new_gc()
        gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])

        if self.colour.hue is None:
            self.window.set_background(self.new_colour(self.colour.hue_rgb))
            self.draw_label(gc)
            return

        backwards = options.get('colour_wheel', 'red_to_yellow_clockwise')
        w, h = self.window.get_size()
        spectral_buf = generate_spectral_rgb_buf(self.colour.hue, 2 * math.pi, w, h, backwards)
        self.window.draw_rgb_image(gc, x=0, y=0, width=w, height=h,
            dith=gtk.gdk.RGB_DITHER_NONE,
            rgb_buf=spectral_buf)

        self.draw_indicators(gc)
        self.draw_label(gc)
    # END_DEF: expose_cb

    def _set_colour(self, colour):
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(colour.hue_rgb))
    # END_DEF: _set_colour
# END_CLASS: HueDisplay

class ValueDisplay(GenericAttrDisplay):
    LABEL = _('Value')

    def __init__(self, colour=None, size=(100, 15)):
        GenericAttrDisplay.__init__(self, colour=colour, size=size)
        self.start_colour = paint.BLACK
        self.end_colour = paint.WHITE
    # END_DEF: __init__

    def expose_cb(self, _widget, _event):
        if self.colour is None:
            self.window.set_background(gtk.gdk.Color(0, 0, 0))
            return
        gc = self.window.new_gc()
        gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])
        w, h = self.window.get_size()

        graded_buf = generate_graded_rgb_buf(self.start_colour, self.end_colour, w, h)
        self.window.draw_rgb_image(gc, x=0, y=0, width=w, height=h,
            dith=gtk.gdk.RGB_DITHER_NONE,
            rgb_buf=graded_buf)

        self.draw_indicators(gc)
        self.draw_label(gc)
    # END_DEF: expose_cb

    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(colour))
        self.indicator_val = colour.value
    # END_DEF: _set_colour
# END_CLASS: ValueDisplay

class ChromaDisplay(ValueDisplay):
    LABEL = _('Chroma')

    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.start_colour = self.colour.hcvw.chroma_side()
        self.end_colour = colour.hue_rgb
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(self.start_colour))
        self.indicator_val = colour.chroma
    # END_DEF: _set_colour
# END_CLASS: ChromaDisplay

class WarmthDisplay(ValueDisplay):
    LABEL = _('Warmth')

    def __init__(self, colour=None, size=(100, 15)):
        GenericAttrDisplay.__init__(self, colour=colour, size=size)
        self.start_colour = paint.CYAN
        self.end_colour = paint.RED
    # END_DEF: __init__

    def _set_colour(self, colour):
        """
        Set values that only change when the colour changes
        """
        self.fg_colour = self.get_colormap().alloc_color(gtkpwx.best_foreground(colour.warmth_rgb()))
        self.indicator_val = (1 + colour.warmth) / 2
    # END_DEF: _set_colour
# END_CLASS: WarmthDisplay

class HCVDisplay(gtk.VBox):
    def __init__(self, colour=paint.WHITE, size=(256, 120), stype = gtk.SHADOW_ETCHED_IN):
        gtk.VBox.__init__(self)

        w, h = size
        self.hue = HueDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.hue, stype), expand=False)
        self.value = ValueDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.value, stype), expand=False)
        self.chroma = ChromaDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.chroma, stype), expand=False)
        self.show()
    # END_DEF: __init__

    def set_colour(self, new_colour):
        self.chroma.set_colour(new_colour)
        self.hue.set_colour(new_colour)
        self.value.set_colour(new_colour)
    # END_DEF: _set_colour
# END_CLASS: HCVDisplay

class HCVWDisplay(HCVDisplay):
    def __init__(self, colour=paint.WHITE, size=(256, 120), stype = gtk.SHADOW_ETCHED_IN):
        HCVDisplay.__init__(self, colour=colour, size=size, stype=stype)
        w, h = size
        self.warmth = WarmthDisplay(colour=colour, size=(w, h / 4))
        self.pack_start(gtkpwx.wrap_in_frame(self.warmth, stype), expand=False)
        self.show()
    # END_DEF: __init__

    def set_colour(self, new_colour):
        HCVDisplay.set_colour(self, new_colour)
        self.warmth.set_colour(new_colour)
    # END_DEF: _set_colour
# END_CLASS: HCVWDisplay

class HueWheelNotebook(gtk.Notebook):
    def __init__(self):
        gtk.Notebook.__init__(self)
        self.hue_chroma_wheel = HueChromaWheel(nrings=5)
        self.hue_value_wheel = HueValueWheel()
        self.append_page(self.hue_chroma_wheel, gtk.Label(_('Hue/Chroma Wheel')))
        self.append_page(self.hue_value_wheel, gtk.Label(_('Hue/Value Wheel')))
    # END_DEF: __init__

    def add_colour(self, new_colour):
        self.hue_chroma_wheel.add_colour(new_colour)
        self.hue_value_wheel.add_colour(new_colour)
    # END_DEF: add_colour

    def del_colour(self, colour):
        self.hue_chroma_wheel.del_colour(colour)
        self.hue_value_wheel.del_colour(colour)
    # END_DEF: del_colour
# END_CLASS: HueWheelNotebook

class ColourWheel(gtk.DrawingArea):
    def __init__(self, nrings=9):
        gtk.DrawingArea.__init__(self)
        self.set_size_request(400, 400)
        self.scale = 1.0
        self.zoom = 1.0
        self.one = 100 * self.scale
        self.size = 3
        self.scaled_size = self.size * self.scale
        self.cx = 0.0
        self.cy = 0.0
        self.tube_colours = {}
        self.mixed_colours = {}
        self.nrings = nrings
        self.connect('expose-event', self.expose_cb)
        self.set_has_tooltip(True)
        self.connect('query-tooltip', self.query_tooltip_cb)
        self.add_events(gtk.gdk.SCROLL_MASK)
        self.connect('scroll-event', self.scroll_event_cb)
        self.show()
    # END_DEF: __init__

    def polar_to_cartesian(self, radius, angle):
        if options.get('colour_wheel', 'red_to_yellow_clockwise'):
            x = -radius * math.cos(angle)
        else:
            x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        return (int(self.cx + x), int(self.cy - y))
    # END_DEF: polar_to_cartesian

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
    # END_DEF: get_colour_nearest_to_xy

    def get_colour_at_xy(self, x, y):
        colour, rng = self.get_colour_nearest_to_xy(x, y)
        return colour if rng < self.scaled_size else None
    # END_DEF: get_colour_at_xy

    def query_tooltip_cb(self, widget, x, y, keyboard_mode, tooltip):
        # TODO: move location of tootip as mouse moves
        colour, rng = self.get_colour_nearest_to_xy(x, y)
        tooltip.set_text(colour.name if colour is not None else '')
        return True
    # END_DEF: query_tooltip_cb

    def scroll_event_cb(self, _widget, event):
        if event.device.source == gtk.gdk.SOURCE_MOUSE:
            new_zoom = self.zoom + 0.025 * (-1 if event.direction == gtk.gdk.SCROLL_UP else 1)
            if new_zoom > 1.0 and new_zoom < 5.0:
                self.zoom = new_zoom
                self.queue_draw()
            return True
        return False
    # END_DEF: scroll_event_cb

    def add_colour(self, new_colour):
        if isinstance(new_colour, paint.MixedColour):
            self.mixed_colours[new_colour] = self.ColourCircle(self, new_colour)
        else:
            self.tube_colours[new_colour] = self.ColourSquare(self, new_colour)
        # The data has changed so do a redraw
        self.queue_draw()
    # END_DEF: add_colour

    def del_colour(self, colour):
        if isinstance(colour, paint.MixedColour):
            self.mixed_colours.pop(colour)
        else:
            self.tube_colours.pop(colour)
        # The data has changed so do a redraw
        self.queue_draw()
    # END_DEF: del_colour

    def new_colour(self, rgb):
        colour = gtk.gdk.Color(*rgb)
        return self.get_colormap().alloc_color(colour)
    # END_DEF: new_colour

    def draw_circle(self, cx, cy, radius, filled=False):
        cx -= radius
        cy -= radius
        diam = int(2 * radius)
        self.window.draw_arc(self.gc, filled, int(cx), int(cy), diam, diam, 0, 360 * 64)
    # END_DEF: draw_circle

    def expose_cb(self, _widget, _event):
        self.gc = self.window.new_gc()
        self.gc.copy(self.get_style().fg_gc[gtk.STATE_NORMAL])

        spacer = 10
        scaledmax = 110.0

        self.gc.set_background(self.new_colour(paint.HCVW.WHITE / 2))

        dw, dh = self.window.get_size()
        self.cx = dw / 2
        self.cy = dh / 2

        # calculate a scale factor to use for drawing the graph based
        # on the minimum available width or height
        mindim = min(self.cx, dh / 2)
        self.scale = mindim / scaledmax
        self.one = self.scale * 100
        self.scaled_size = self.size * self.scale

        # Draw the graticule
        self.gc.set_foreground(self.new_colour(paint.HCVW.WHITE * 3 / 4))
        for radius in [100 * (i + 1) * self.scale / self.nrings for i in range(self.nrings)]:
            self.draw_circle(self.cx, self.cy, int(round(radius * self.zoom)))

        self.gc.line_width = 2
        for angle in [paint.rgbh.PI_60 * i for i in range(6)]:
            hue_rgb = paint.HCVW.rgb_for_hue(angle)
            self.gc.set_foreground(self.new_colour(hue_rgb))
            self.window.draw_line(self.gc, self.cx, self.cy, *self.polar_to_cartesian(self.one * self.zoom, angle))
        for tube in self.tube_colours.values():
            tube.draw()
        for mix in self.mixed_colours.values():
            mix.draw()
        return True
    # END_DEF: expose_cb

    class ColourShape(object):
        def __init__(self, parent, colour):
            self.parent = parent
            self.colour = colour
            self.x = None
            self.y = None
            self.pen_width = 2
            self.predraw_setup()
        # END_DEF: __init__

        def predraw_setup(self):
            """
            Set up colour values ready for drawing
            """
            self.colour_angle = self.colour.hue if self.colour.hue is not None else paint.HueAngle(math.pi / 2)
            self.fg_colour = self.parent.new_colour(self.colour.rgb)
            self.value_colour = self.parent.new_colour(paint.BLACK)
            self.chroma_colour = self.parent.new_colour(self.colour.hcvw.chroma_side())
            self.choose_radius_attribute()
        # END_DEF: predraw_setup

        def range_from(self, x, y):
            dx = x - self.x
            dy = y - self.y
            return math.sqrt(dx * dx + dy * dy)
        # END_DEF: range_from
    # END_CLASS: ColourShape

    class ColourSquare(ColourShape):
        polypoints = ((-1, 1), (-1, -1), (1, -1), (1, 1))

        def draw(self):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            square = tuple(tuple(pp[i] * self.parent.scaled_size for i in range(2)) for pp in self.polypoints)
            square_pts = [tuple((int(self.x + pt[0]), int(self.y +  pt[1]))) for pt in square]
            # draw the middle
            self.parent.gc.set_foreground(self.fg_colour)
            self.parent.window.draw_polygon(self.parent.gc, filled=True, points=square_pts)
            self.parent.gc.set_foreground(self.chroma_colour)
            self.parent.window.draw_polygon(self.parent.gc, filled=False, points=square_pts)
        # END_DEF: draw
    # END_CLASS: ColourSquare

    class ColourCircle(ColourShape):
        def draw(self):
            self.predraw_setup()
            self.x, self.y = self.parent.polar_to_cartesian(self.radius * self.parent.zoom, self.colour_angle)
            self.parent.gc.set_foreground(self.fg_colour)
            self.parent.draw_circle(self.x, self.y, radius=self.parent.scaled_size, filled=True)
            self.parent.gc.set_foreground(self.chroma_colour)
            self.parent.draw_circle(self.x, self.y, radius=self.parent.scaled_size, filled=False)
        # END_DEF: draw
    # END_CLASS: ColourCircle
# END_CLASS: ColourWheel

class HueChromaWheel(ColourWheel):
    class ColourSquare(ColourWheel.ColourSquare):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma
        # END_DEF: choose_radius_attribute
    # END_CLASS: ColourSquare

    class ColourCircle(ColourWheel.ColourCircle):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.chroma
        # END_DEF: choose_radius_attribute
    # END_CLASS: ColourCircle
# END_CLASS: HueChromaWheel

class HueValueWheel(ColourWheel):
    class ColourSquare(ColourWheel.ColourSquare):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value
        # END_DEF: choose_radius_attribute
    # END_CLASS: ColourSquare

    class ColourCircle(ColourWheel.ColourCircle):
        def choose_radius_attribute(self):
            self.radius = self.parent.one * self.colour.value
        # END_DEF: choose_radius_attribute
    # END_CLASS: ColourCircle
# END_CLASS: HueValueWheel

class ColourListStore(gtkpwx.NamedListStore):
    Row = collections.namedtuple('Row', ['colour'])
    types = Row(colour=object)

    def append_colour(self, colour):
        self.append(self.Row(colour))
    # END_DEF: append_colour

    def remove_colour(self, colour):
        model_iter = self.find_named(lambda x: x.colour == colour)
        if model_iter is None:
            raise LookupError()
        # return the iter in case the client is interested
        self.emit('colour-removed', colour)
        return self.remove(model_iter)
    # END_DEF: remove_colour

    def remove_colours(self, colours):
        for colour in colours:
            self.remove_colour(colour)
    # END_DEF: remove_colours

    def get_colours(self):
        return [row.colour for row in self.named()]
    # END_DEF: get_colours

    def get_colour_with_name(self, colour_name):
        """
        Return the colour with the specified name or None if not present
        """
        for row in self.named():
            if row.colour.name == colour_name:
                return row.colour
        return None
    # END_DEF: get_colour_with_name
gobject.signal_new('colour-removed', ColourListStore, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
# END_CLASS: ColourListStore

def paint_cell_data_func(column, cell, model, model_iter, attribute):
    colour = model.get_value_named(model_iter, 'colour')
    if attribute == 'name':
        cell.set_property('text', colour.name)
        cell.set_property('background', gtk.gdk.Color(*colour.rgb))
        cell.set_property('foreground', gtkpwx.best_foreground(colour.rgb))
    elif attribute == 'value':
        cell.set_property('text', str(round(colour.value, 2)))
        cell.set_property('background', gtk.gdk.Color(*colour.value_rgb()))
        cell.set_property('foreground', gtkpwx.best_foreground(colour.value_rgb()))
    elif attribute == 'hue':
        cell.set_property('background', gtk.gdk.Color(*colour.hue_rgb))
    elif attribute == 'warmth':
        cell.set_property('background', gtk.gdk.Color(*colour.warmth_rgb()))
    elif attribute == 'permanence':
        cell.set_property('text', str(colour.permanence))
    elif attribute == 'transparency':
        cell.set_property('text', str(colour.transparency))
# END_DEF: paint_cell_data_func

TNS = collections.namedtuple('TNS', ['title', 'attr', 'properties', 'sort_key_function'])

def colour_attribute_column_spec(tns):
    return gtkpwx.ColumnSpec(
        title=tns.title,
        properties=tns.properties,
        sort_key_function=tns.sort_key_function,
        cells=[
            gtkpwx.CellSpec(
                cell_renderer_spec=gtkpwx.CellRendererSpec(
                    cell_renderer=gtk.CellRendererText,
                    expand=None,
                    start=False
                ),
                properties=None,
                cell_data_function_spec=gtkpwx.CellDataFunctionSpec(
                    function=paint_cell_data_func,
                    user_data=tns.attr
                ),
                attributes={}
            ),
        ],
    )
# END_DEF: colour_attribute_column_spec

COLOUR_ATTRS = [
    TNS(_('Colour Name'), 'name', {'resizable' : True}, lambda row: row.colour.name),
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
# END_DEF: colour_attribute_column_specs

def generate_colour_list_spec(model):
    """
    Generate the specification for a paint colour list
    """
    return gtkpwx.ViewSpec(
        properties={},
        selection_mode=gtk.SELECTION_MULTIPLE,
        columns=colour_attribute_column_specs(model)
    )
# END_DEF: generate_colour_list_spec

class ColourListView(gtkpwx.View, gtkpwx.CAGandUIManager):
    Model = ColourListStore
    specification = generate_colour_list_spec(ColourListStore)
    UI_DESCR = '''
    <ui>
        <popup name='colour_list_popup'>
            <menuitem action='remove_selected_colours'/>
        </popup>
    </ui>
    '''
    def __init__(self, *args, **kwargs):
        gtkpwx.View.__init__(self, *args, **kwargs)
        gtkpwx.CAGandUIManager.__init__(self, selection=self.get_selection(), popup='/colour_list_popup')
    # END_DEF: __init__

    def populate_action_groups(self):
        """
        Populate action groups ready for UI initialization.
        """
        self.action_groups[gtkpwx.AC_SELN_MADE].add_actions(
            [
                ('remove_selected_colours', gtk.STOCK_REMOVE, None, None,
                 _('Remove the selected colours from the list.'), self._remove_selection_cb),
            ]
        )
    # END_DEF: populate_action_groups

    def _remove_selection_cb(self, _action):
        """
        Delete the currently selected colours
        """
        self.model.remove_colours(self.get_selected_colours())
    # END_DEF: _remove_selection_cb

    def get_selected_colours(self):
        """
        Return the currently selected colours as a list.
        """
        return [row.colour for row in gtkpwx.NamedTreeModel.get_selected_rows(self.get_selection())]
    # END_DEF: get_selected_colours
# END_CLASS: ColourListView

if __name__ == '__main__':
    doctest.testmod()
