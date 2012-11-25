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
    def to_mono(rgb):
        val = (sum(rgb) + 1) / 3
        return RGB(val, val, val)
    # END_DEF: to_mono
WHITE = RGB(ONE, ONE, ONE)
BLACK = RGB(0, 0, 0)
# END_CLASS: RGB

class Hue(rgbh.Hue):
    ONE = ONE
    ZERO = ZERO

class XY(rgbh.XY):
    HUE_CL = Hue

def calc_rowstride(bytes_per_row):
    """
    Return the appropriate rowstride to use for a row with the given length
    """
    rem = bytes_per_row % 4
    return bytes_per_row + (0 if rem == 0 else 4 - rem)
# END_DEF: calc_rowstride

class ValueLimitCriteria(collections.namedtuple('ValueLimitCriteria', ['n_levels', 'values'])):
    __slots__ = ()

    @classmethod
    def create(cls, n_levels):
        """
        Create an instance of ValueLimitCriteria for the specified number of
        levels and rgbs associated with this class (i.e. cls.ONE).
        >>> ValueLimitCriteria.create(6)
        ValueLimitCriteria(n_levels=6, values=(Fraction(0, 1), Fraction(1, 5), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5), Fraction(1, 1)))
        """
        step = fractions.Fraction(1, n_levels - 1)
        values = tuple([step * i for i in range(n_levels)])
        return ValueLimitCriteria(n_levels, values)
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
        return (sum(rgb) * (self.n_levels - 1) * 2 + THREE) / SIX
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
        >>> hlc.hues[0]
        Hue(0.0)
        >>> Hue.get_rgb(hlc.hues[1])
        RGB(red=255, green=255, blue=0)
        >>> Hue.get_rgb(hlc.hues[3])
        RGB(red=0, green=255, blue=255)
        '''
        step = 2 * math.pi / n_hues
        hues = [Hue.normalize(step * i) for i in range(n_hues)]
        return HueLimitCriteria(n_hues, hues, step)
    # END_DEF: create

    def get_hue_index(self, hue):
        """
        Return the index of hue w.r.t. the specified HueLevelCriteria
        >>> import math
        >>> hlc = HueLimitCriteria.create(6)
        >>> hlc.get_hue_index(ONE, ONE, 0)
        1
        >>> hlc.get_hue_index(ONE, 0, ONE / 2)
        0
        """
        if hue > 0.0:
            index = int(round(float(hue) / self.step))
        else:
            index = int(round((float(hue) + 2 * math.pi) / self.step))
            if index == self.n_hues:
                index = 0
        return index
    # END_DEF: get_hue_index
# END_CLASS: HueLimitCriteria

class RGBH(collections.namedtuple('RGBH', ['rgb', 'hue'])):
    __slots__ = ()

    @classmethod
    def from_red_green_blue(cls, red, green, blue):
        """
        Generate an instance from red, green and blue values
        """
        rgb = RGB(red, green, blue)
        hue = XY.from_rgb(rgb).get_hue()
        return cls(rgb, hue)
    # END_DEF: from_pixbuf_data

    @classmethod
    def from_chr_data(cls, data, offset):
        """
        Generate an instance from pixbuf data at the given offet
        """
        return cls.from_red_green_blue(ord(data[offset]), ord(data[offset + 1]), ord(data[offset + 2]))
    # END_DEF: from_pixbuf_data

    @classmethod
    def from_data(cls, data, offset):
        """
        Generate an instance from data at the given offet
        """
        return cls.from_red_green_blue(data[offset], data[offset + 1], data[offset + 2])
    # END_DEF: from_pixbuf_data

    def get_value(self):
        """
        Return the rgb value as a Fraction
        >>> RGBH.from_red_green_blue(ONE, ONE, ONE).get_value()
        Fraction(1, 1)
        >>> RGBH.from_red_green_blue(ONE, ONE, 0).get_value()
        Fraction(2, 3)
        >>> RGBH.from_red_green_blue(ONE, 0, 0).get_value()
        Fraction(1, 3)
        """
        return fractions.Fraction(sum(self.rgb), THREE)
    # END_DEF: get_value

    def get_value_rgb(self):
        """
        Return the rgb with no hue and same value as rgb
        >>> RGBH.from_red_green_blue(ONE, ONE, ONE).get_value_rgb()
        RGB(red=255, green=255, blue=255)
        >>> RGBH.from_red_green_blue(ONE, ONE, 0).get_value_rgb()
        RGB(red=170, green=170, blue=170)
        >>> RGBH.from_red_green_blue(ONE, 0, 0).get_value_rgb()
        RGB(red=85, green=85, blue=85)
        """
        comp = int(round(RGB.get_avg_value(self.rgb)))
        return RGB(comp, comp, comp)
    # END_DEF: get_value_rgb

    def get_hue_rgb(self, value=None):
        """
        Return the rgb for our hue and the given value (or our value
        if the given value is None)
        """
        if self.hue is None:
            if value is None:
                return self.rgb
            else:
                return WHITE * value
        if value is None:
            value = self.get_value()
        return Hue.get_rgb(self.hue, value)
    # END_DEF: get_hue_rgb

    def transform_limited_value(self, vlc):
        value = self.get_value()
        # zero divided by zero is zero so no change
        if value == 0:
            return self
        index = vlc.get_value_index(self.rgb)
        if index == 0:
            return RGBH(BLACK, None)
        elif index == vlc.n_levels - 1:
            return RGBH(WHITE, None)
        rgb = self.rgb * fractions.Fraction(vlc.values[index], value)
        if max(rgb) > ONE:
            rgb = self.get_hue_rgb(vlc.values[index])
        # scaling the rgb values won't change the hue
        return RGBH(rgb, self.hue)
    # END_DEF: transform_limited_value

    def transform_limited_hue(self, hlc):
        if self.hue is None:
            return self
        index = hlc.get_hue_index(self.hue)
        if RGB.ncomps(self.rgb) == 2:
            value = self.get_value()
            rgb = Hue.get_rgb(hlc.hues[index], value)
        else:
            rgb = RGB.rotated(self.rgb, hlc.hues[index] - self.hue)
        return RGBH(rgb, hlc.hues[index])
    # END_DEF: transform_limited_hue
# END_CLASS: RGBH

class PixBufRow:
    def __init__(self, data, start, end, nc=3):
        self.pixels = [RGBH.from_data(data, i) for i in xrange(start, end, nc)]
    # END_DEF: __init__

    def __iter__(self):
        for pixel in self.pixels:
            yield pixel
    # END_DEF: __iter__

    @property
    def width(self):
        return len(self.pixels)
    # END_DEF: width

    @property
    def has_alpha(self):
        return False
    # END_DEF: has_alpha

    def tostring(self):
        assert False
        return self.pixels.tostring()
    # END_DEF: tostring
# END_CLASS: PixBufRow

def transform_row_raw(pbr):
    return [pixel.rgb for pixel in pbr]
# END_DEF: transform_row_raw

def transform_row_mono(pbr):
    return [RGB.to_mono(pixel.rgb) for pixel in pbr]
# END_DEF: transform_row_mono

def transform_row_notan(pbr, threshold):
    return [BLACK if RGB.get_value(pixel.rgb) <= threshold else WHITE for pixel in pbr]
# END_DEF: transform_row_notan

def transform_row_high_chroma(pbr, *args):
    return [pixel.get_hue_rgb() for pixel in pbr]
# END_DEF: transform_row_notan

def transform_row_limited_value(pbr, vlc):
    return [pixel.transform_limited_value(vlc).rgb for pixel in pbr]
# END_DEF: transform_row_high_chroma

def transform_row_limited_value_mono(pbr, vlc):
    return [RGB.to_mono(pixel.transform_limited_value(vlc).rgb) for pixel in pbr]
# END_DEF: transform_row_limited_value_mono

def transform_row_limited_hue(pbr, hlc):
    return [pixel.transform_limited_hue(hlc).rgb for pixel in pbr]
# END_DEF: transform_limited_hue

def transform_row_limited_hue_value(pbr, hlc, vlc):
    return [pixel.transform_limited_value(vlc).transform_limited_hue(hlc).rgb for pixel in pbr]
# END_DEF: transform_limited_hue_value

class RGBHImage(gobject.GObject):
    """
    An object containing a RGB and Hue array representing a Pixbuf
    """

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
        w, h = (pixbuf.get_width(), pixbuf.get_height())
        # FUTUREPROOF: make useable for bps other than 8
        # TODO: think about what to do if pixbuf has alpha
        assert pixbuf.get_bits_per_sample() == 8
        nc = pixbuf.get_n_channels()
        rs = pixbuf.get_rowstride()
        data = array.array('B', pixbuf.get_pixels()).tolist()
        self.__pixel_rows = []
        for j in range(h):
            self.emit('progress-made', fractions.Fraction(j, h))
            start = j * rs
            self.__pixel_rows.append(PixBufRow(data, start, start + w * nc, nc))
        self.emit('progress-made', fractions.Fraction(1))
        self.__size = gtkpwx.WH(width=w, height=h)
    # END_DEF: set_from_pixbuf

    def get_mapped_pixbuf(self, map_to_flat_row):
        if self.__pixel_rows is None:
            return None
        bytes_per_row = self.__size.width * 3
        rowstride = calc_rowstride(bytes_per_row)
        padding = '\000' * (rowstride - bytes_per_row)
        data = ''
        for row_n, pixel_row in enumerate(self.__pixel_rows):
            data += array.array('B', map_to_flat_row(pixel_row)).tostring()
            data += padding
            self.emit('progress-made', fractions.Fraction(row_n + 1, self.__size.height))
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

if __name__ == '__main__':
    doctest.testmod()
