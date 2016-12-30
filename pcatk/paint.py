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
Virtual paint library
'''

import collections
import math
import re
import fractions

from . import rgbh

if __name__ == '__main__':
    import doctest
    _ = lambda x: x

class RGB(rgbh.RGB16):
    __slots__ = ()
    def __add__(self, other):
        '''
        Add two RGB values together
        '''
        return RGB(red=self.red + other.red, green=self.green + other.green, blue=self.blue + other.blue)
    def __sub__(self, other):
        '''
        Subtract one RGB value from another
        '''
        return RGB(red=self.red - other.red, green=self.green - other.green, blue=self.blue - other.blue)
    def __mul__(self, mul):
        '''
        Multiply all components by a fraction preserving component type
        '''
        return RGB(*(self.ROUND(self[i] * mul) for i in range(3)))
    def __truediv__(self, div):
        '''
        Divide all components by a value
        '''
        return RGB(*(self.ROUND(self[i] / div) for i in range(3)))
    def __str__(self):
        return 'RGB(0x{0:X}, 0x{1:X}, 0x{2:X})'.format(*self)
    @staticmethod
    def rotated(rgb, delta_hue_angle):
        return RGB(*rgbh.RGB16.rotated(rgb, delta_hue_angle))

class Hue(rgbh.Hue16):
    pass

# Primary Colours
RGB_RED = RGB(red=RGB.ONE, green=RGB.ZERO, blue=RGB.ZERO)
RGB_GREEN = RGB(red=RGB.ZERO, green=RGB.ONE, blue=RGB.ZERO)
RGB_BLUE = RGB(red=RGB.ZERO, green=RGB.ZERO, blue=RGB.ONE)
# Secondary Colours
RGB_CYAN = RGB_BLUE + RGB_GREEN
RGB_MAGENTA = RGB_BLUE + RGB_RED
RGB_YELLOW = RGB_RED + RGB_GREEN
# Black and White
RGB_WHITE = RGB_RED + RGB_GREEN + RGB_BLUE
RGB_BLACK = RGB(*((0,) * 3))
# The "ideal" palette is one that contains the full range at full strength
IDEAL_RGB_COLOURS = [RGB_WHITE, RGB_MAGENTA, RGB_RED, RGB_YELLOW, RGB_GREEN, RGB_CYAN, RGB_BLUE, RGB_BLACK]
IDEAl_COLOUR_NAMES = ['WHITE', 'MAGENTA', 'RED', 'YELLOW', 'GREEN', 'CYAN', 'BLUE', 'BLACK']

class HCVW(object):
    def __init__(self, rgb):
        self.rgb = RGB(*rgb)
        self.value = self.rgb.get_value()
        xy = rgbh.XY.from_rgb(self.rgb)
        self.warmth = fractions.Fraction.from_float(xy.x / RGB.ONE)
        self.hue = Hue.from_angle(xy.get_angle())
        self.chroma = xy.get_hypot() * self.hue.chroma_correction / RGB.ONE
    def value_rgb(self):
        return RGB_WHITE * self.value
    def hue_rgb_for_value(self, value=None):
        if value is None:
            # i.e. same hue and value but without any unnecessary grey
            value = self.value
        return RGB(*self.hue.rgb_with_value(value))
    def zero_chroma_rgb(self):
        # get the rgb for the grey which would result from this colour
        # having white or black (whichever is quicker) added until the
        # chroma value is zero (useful for displaying chroma values)
        if self.hue.is_grey():
            return self.value_rgb()
        mcv = self.hue.max_chroma_value()
        dc = 1.0 - self.chroma
        if dc != 0.0:
            return RGB_WHITE * ((self.value - mcv * self.chroma) / dc)
        elif mcv < 0.5:
            return RGB_BLACK
        else:
            return RGB_WHITE
    def chroma_side(self):
        # Is it darker or lighter than max chroma for the hue?
        if sum(self.rgb) > sum(self.hue.rgb):
            return WHITE
        else:
            return BLACK
    def get_rotated_rgb(self, delta_hue_angle):
        '''
        Return a copy of our rgb rotated by the given amount but with
        the same value and without unavoidable chroma change.
        import utils
        >>> HCVW((10, 10, 0)).get_rotated_rgb(-utils.PI_60)
        RGB(red=20, green=0, blue=0)
        '''
        if RGB.ncomps(self.rgb) == 2:
            # we have no grey so only add grey if necessary to maintain value
            hue = Hue.from_angle(self.hue.angle + delta_hue_angle)
            return RGB(*hue.rgb_with_value(self.value))
        else:
            # Simple rotation is the correct solution for 1 or 3 components
            return RGB.rotated(self.rgb, delta_hue_angle)
    def __str__(self):
        string = '(HUE = {0}, '.format(str(self.hue.rgb))
        string += 'VALUE = {0}, '.format(round(self.value, 2))
        string += 'CHROMA = {0}, '.format(round(self.chroma, 2))
        string += 'WARMTH = {0})'.format(round(self.warmth, 2))
        return string

RATING = collections.namedtuple('RATING', ['abbrev', 'descr', 'rval'])

class MappedFloat(object):
    class BadValue(Exception): pass
    MAP = None
    def __init__(self, ival=0.0):
        if isinstance(ival, (str, bytes)):
            self.val = None
            for mapi in self.MAP:
                if ival == mapi.abbrev or ival == mapi.descr:
                    self.val = mapi.rval
                    break
            if self.val is None:
                try:
                    self.val = float(ival)
                except ValueError:
                    raise self.BadValue(_('Unrecognized rating value: {0}').format(ival))
        else: # assume it's a real value in the mapped range
            self.val = ival
    def __str__(self):
        rval = round(self.val, 0)
        for mapi in self.MAP:
            if rval == mapi.rval:
                return mapi.abbrev
        raise  self.BadValue(_('Invalid rating: {0}').format(self.val))
    def description(self):
        rval = round(self.val, 0)
        for mapi in self.MAP:
            if rval == mapi.rval:
                return mapi.descr
        raise  self.BadValue(_('Invalid rating: {0}').format(self.val))
    # Enough operators to facilitate weighted averaging
    def __mul__(self, multiplier):
        return self.__class__(self.val * multiplier)
    def __iadd__(self, other):
        self.val += other.val
        return self
    def __itruediv__(self, divisor):
        self.val /= divisor
        return self
    # And sorting (Python 3.0 compatible)
    def __lt__(self, other):
        return self.val < other.val
    def __le__(self, other):
        return self.val <= other.val
    def __gt__(self, other):
        return self.val > other.val
    def __ge__(self, other):
        return self.val >= other.val
    def __eq__(self, other):
        return self.val == other.val
    def __ne__(self, other):
        return self.val != other.val

class Permanence(MappedFloat):
    MAP = (
            RATING('AA', _('Extremely Permanent'), 4.0),
            RATING('A', _('Permanent'), 3.0),
            RATING('B', _('Moderately Durable'), 2.0),
            RATING('C', _('Fugitive'), 1.0),
        )

    def __repr__(self):
        return 'Permanence({0})'.format(self.val)

class Transparency(MappedFloat):
    MAP = (
            RATING('O', _('Opaque'), 1.0),
            RATING('SO', _('Semi-opaque'), 2.0),
            RATING('ST', _('Semi-transparent'), 3.0),
            RATING('T', _('Transparent'), 4.0),
        )

    def __repr__(self):
        return 'Transparency({0})'.format(self.val)

class Colour(object):
    def __init__(self, rgb, transparency=None, permanence=None):
        self.hcvw = HCVW(rgb)
        if transparency is None:
            transparency = Transparency('O')
        if permanence is None:
            permanence = Permanence('B')
        self.transparency = transparency if isinstance(transparency, Transparency) else Transparency(transparency)
        self.permanence = permanence if isinstance(permanence, Permanence) else Permanence(permanence)
    def __str__(self):
        string = 'RGB: {0} Transparency: {1} Permanence: {2} '.format(self.rgb, self.transparency, self.permanence)
        return string + str(self.hcvw)
    def __repr__(self):
        fmt_str = 'Colour(rgb={0}, transparency={1}, permanence={2})'
        return fmt_str.format(self.rgb, self.transparency, self.permanence)
    def __getitem__(self, i):
        return self.hcvw.rgb[i]
    def __iter__(self):
        """
        Iterate over colour's rgb values
        """
        for i in range(3):
            yield self.hcvw.rgb[i]
    @property
    def rgb(self):
        return self.hcvw.rgb
    @property
    def hue_angle(self):
        return self.hcvw.hue.angle
    @property
    def hue(self):
        return self.hcvw.hue
    @property
    def hue_rgb(self):
        return RGB(*self.hcvw.hue.rgb)
    @property
    def value(self):
        return self.hcvw.value
    def value_rgb(self):
        return self.hcvw.value_rgb()
    @property
    def chroma(self):
        return self.hcvw.chroma
    @property
    def warmth(self):
        return self.hcvw.warmth
    def warmth_rgb(self):
        return (RGB_CYAN * (1 - self.hcvw.warmth) + RGB_RED * (1 + self.hcvw.warmth)) / 2
    def set_rgb(self, rgb):
        """
        Change this colours RGB values
        """
        self.hcvw = HCVW(rgb)
    def set_permanence(self, permanence):
        """
        Change this colours permanence value
        """
        self.permanence = permanence if isinstance(permanence, Permanence) else Permanence(permanence)
    def set_transparency(self, transparency):
        """
        Change this colours transparency value
        """
        self.transparency = transparency if isinstance(transparency, Transparency) else Transparency(transparency)

class NamedColour(Colour):
    def __init__(self, name, rgb, transparency=None, permanence=None):
        Colour.__init__(self, rgb, transparency=transparency, permanence=permanence)
        self.name = name
    def __repr__(self):
        fmt_str = 'NamedColour(name="{0}", rgb={1}, transparency="{2}", permanence="{3}")'
        return fmt_str.format(self.name, self.rgb, self.transparency, self.permanence)
    def __str__(self):
        return self.name
    def __len__(self):
        return len(self.name)

WHITE, MAGENTA, RED, YELLOW, GREEN, CYAN, BLUE, BLACK = [NamedColour(name, rgb) for name, rgb in zip(IDEAl_COLOUR_NAMES, IDEAL_RGB_COLOURS)]
IDEAL_COLOURS = [WHITE, MAGENTA, RED, YELLOW, GREEN, CYAN, BLUE, BLACK]

SERIES_ID = collections.namedtuple('SERIES_ID', ['maker', 'name'])

class TubeColour(NamedColour):
    def __init__(self, series, name, rgb, transparency=None, permanence=None):
        NamedColour.__init__(self, name, rgb, transparency=transparency, permanence=permanence)
        self.series = series
    def __str__(self):
        return self.name + ' ({0}: {1})'.format(*self.series.series_id)
    def __len__(self):
        return len(str(self))

class Series(object):
    class ParseError(Exception):
        pass
    def __init__(self, maker, name, colours=None):
        self.series_id = SERIES_ID(maker=maker, name=name)
        self.tube_colours = {}
        for colour in colours:
            self.add_colour(colour)
    def __cmp__(self, other):
        result = cmp(self.series_id.maker, other.series_id.maker)
        if result == 0:
            result = cmp(self.series_id.name, other.series_id.name)
        return result
    def add_colour(self, colour):
        tube_colour = TubeColour(self, name=colour.name, rgb=colour.rgb, transparency=colour.transparency, permanence=colour.permanence)
        self.tube_colours[tube_colour.name] = tube_colour
    def definition_text(self):
        # No i18n for these strings
        string = 'Manufacturer: {0}\n'.format(self.series_id.maker)
        string += 'Series: {0}\n'.format(self.series_id.name)
        for colour in self.tube_colours.values():
            string += '{0}\n'.format(repr(colour))
        return string
    @staticmethod
    def fm_definition(definition_text):
        lines = definition_text.splitlines()
        if len(lines) < 2:
            raise Series.ParseError(_('Too few lines: {0}.'.format(len(lines))))
        match = re.match('^Manufacturer:\s+(\S.*)\s*$', lines[0])
        if not match:
            raise Series.ParseError(_('Manufacturer not found.'))
        mfkr_name = match.group(1)
        match = re.match('^Series:\s+(\S.*)\s*$', lines[1])
        if not match:
            raise Series.ParseError(_('Series name not found.'))
        series_name = match.group(1)
        matcher = re.compile('(^[^:]+):\s+(RGB\([^)]+\)), (Transparency\([^)]+\)), (Permanence\([^)]+\))$')
        if len(lines) > 2 and matcher.match(lines[2]):
            # Old format
            # TODO: remove support for old tube series format
            colours = []
            for line in lines[2:]:
                match = matcher.match(line)
                if not match:
                    raise Series.ParseError(_('Badly formed definition: {0}.').format(line))
                # Old data files were wx and hence 8 bits per channel
                # so we need to convert them to 16 bist per channel
                rgb = [channel << 8 for channel in eval(match.group(2))]
                colours.append(NamedColour(match.group(1), rgb, eval(match.group(3)), eval(match.group(4))))
        else:
            try:
                colours = [eval(line) for line in lines[2:]]
            except TypeError as edata:
                raise Series.ParseError(_('Badly formed definition: {0}. ({1})').format(line, str(edata)))
        return Series(maker=mfkr_name, name=series_name, colours=colours)

BLOB = collections.namedtuple('BLOB', ['colour', 'parts'])

class MixedColour(Colour):
    def __init__(self, blobs):
        rgb = RGB_BLACK
        transparency = Transparency(0.0)
        permanence = Permanence(0.0)
        parts = 0
        for blob in blobs:
            parts += blob.parts
            rgb += blob.colour.rgb * blob.parts
            transparency += blob.colour.transparency * blob.parts
            permanence += blob.colour.permanence * blob.parts
        if parts > 0:
            rgb /= parts
            transparency /= parts
            permanence /= parts
        Colour.__init__(self, rgb=rgb, transparency=transparency, permanence=permanence)
        self.blobs = sorted(blobs, key=lambda x: x.parts, reverse=True)
    def _components_str(self):
        string = _('\nComponents:\n')
        for blob in self.blobs:
            string += _('\t{0} Part(s): {1}\n').format(blob.parts, blob.colour)
        return string
    def __str__(self):
        return _('Mixed Colour: ') + Colour.__str__(self) + self._components_str()
    def contains_colour(self, colour):
        for blob in self.blobs:
            if blob.colour == colour:
                return True
        return False

class NamedMixedColour(MixedColour):
    def __init__(self, blobs, name, notes=''):
        MixedColour.__init__(self, blobs)
        self.name = name
        self.notes = notes
    def __str__(self):
        return ('Name: "{0}" Notes: "{1}"').format(self.name, self.notes) + Colour.__str__(self) + self._components_str()

if __name__ == '__main__':
    doctest.testmod()
