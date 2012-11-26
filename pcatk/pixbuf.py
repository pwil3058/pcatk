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

class HueAngle(rgbh.HueAngle):
    ONE = ONE
    ZERO = ZERO

class XY(rgbh.XY):
    HUE_CL = HueAngle

def calc_rowstride(bytes_per_row):
    """
    Return the appropriate rowstride to use for a row with the given length
    """
    rem = bytes_per_row % 4
    return bytes_per_row + (0 if rem == 0 else 4 - rem)
# END_DEF: calc_rowstride

class ValueLimitCriteria(collections.namedtuple('ValueLimitCriteria', ['n_values', 'values', 'value_rgbs'])):
    __slots__ = ()

    @classmethod
    def create(cls, n_values):
        """
        Create an instance of ValueLimitCriteria for the specified number of
        levels and rgbs associated with this class (i.e. cls.ONE).
        >>> ValueLimitCriteria.create(6)
        ValueLimitCriteria(n_values=6, values=(Fraction(0, 1), Fraction(1, 5), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5), Fraction(1, 1)))
        """
        step = fractions.Fraction(1, n_values - 1)
        values = tuple([step * i for i in range(n_values)])
        value_rgbs = tuple([WHITE * value for value in values])
        return ValueLimitCriteria(n_values, values, value_rgbs)
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

class HueLimitCriteria(collections.namedtuple('HueLimitCriteria', ['n_hues', 'hue_angles', 'step'])):
    __slots__ = ()

    @classmethod
    def create(cls, n_hues):
        '''
        >>> import math
        >>> hlc = HueLimitCriteria.create(6)
        >>> hlc.n_hues
        6
        >>> hlc.n_hues == len(hlc.hue_angles)
        True
        >>> hlc.hue_angles[0]
        HueAngle(0.0)
        >>> HueAngle.get_rgb(hlc.hue_angles[1])
        RGB(red=255, green=255, blue=0)
        >>> HueAngle.get_rgb(hlc.hue_angles[3])
        RGB(red=0, green=255, blue=255)
        '''
        step = 2 * math.pi / n_hues
        hue_angles = [HueAngle.normalize(step * i) for i in range(n_hues)]
        return HueLimitCriteria(n_hues, hue_angles, step)
    # END_DEF: create

    def get_hue_angle_index(self, hue_angle):
        """
        Return the index of hue_angle w.r.t. the specified HueLevelCriteria
        >>> import math
        >>> hlc = HueLimitCriteria.create(6)
        >>> hlc.get_hue_angle_index((ONE, ONE, 0))
        1
        >>> hlc.get_hue_angle_index((ONE, 0, ONE / 2))
        0
        """
        if hue_angle > 0.0:
            index = int(round(float(hue_angle) / self.step))
        else:
            index = int(round((float(hue_angle) + 2 * math.pi) / self.step))
            if index == self.n_hues:
                index = 0
        return index
    # END_DEF: get_hue_angle_index
# END_CLASS: HueLimitCriteria

class HueValueLimitCriteria(collections.namedtuple('HueValueLimitCriteria', ['hlc', 'vlc', 'hv_rgbs'])):
    __slots__ = ()

    @classmethod
    def create(cls, n_hues, n_values):
        hlc = HueLimitCriteria.create(n_hues)
        vlc = ValueLimitCriteria.create(n_values)
        hv_rgbs = [[HueAngle.get_rgb(hue_angle, val) for val in vlc.values] for hue_angle in hlc.hue_angles]
        return HueValueLimitCriteria(hlc, vlc, hv_rgbs)
    # END_DEF: create

    def get_hue_angle_index(self, hue_angle):
        return self.hlc.get_hue_angle_index(hue_angle)
    # END_DEF: get_hue_angle_index

    def get_value_index(self, rgb):
        return self.vlc.get_value_index(rgb)
    # END_DEF: get_value_index
# END_CLASS: HueValueLimitCriteria

