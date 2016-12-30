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
Manipulate Gdk.Pixbuf objects for fun and pleasure
'''

import collections
import math
import fractions
import array

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf

from . import options
from . import utils
from . import gtkpwx
from . import rgbh

if __name__ == '__main__':
    _ = lambda x: x
    import doctest

class RGB(rgbh.RGB8):
    @classmethod
    def scaled_to_sum(cls, rgb, new_sum):
        cur_sum = sum(rgb)
        return array.array(cls.TYPECODE, (int(rgb[i] * new_sum / cur_sum + 0.5) for i in range(3)))
    @classmethod
    def to_mono(cls, rgb):
        val = (sum(rgb) + 1) // 3
        return array.array(cls.TYPECODE, (val, val, val))
WHITE = array.array(RGB.TYPECODE, (RGB.ONE, RGB.ONE, RGB.ONE))
BLACK = array.array(RGB.TYPECODE, (0, 0, 0))

class Hue(rgbh.Hue8):
    pass

def calc_rowstride(bytes_per_row):
    """
    Return the appropriate rowstride to use for a row with the given length
    """
    rem = bytes_per_row % 4
    return bytes_per_row + (0 if rem == 0 else 4 - rem)

class ValueLimitCriteria(collections.namedtuple('ValueLimitCriteria', ['n_values', 'c_totals', 'value_rgbs']), rgbh.BPC8):
    __slots__ = ()
    @classmethod
    def create(cls, n_values):
        """
        Create an instance of ValueLimitCriteria for the specified number of
        levels and rgbs associated with this class (i.e. cls.ONE).
        >>> ValueLimitCriteria.create(6)
        ValueLimitCriteria(n_values=6, c_totals=(Fraction(0, 1), Fraction(1, 5), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5), Fraction(1, 1)))
        """
        c_totals = tuple([int(cls.THREE * i / (n_values - 1) + 0.5) for i in range(n_values)])
        value_rgbs = tuple([array.array(cls.TYPECODE, (int((total + 0.5) / 3),) * 3) for total in c_totals])
        return ValueLimitCriteria(n_values, c_totals, value_rgbs)
    def get_value_index(self, rgb):
        """
        Return the index of rgb value w.r.t. the specified ValueLimitCriteria
        >>> vlc = ValueLimitCriteria.create(6)
        >>> vlc.get_value_index(ONE, ONE, ONE)
        5
        >>> vlc.get_value_index(ONE, ONE, 0)
        3
        >>> vlc.get_value_index(ONE, 0, 0)
        2
        """
        return (sum(rgb) * (self.n_values - 1) * 2 + self.THREE) // self.SIX

class HueLimitCriteria(collections.namedtuple('HueLimitCriteria', ['n_hues', 'hues', 'step'])):
    __slots__ = ()
    @classmethod
    def create(cls, n_hues):
        '''
        >>> import math
        >>> hlc = HueLimitCriteria.create(6)
        >>> hlc.n_hues
        6
        >>> hlc.n_hues == len(hlc.hues)
        True
        >>> hlc.hues[0].angle
        Angle(0.0)
        >>> hlc.hues[1].rgb
        (red=255, green=255, blue=0)
        >>> hlc.hues[3].rgb
        (red=0, green=255, blue=255)
        '''
        step = 2 * math.pi / n_hues
        angles = [utils.Angle.normalize(step * i) for i in range(n_hues)]
        hues = [Hue.from_angle(angle) for angle in angles]
        return HueLimitCriteria(n_hues, hues, step)
    def get_hue_index(self, hue):
        """
        Return the index of hue w.r.t. the specified HueLevelCriteria
        >>> import math
        >>> hlc = HueLimitCriteria.create(6)
        >>> hlc.get_hue_index((ONE, ONE, 0))
        1
        >>> hlc.get_hue_index((ONE, 0, ONE / 2))
        0
        """
        if hue.is_grey():
            return None
        if hue.angle > 0.0:
            index = int(round(float(hue.angle) / self.step))
        else:
            index = int(round((float(hue.angle) + 2 * math.pi) / self.step))
            if index == self.n_hues:
                index = 0
        return index

class HueValueLimitCriteria(collections.namedtuple('HueValueLimitCriteria', ['hlc', 'vlc', 'hv_rgbs'])):
    __slots__ = ()
    @classmethod
    def create(cls, n_hues, n_values):
        hlc = HueLimitCriteria.create(n_hues)
        vlc = ValueLimitCriteria.create(n_values)
        hv_rgbs = [[hue.rgb_with_total(total) for total in vlc.c_totals] for hue in hlc.hues]
        return HueValueLimitCriteria(hlc, vlc, hv_rgbs)
    def get_hue_index(self, hue):
        return self.hlc.get_hue_index(hue)
    def get_value_index(self, rgb):
        return self.vlc.get_value_index(rgb)

class PixBufRow(rgbh.BPC8):
    def __init__(self, data, start, end, nc=3):
        self.rgbs = [array.array(self.TYPECODE, (data[i], data[i+1], data[i+2])) for i in range(start, end, nc)]
        self.hues = [Hue.from_rgb(rgb) for rgb in self.rgbs]
    def __iter__(self):
        for rgb, hue in zip(self.rgbs, self.hues):
            yield (rgb, hue)
    @property
    def width(self):
        return len(self.pixels)
    @property
    def has_alpha(self):
        return False

def transform_row_raw(pbr):
    return pbr.rgbs

def transform_row_mono(pbr):
    return [RGB.to_mono(rgb) for rgb in pbr.rgbs]

def transform_row_notan(pbr, threshold):
    sum_thr = RGB.THREE * threshold.numerator / threshold.denominator
    return [BLACK if sum(rgb) <= sum_thr else WHITE for rgb in pbr.rgbs]

def transform_row_high_chroma(pbr):
    return [hue.rgb_with_total(sum(rgb)) for rgb, hue in pbr]

def transform_row_limited_value(pbr, vlc):
    def transform_limited_value(rgb, hue, vlc):
        index = vlc.get_value_index(rgb)
        if index == 0:
            return BLACK
        elif index == vlc.n_values - 1:
            return WHITE
        try:
            rgb = RGB.scaled_to_sum(rgb, vlc.c_totals[index])
        except OverflowError:
            rgb = hue.rgb_with_total(vlc.c_totals[index])
        return rgb
    return [transform_limited_value(rgb, hue, vlc) for rgb, hue in pbr]

def transform_row_limited_value_mono(pbr, vlc):
    return [vlc.value_rgbs[vlc.get_value_index(rgb)] for rgb in pbr.rgbs]

def transform_row_limited_hue(pbr, hlc):
    def transform_limited_hue(rgb, hue, hlc):
        index = hlc.get_hue_index(hue)
        if index is None:
            return rgb
        if RGB.ncomps(rgb) == 2:
            rgb = hlc.hues[index].rgb_with_total(sum(rgb))
        else:
            rgb = RGB.rotated(rgb, hlc.hues[index].angle - hue.angle)
        return rgb
    return [transform_limited_hue(rgb, hue, hlc) for rgb, hue in pbr]

def transform_row_limited_hue_value(pbr, hvlc):
    def transform_limited_hue_value(rgb, hue, hvlc):
        v_index = hvlc.get_value_index(rgb)
        if v_index == 0:
            return BLACK
        elif v_index == hvlc.vlc.n_values - 1:
            return WHITE
        h_index = hvlc.get_hue_index(hue)
        if h_index is None:
            return hvlc.vlc.value_rgbs[v_index]
        target_total = hvlc.vlc.c_totals[v_index]
        if RGB.ncomps(rgb) == 2:
            rgb = hvlc.hlc.hues[h_index].rgb_with_total(target_total)
        else:
            rgb = RGB.rotated(rgb, hvlc.hlc.hues[h_index].angle - hue.angle)
            try:
                rgb = RGB.scaled_to_sum(rgb, target_total)
            except OverflowError:
                rgb = hvlc.hv_rgbs[h_index][v_index]
        return rgb
    return [transform_limited_hue_value(rgb, hue, hvlc) for rgb, hue in pbr]

def rgb_row_to_string(rgb_row):
    result = array.array('B')
    for rgb in rgb_row:
        result.extend(rgb)
    return result.tostring()

class RGBHImage(GObject.GObject):
    """
    An object containing a RGB and Hue array representing a Pixbuf
    """
    NPR = 50 # the number of progress reports to make during a loop
    def __init__(self, pixbuf=None):
        GObject.GObject.__init__(self)
        self.__size = gtkpwx.WH(width=0, height=0)
        self.__pixel_rows = None
        if pixbuf is not None:
            self.set_from_pixbuf(pixbuf)
    @property
    def size(self):
        """
        The size of this image as an instance gtkpwx.WH
        """
        return self.__size
    def __getitem__(self, index):
        """
        Get the row with the given index
        """
        return self.__pixel_rows[index]
    def set_from_pixbuf(self, pixbuf):
        size = pixbuf.get_width() * pixbuf.get_height()
        if size > 640 * 640:
            # Scale down large images
            ar = fractions.Fraction(pixbuf.get_width(), pixbuf.get_height())
            if ar > 1:
                new_w = int(640 * math.sqrt(ar) + 0.5)
                new_h = int(new_w / ar + 0.5)
            else:
                new_h = int(640 / math.sqrt(ar) + 0.5)
                new_w = int(new_h * ar + 0.5)
            pixbuf = pixbuf.scale_simple(new_w, new_h, GdkPixbuf.InterpType.BILINEAR)
        w, h = (pixbuf.get_width(), pixbuf.get_height())
        self.__size = gtkpwx.WH(width=w, height=h)
        # FUTUREPROOF: make useable for bps other than 8
        # TODO: think about what to do if pixbuf has alpha
        assert pixbuf.get_bits_per_sample() == 8
        nc = pixbuf.get_n_channels()
        rs = pixbuf.get_rowstride()
        data = array.array('B', pixbuf.get_pixels())
        self.__pixel_rows = []
        pr_step = h / self.NPR
        next_pr_due = 0
        for j in range(h):
            if j >= next_pr_due:
                self.emit('progress-made', fractions.Fraction(j, h))
                next_pr_due += pr_step
            start = j * rs
            self.__pixel_rows.append(PixBufRow(data, start, start + w * nc, nc))
        self.emit('progress-made', fractions.Fraction(1))
    def get_mapped_pixbuf(self, map_to_flat_row):
        if self.__pixel_rows is None:
            return None
        bytes_per_row = self.__size.width * 3
        rowstride = calc_rowstride(bytes_per_row)
        padding = b"\000" * (rowstride - bytes_per_row)
        data = b""
        pr_step = len(self.__pixel_rows) / self.NPR
        next_pr_due = 0
        for row_n, pixel_row in enumerate(self.__pixel_rows):
            if row_n >= next_pr_due:
                self.emit('progress-made', fractions.Fraction(row_n, self.__size.height))
                next_pr_due += pr_step
            data += rgb_row_to_string(map_to_flat_row(pixel_row))
            data += padding
        self.emit('progress-made', fractions.Fraction(1))
        return GdkPixbuf.Pixbuf.new_from_data(
            data=data,
            colorspace=GdkPixbuf.Colorspace.RGB,
            has_alpha=False,
            bits_per_sample=8,
            width=self.__size.width,
            height=self.__size.height,
            rowstride=rowstride
        )
    def get_pixbuf(self):
        """
        Return a Gdk.Pixbuf representation of the image
        """
        def map_to_flat_row(row):
            for pixel in row:
                for component in pixel.rgb:
                    yield component
        return self.get_mapped_pixbuf(map_to_flat_row)
GObject.type_register(RGBHImage)
GObject.signal_new('progress-made', RGBHImage, GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))

class Transformer(object):
    """
    A wrapper for an artistic analytical view of an image
    """
    LABEL = ''
    def __init__(self):
        self.initialize_parameters()
    def initialize_parameters(self):
        pass
    def transformed_pixbuf(self, rgbh_image):
        return rgbh_image.get_mapped_pixbuf(self.transform_row)

class TransformerRaw(Transformer):
    LABEL = _('Raw')

    def transform_row(self, row):
        return transform_row_raw(row)

class TransformerNotan(Transformer):
    LABEL = _('Notan')
    def initialize_parameters(self):
        self._threshold = fractions.Fraction(2, 10)
    def transform_row(self, row):
        return transform_row_notan(row, self._threshold)

class TransformerValue(Transformer):
    LABEL = _('Monotone')
    def transform_row(self, row):
        return transform_row_mono(row)

class TransformerRestrictedValue(Transformer):
    LABEL = _('Restricted Value (Monotone)')
    def initialize_parameters(self):
        self.__vlc = ValueLimitCriteria.create(11)
    def transform_row(self, row):
        return transform_row_limited_value_mono(row, self.__vlc)

class TransformerColourRestrictedValue(Transformer):
    LABEL = _('Restricted Value')
    def initialize_parameters(self):
        self.__vlc = ValueLimitCriteria.create(11)
    def transform_row(self, row):
        return transform_row_limited_value(row, self.__vlc)

class TransformerRestrictedHue(Transformer):
    LABEL = _('Restricted Hue')
    def initialize_parameters(self):
        self.__hlc = HueLimitCriteria.create(6)
    def transform_row(self, row):
        return transform_row_limited_hue(row, self.__hlc)

class TransformerRestrictedHueValue(Transformer):
    LABEL = _('Restricted Hue and Value')
    def initialize_parameters(self):
        self.__hvlc = HueValueLimitCriteria.create(6, 11)
    def transform_row(self, row):
        return transform_row_limited_hue_value(row, self.__hvlc)

class TransformerHighChroma(Transformer):
    LABEL = _('High Chroma')
    def initialize_parameters(self):
        pass
    def transform_row(self, row):
        return transform_row_high_chroma(row)

if __name__ == '__main__':
    doctest.testmod()
