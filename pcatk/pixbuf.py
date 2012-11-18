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
WHITE = rgbh.RGB(ONE, ONE, ONE)
BLACK = rgbh.RGB(0, 0, 0)

def calc_rowstride(bytes_per_row):
    """
    Return the appropriate rowstride to use for a row with the given length
    """
    rem = bytes_per_row % 4
    return bytes_per_row + (0 if rem == 0 else 4 - rem)
# END_DEF: calc_rowstride

ValueLevelCriteria = collections.namedtuple('ValueLevelCriteria', ['n_levels', 'values'])
HueLimitCriteria = collections.namedtuple('HueLimitCriteria', ['n_hues', 'hues', 'step'])

class Hue(rgbh.Hue):
    ONE = ONE
    ZERO = ZERO

class XY(rgbh.XY):
    HUE_CL = Hue

class RGBH(collections.namedtuple('RGBH', ['rgb', 'hue'])):
    __slots__ = ()

    @classmethod
    def from_red_green_blue(cls, red, green, blue):
        """
        Generate an instance from red, green and blue values
        """
        rgb = rgbh.RGB(red, green, blue)
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

    @classmethod
    def create_value_level_criteria(cls, n_levels):
        """
        Create an instance of ValueLevelCriteria for the specified number of
        levels and rgbs associated with this class (i.e. cls.ONE).
        >>> RGBH.create_value_level_criteria(6)
        ValueLevelCriteria(n_levels=6, values=(Fraction(0, 1), Fraction(1, 5), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5), Fraction(1, 1)))
        """
        step = fractions.Fraction(1, n_levels - 1)
        values = tuple([step * i for i in range(n_levels)])
        return ValueLevelCriteria(n_levels, values)
    # END_DEF: create_value_level_criteria

    @classmethod
    def create_hue_limit_criteria(cls, n_hues):
        '''
        >>> import math
        >>> hlc = RGBH.create_hue_limit_criteria(6)
        >>> hlc.n_hues
        6
        >>> hlc.n_hues == len(hlc.hues)
        True
        >>> hlc.hues[0]
        Hue(0.0)
        >>> hlc.hues[1].get_rgb()
        RGB(red=255, green=255, blue=0)
        >>> hlc.hues[3].get_rgb()
        RGB(red=0, green=255, blue=255)
        '''
        step = 2 * math.pi / n_hues
        hues = [Hue.normalize(step * i) for i in range(n_hues)]
        return HueLimitCriteria(n_hues, hues, step)
    # END_DEF: create_hue_limit_criteria

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
        comp = int(round(self.rgb.get_avg_value()))
        return rgbh.RGB(comp, comp, comp)
    # END_DEF: get_value_rgb

    def get_value_index(self, vlc):
        """
        Return the index of rgb value w.r.t. the specified ValueLevelCriteria
        >>> vlc = RGBH.create_value_level_criteria(6)
        >>> RGBH.from_red_green_blue(ONE, ONE, ONE).get_value_index(vlc)
        5
        >>> RGBH.from_red_green_blue(ONE, ONE, 0).get_value_index(vlc)
        3
        >>> RGBH.from_red_green_blue(ONE, 0, 0).get_value_index(vlc)
        2
        """
        return (sum(self.rgb) * (vlc.n_levels - 1) * 2 + THREE) / SIX
    # END_DEF: get_value_index

    def get_hue_index(self, hlc):
        """
        Return the index of hue w.r.t. the specified HueLevelCriteria
        >>> import math
        >>> hlc = RGBH.create_hue_limit_criteria(6)
        >>> RGBH.from_red_green_blue(ONE, ONE, 0).get_hue_index(hlc)
        1
        >>> RGBH.from_red_green_blue(ONE, 0, ONE / 2).get_hue_index(hlc)
        0
        """
        if self.hue > 0.0:
            index = int(round(float(self.hue) / hlc.step))
        else:
            index = int(round((float(self.hue) + 2 * math.pi) / hlc.step))
            if index == hlc.n_hues:
                index = 0
        return index
    # END_DEF: get_hue_index

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
        return self.hue.get_rgb(value)
    # END_DEF: get_hue_rgb

    def transform_limited_value(self, vlc):
        value = self.get_value()
        # zero divided by zero is zero so no change
        if value == 0:
            return self
        index = self.get_value_index(vlc)
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
        index = self.get_hue_index(hlc)
        if self.rgb.ncomps() == 2:
            value = self.get_value()
            rgb = hlc.hues[index].get_rgb(value)
        else:
            rgb = self.rgb.rotated(hlc.hues[index] - self.hue)
        return RGBH(rgb, hlc.hues[index])
    # END_DEF: transform_limited_hue
# END_CLASS: RGBH

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
            my_row_j = []
            in_row_j_start = j * rs
            in_row_j_end = in_row_j_start + w * nc
            for i in range(in_row_j_start, in_row_j_end, nc):
                my_row_j.append(RGBH.from_data(data, i))
            self.__pixel_rows.append(my_row_j)
            self.emit('progress-made', fractions.Fraction(j + 1, h))
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