class RGBH(collections.namedtuple('RGBH', ['rgb', 'hue_angle'])):
    __slots__ = ()

    @classmethod
    def from_data(cls, data, offset):
        """
        Generate an instance from data at the given offet
        """
        rgb = RGB(data[offset], data[offset + 1], data[offset + 2])
        hue_angle = XY.from_rgb(rgb).get_hue_angle()
        return cls(rgb, hue_angle)
    # END_DEF: from_pixbuf_data

    def transform_high_chroma(self):
        if math.isnan(self.hue_angle):
            return self.rgb
        return HueAngle.get_rgb(self.hue_angle, RGB.get_value(self.rgb))
    # END_DEF: transform_high_chroma

    def transform_limited_value(self, vlc):
        index = vlc.get_value_index(self.rgb)
        if index == 0:
            return BLACK
        elif index == vlc.n_values - 1:
            return WHITE
        value = RGB.get_value(self.rgb)
        rgb = self.rgb * fractions.Fraction(vlc.values[index], value)
        if max(rgb) > ONE:
            if math.isnan(self.hue_angle):
                rgb = WHITE
            else:
                rgb = HueAngle.get_rgb(self.hue_angle, vlc.values[index])
        return rgb
    # END_DEF: transform_limited_value

    def transform_limited_value_mono(self, vlc):
        index = vlc.get_value_index(self.rgb)
        return vlc.value_rgbs[index]
    # END_DEF: transform_limited_value

    def transform_limited_hue(self, hlc):
        if math.isnan(self.hue_angle):
            return self.rgb
        index = hlc.get_hue_angle_index(self.hue_angle)
        if RGB.ncomps(self.rgb) == 2:
            value = RGB.get_value(self.rgb)
            rgb = HueAngle.get_rgb(hlc.hue_angles[index], value)
        else:
            rgb = RGB.rotated(self.rgb, hlc.hue_angles[index] - self.hue_angle)
        return rgb
    # END_DEF: transform_limited_hue

    def transform_limited_hue_value(self, hvlc):
        v_index = hvlc.get_value_index(self.rgb)
        if v_index == 0:
            return BLACK
        elif v_index == hvlc.vlc.n_values - 1:
            return WHITE
        elif math.isnan(self.hue_angle):
            return self.rgb
        h_index = hvlc.get_hue_angle_index(self.hue_angle)
        target_value = hvlc.vlc.values[v_index]
        if RGB.ncomps(self.rgb) == 2:
            rgb = HueAngle.get_rgb(hvlc.hlc.hue_angles[h_index], target_value)
        else:
            rgb = RGB.rotated(self.rgb, hvlc.hlc.hue_angles[h_index] - self.hue_angle)
            rgb = rgb * fractions.Fraction(target_value, RGB.get_value(rgb))
            if max(rgb) > ONE:
                rgb = hvlc.hv_rgbs[h_index][v_index]
        return rgb
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

def transform_row_high_chroma(pbr):
    return [pixel.transform_high_chroma() for pixel in pbr]
# END_DEF: transform_row_notan

def transform_row_limited_value(pbr, vlc):
    return [pixel.transform_limited_value(vlc) for pixel in pbr]
# END_DEF: transform_row_high_chroma

def transform_row_limited_value_mono(pbr, vlc):
    return [pixel.transform_limited_value_mono(vlc) for pixel in pbr]
# END_DEF: transform_row_limited_value_mono

def transform_row_limited_hue(pbr, hlc):
    return [pixel.transform_limited_hue(hlc) for pixel in pbr]
# END_DEF: transform_limited_hue

def transform_row_limited_hue_value(pbr, hvlc):
    return [pixel.transform_limited_hue_value(hvlc) for pixel in pbr]
# END_DEF: transform_limited_hue_value

class RGBHImage(gobject.GObject):
    """
    An object containing a RGB and HueAngle array representing a Pixbuf
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
