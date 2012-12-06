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
Manipulate gtk.gdk.Pixbuf objects for fun and pleasure
'''

import collections
import math
import fractions
import array

import gtk
import gobject

from pcatk import options
from pcatk import utils
from pcatk import gtkpwx
from pcatk import rgbh

if __name__ == '__main__':
    _ = lambda x: x
    import doctest

# 8 bits per channel specific constants
ZERO = 0
BITS_PER_CHANNEL = 8
ONE = (1 << BITS_PER_CHANNEL) - 1
THREE = ONE * 3
SIX = ONE * 6

class RGB(rgbh.RGB):
    @staticmethod
    def get_value(rgb):
        return fractions.Fraction(sum(rgb), THREE)
    # END_DEF: get_value

    @staticmethod
    def scaled_to_sum(rgb, new_sum):
        cur_sum = sum(rgb)
        return tuple(int(rgb[i] * new_sum / cur_sum + 0.5) for i in range(3))
    # END_DEF: get_value

    @staticmethod
    def to_mono(rgb):
        val = (sum(rgb) + 1) / 3
        return (val, val, val)
    # END_DEF: to_mono
WHITE = (ONE, ONE, ONE)
BLACK = (0, 0, 0)
# END_CLASS: RGB

class XY(rgbh.XY):
    ONE = ONE

def calc_rowstride(bytes_per_row):
    """
    Return the appropriate rowstride to use for a row with the given length
    """
    rem = bytes_per_row % 4
    return bytes_per_row + (0 if rem == 0 else 4 - rem)
# END_DEF: calc_rowstride

class ValueLimitCriteria(collections.namedtuple('ValueLimitCriteria', ['n_values', 'c_totals', 'value_rgbs'])):
    __slots__ = ()

    @classmethod
    def create(cls, n_values):
        """
        Create an instance of ValueLimitCriteria for the specified number of
        levels and rgbs associated with this class (i.e. cls.ONE).
        >>> ValueLimitCriteria.create(6)
        ValueLimitCriteria(n_values=6, c_totals=(Fraction(0, 1), Fraction(1, 5), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5), Fraction(1, 1)))
        """
        c_totals = tuple([int(THREE * i / (n_values - 1) + 0.5) for i in range(n_values)])
        value_rgbs = tuple([(int((total + 0.5) / 3),) * 3 for total in c_totals])
        return ValueLimitCriteria(n_values, c_totals, value_rgbs)
    # END_DEF: create

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
        return (sum(rgb) * (self.n_values - 1) * 2 + THREE) / SIX
    # END_DEF: get_value_index
# END_CLASS: ValueLimitCriteria

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
        hues = [rgbh.Hue.from_angle(angle, ONE) for angle in angles]
        return HueLimitCriteria(n_hues, hues, step)
    # END_DEF: create

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
    # END_DEF: get_hue_index
# END_CLASS: HueLimitCriteria

class HueValueLimitCriteria(collections.namedtuple('HueValueLimitCriteria', ['hlc', 'vlc', 'hv_rgbs'])):
    __slots__ = ()

    @classmethod
    def create(cls, n_hues, n_values):
        hlc = HueLimitCriteria.create(n_hues)
        vlc = ValueLimitCriteria.create(n_values)
        hv_rgbs = [[hue.rgb_with_total(total) for total in vlc.c_totals] for hue in hlc.hues]
        return HueValueLimitCriteria(hlc, vlc, hv_rgbs)
    # END_DEF: create

    def get_hue_index(self, hue):
        return self.hlc.get_hue_index(hue)
    # END_DEF: get_hue_index

    def get_value_index(self, rgb):
        return self.vlc.get_value_index(rgb)
    # END_DEF: get_value_index
# END_CLASS: HueValueLimitCriteria

class PixBufRow:
    def __init__(self, data, start, end, nc=3):
        self.rgbs = [(data[i], data[i+1], data[i+2]) for i in xrange(start, end, nc)]
        self.hues = [XY.from_rgb(rgb).get_hue() for rgb in self.rgbs]

    def __iter__(self):
        for rgb, hue in zip(self.rgbs, self.hues):
            yield (rgb, hue)
    # END_DEF: __iter__

    @property
    def width(self):
        return len(self.pixels)
    # END_DEF: width

    @property
    def has_alpha(self):
        return False
    # END_DEF: has_alpha
# END_CLASS: PixBufRow

def transform_row_raw(pbr):
    return pbr.rgbs
# END_DEF: transform_row_raw

def transform_row_mono(pbr):
    return [RGB.to_mono(rgb) for rgb in pbr.rgbs]
# END_DEF: transform_row_mono

def transform_row_notan(pbr, threshold):
    sum_thr = THREE * threshold.numerator / threshold.denominator
    return [BLACK if sum(rgb) <= sum_thr else WHITE for rgb in pbr.rgbs]
# END_DEF: transform_row_notan

def transform_row_high_chroma(pbr):
    return [hue.rgb_with_total(sum(rgb)) for rgb, hue in pbr]
# END_DEF: transform_row_notan

def transform_row_limited_value(pbr, vlc):
    def transform_limited_value(rgb, hue, vlc):
        index = vlc.get_value_index(rgb)
        if index == 0:
            return BLACK
        elif index == vlc.n_values - 1:
            return WHITE
        rgb = RGB.scaled_to_sum(rgb, vlc.c_totals[index])
        if max(rgb) > ONE:
            rgb = hue.rgb_with_total(vlc.c_totals[index])
        return rgb
    # END_DEF: transform_limited_value
    return [transform_limited_value(rgb, hue, vlc) for rgb, hue in pbr]
# END_DEF: transform_row_limited_value

def transform_row_limited_value_mono(pbr, vlc):
    return [vlc.value_rgbs[vlc.get_value_index(rgb)] for rgb in pbr.rgbs]
# END_DEF: transform_row_limited_value_mono

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
    # END_DEF: transform_limited_hue
    return [transform_limited_hue(rgb, hue, hlc) for rgb, hue in pbr]
# END_DEF: transform_limited_hue

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
            rgb = RGB.scaled_to_sum(rgb, target_total)
            if max(rgb) > ONE:
                rgb = hvlc.hv_rgbs[h_index][v_index]
        return rgb
    # END_DEF: transform_limited_hue
    return [transform_limited_hue_value(rgb, hue, hvlc) for rgb, hue in pbr]
# END_DEF: transform_limited_hue_value

def rgb_row_to_string(rgb_row):
    def flatten(rgb_row):
        for rgb in rgb_row:
            for component in rgb:
                yield component
    return array.array('B', flatten(rgb_row)).tostring()
# END_DEF: rgb_row_to_string

class RGBHImage(gobject.GObject):
    """
    An object containing a RGB and Hue array representing a Pixbuf
    """
    NPR = 50 # the number of progress reports to make during a loop

    def __init__(self, pixbuf=None):
        gobject.GObject.__init__(self)
        self.__size = gtkpwx.WH(width=0, height=0)
        self.__pixel_rows = None
        if pixbuf is not None:
            self.set_from_pixbuf(pixbuf)
    # END_DEF: __init__()

    @property
    def size(self):
        """
        The size of this image as an instance gtkpwx.WH
        """
        return self.__size
    # END_DEF: size

    def __getitem__(self, index):
        """
        Get the row with the given index
        """
        return self.__pixel_rows[index]
    # END_DEF: __getitem__

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
            pixbuf = pixbuf.scale_simple(new_w, new_h, gtk.gdk.INTERP_BILINEAR)
        w, h = (pixbuf.get_width(), pixbuf.get_height())
        self.__size = gtkpwx.WH(width=w, height=h)
        # FUTUREPROOF: make useable for bps other than 8
        # TODO: think about what to do if pixbuf has alpha
        assert pixbuf.get_bits_per_sample() == 8
        nc = pixbuf.get_n_channels()
        rs = pixbuf.get_rowstride()
        data = array.array('B', pixbuf.get_pixels()).tolist()
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
    # END_DEF: set_from_pixbuf

    def get_mapped_pixbuf(self, map_to_flat_row):
        if self.__pixel_rows is None:
            return None
        bytes_per_row = self.__size.width * 3
        rowstride = calc_rowstride(bytes_per_row)
        padding = '\000' * (rowstride - bytes_per_row)
        data = ''
        pr_step = len(self.__pixel_rows) / self.NPR
        next_pr_due = 0
        for row_n, pixel_row in enumerate(self.__pixel_rows):
            if row_n >= next_pr_due:
                self.emit('progress-made', fractions.Fraction(row_n, self.__size.height))
                next_pr_due += pr_step
            data += rgb_row_to_string(map_to_flat_row(pixel_row))
            data += padding
        self.emit('progress-made', fractions.Fraction(1))
        return gtk.gdk.pixbuf_new_from_data(
            data=data,
            colorspace=gtk.gdk.COLORSPACE_RGB,
            has_alpha=False,
            bits_per_sample=8,
            width=self.__size.width,
            height=self.__size.height,
            rowstride=rowstride
        )
    # END_DEF: get_mapped_pixbuf

    def get_pixbuf(self):
        """
        Return a gtk.gdk.Pixbuf representation of the image
        """
        def map_to_flat_row(row):
            for pixel in row:
                for component in pixel.rgb:
                    yield component
        return self.get_mapped_pixbuf(map_to_flat_row)
    # END_DEF: get_pixbuf
gobject.type_register(RGBHImage)
gobject.signal_new('progress-made', RGBHImage, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
# END_CLASS: RGBHImage

class Transformer(object):
    """
    A wrapper for an artistic analytical view of an image
    """
    LABEL = ''

    def __init__(self):
        self.initialize_parameters()
    # END_DEF: __init__()

    def initialize_parameters(self):
        pass
    # END_DEF: initialize_parameters

    def transformed_pixbuf(self, rgbh_image):
        return rgbh_image.get_mapped_pixbuf(self.transform_row)
    # END_DEF: transformed_pixbuf
# END_CLASS: Transformer

class TransformerRaw(Transformer):
    LABEL = _('Raw')

    def transform_row(self, row):
        return transform_row_raw(row)
    # END_DEF: transform_row
# END_CLASS: TransformerRaw

class TransformerNotan(Transformer):
    LABEL = _('Notan')

    def initialize_parameters(self):
        self._threshold = fractions.Fraction(2, 10)
    # END_DEF: initialize_parameters

    def transform_row(self, row):
        return transform_row_notan(row, self._threshold)
    # END_DEF: transform_row
# END_CLASS: TransformerNotan

class TransformerValue(Transformer):
    LABEL = _('Monotone')

    def transform_row(self, row):
        return transform_row_mono(row)
    # END_DEF: transform_row
# END_CLASS: TransformerValue

class TransformerRestrictedValue(Transformer):
    LABEL = _('Restricted Value (Monotone)')

    def initialize_parameters(self):
        self.__vlc = ValueLimitCriteria.create(11)
    # END_DEF: initialize_parameters

    def transform_row(self, row):
        return transform_row_limited_value_mono(row, self.__vlc)
    # END_DEF: transform_row
# END_CLASS: TransformerRestrictedValue

class TransformerColourRestrictedValue(Transformer):
    LABEL = _('Restricted Value')

    def initialize_parameters(self):
        self.__vlc = ValueLimitCriteria.create(11)
    # END_DEF: initialize_parameters

    def transform_row(self, row):
        return transform_row_limited_value(row, self.__vlc)
    # END_DEF: transform_row
# END_CLASS: TransformerColourRestrictedValue

class TransformerRestrictedHue(Transformer):
    LABEL = _('Restricted Hue')

    def initialize_parameters(self):
        self.__hlc = HueLimitCriteria.create(6)
    # END_DEF: initialize_parameters

    def transform_row(self, row):
        return transform_row_limited_hue(row, self.__hlc)
    # END_DEF: transform_row
# END_CLASS: TransformerRestrictedHue

class TransformerRestrictedHueValue(Transformer):
    LABEL = _('Restricted Hue and Value')

    def initialize_parameters(self):
        self.__hvlc = HueValueLimitCriteria.create(6, 11)
    # END_DEF: initialize_parameters

    def transform_row(self, row):
        return transform_row_limited_hue_value(row, self.__hvlc)
    # END_DEF: transform_row
# END_CLASS: TransformerRestrictedHueValue

class TransformerHighChroma(Transformer):
    LABEL = _('High Chroma')

    def initialize_parameters(self):
        pass
    # END_DEF: initialize_parameters

    def transform_row(self, row):
        return transform_row_high_chroma(row)
    # END_DEF: transform_row
# END_CLASS: TransformerHighChroma

if __name__ == '__main__':
    doctest.testmod()
