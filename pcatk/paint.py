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

from pcatk import rgbh

if __name__ == '__main__':
    import doctest
    _ = lambda x: x

ZERO = 0
BITS_PER_CHANNEL = 16
ONE = (1 << BITS_PER_CHANNEL) - 1
TWO = ONE * 2
THREE = ONE * 3

class RGB(collections.namedtuple('RGB', ['red', 'green', 'blue']), rgbh.RGB):
    __slots__ = ()

    def __add__(self, other):
        '''
        Add two RGB values together
        >>> RGB(1, 2, 3) + RGB(7, 5, 3)
        RGB(red=8, green=7, blue=6)
        >>> RGB(1.0, 2.0, 3.0) + RGB(7.0, 5.0, 3.0)
        RGB(red=8.0, green=7.0, blue=6.0)
        '''
        return RGB(red=self.red + other.red, green=self.green + other.green, blue=self.blue + other.blue)
    # END_DEF: __add__

    def __sub__(self, other):
        '''
        Subtract one RGB value from another
        >>> RGB(1, 2, 3) - RGB(7, 5, 3)
        RGB(red=-6, green=-3, blue=0)
        >>> RGB(1.0, 2.0, 3.0) - RGB(7.0, 5.0, 3.0)
        RGB(red=-6.0, green=-3.0, blue=0.0)
        '''
        return RGB(red=self.red - other.red, green=self.green - other.green, blue=self.blue - other.blue)
    # END_DEF: __sub__

    def __mul__(self, mul):
        '''
        Multiply all components by a fraction preserving component type
        >>> from fractions import Fraction
        >>> RGB(1, 2, 3) * Fraction(3)
        RGB(red=3, green=6, blue=9)
        >>> RGB(7.0, 2.0, 5.0) * Fraction(3)
        RGB(red=21.0, green=6.0, blue=15.0)
        >>> RGB(Fraction(7), Fraction(2, 3), Fraction(5, 2)) * Fraction(3, 2)
        RGB(red=Fraction(21, 2), green=Fraction(1, 1), blue=Fraction(15, 4))
        '''
        return RGB(*(int(self[i] * mul + 0.5) for i in range(3)))
    # END_DEF: __mul__

    def __div__(self, div):
        '''
        Divide all components by a value
        >>> from fractions import Fraction
        >>> RGB(1, 2, 3) / 3
        RGB(red=0, green=0, blue=1)
        >>> RGB(7.0, 2.0, 5.0) / Fraction(2)
        RGB(red=3.5, green=1.0, blue=2.5)
        >>> RGB(Fraction(7), Fraction(2, 3), Fraction(5, 2)) / 5
        RGB(red=Fraction(7, 5), green=Fraction(2, 15), blue=Fraction(1, 2))
        '''
        return RGB(*(int(self[i] / div + 0.5) for i in range(3)))
    # END_DEF: __div__

    def __str__(self):
        return 'RGB({0}, {1}, {2})'.format(*self)
    # END_DEF: __str__

    def get_value(self):
        return fractions.Fraction(sum(self), THREE)
    # END_DEF: get_value

    @staticmethod
    def rotated(rgb, delta_hue_angle):
        return RGB(*rgbh.RGB.rotated(rgb, delta_hue_angle))
    # END_DEF: rotated
# END_CLASS: RGB

class Hue(rgbh.Hue):
    ONE = ONE

# Primary Colours
RGB_RED = RGB(red=ONE, green=ZERO, blue=ZERO)
RGB_GREEN = RGB(red=ZERO, green=ONE, blue=ZERO)
RGB_BLUE = RGB(red=ZERO, green=ZERO, blue=ONE)
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
        self.warmth = fractions.Fraction.from_float(xy.x / ONE)
        self.hue = Hue.from_angle(xy.get_angle())
        self.chroma = xy.get_hypot() * self.hue.get_chroma_correction() / ONE
    # END_DEF: __init__

    def hue_rgb_for_value(self, value=None):
        if value is None:
            # i.e. same hue and value but without any unnecessary grey
            value = self.value
        return RGB(*self.hue.rgb_with_value(value))
    # END_DEF: hue_rgb_for_value

    def chroma_side(self):
        # Is it darker or lighter than max chroma for the hue?
        if sum(self.rgb) > sum(self.hue.rgb):
            return WHITE
        else:
            return BLACK
    # END_DEF: chroma_side

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
    # END_DEF: get_rotated_rgb

    def __str__(self):
        string = '(HUE = {0}, '.format(self.hue.rgb)
        string += 'VALUE = {0}, '.format(round(self.value, 2))
        string += 'CHROMA = {0}, '.format(round(self.chroma, 2))
        string += 'WARMTH = {0})'.format(round(self.warmth, 2))
        return string
    # END_DEF: __str__()
# END_CLASS: HCVW

RATING = collections.namedtuple('RATING', ['abbrev', 'descr', 'rval'])

class MappedFloat(object):
    class BadValue(Exception): pass
    MAP = None

    def __init__(self, ival=0.0):
        if isinstance(ival, (str, unicode)):
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
    # END_DEF: __init__

    def __str__(self):
        rval = round(self.val, 0)
        for mapi in self.MAP:
            if rval == mapi.rval:
                return mapi.abbrev
        raise  self.BadValue(_('Invalid rating: {0}').format(self.val))
    # END_DEF: __str__

    # Enough operators to facilitate weighted averaging
    def __mul__(self, multiplier):
        return self.__class__(self.val * multiplier)
    # END_DEF: __mul__

    def __iadd__(self, other):
        self.val += other.val
        return self
    # END_DEF: __iadd__

    def __idiv__(self, divisor):
        self.val /= divisor
        return self
    # END_DEF: __idiv__

    # And sorting (Python 3.0 compatible)
    def __lt__(self, other):
        return self.val < other.val
    # END_DEF: __lt__

    def __le__(self, other):
        return self.val <= other.val
    # END_DEF: __le__

    def __gt__(self, other):
        return self.val > other.val
    # END_DEF: __gt__

    def __ge__(self, other):
        return self.val >= other.val
    # END_DEF: __ge__

    def __eq__(self, other):
        return self.val == other.val
    # END_DEF: __eq__

    def __ne__(self, other):
        return self.val != other.val
    # END_DEF: __ne__
# END_CLASS: MappedFloat

class Permanence(MappedFloat):
    MAP = (
            RATING('AA', _('Extremely Permanent'), 4.0),
            RATING('A', _('Permanent'), 3.0),
            RATING('B', _('Moderately Durable'), 2.0),
            RATING('C', _('Fugitive'), 1.0),
        )

    def __repr__(self):
        return 'Permanence({0})'.format(self.val)
    # END_DEF: __repr__
# END_CLASS: Permanence

class Transparency(MappedFloat):
    MAP = (
            RATING('O', _('Opaque'), 1.0),
            RATING('SO', _('Semi-opaque'), 2.0),
            RATING('ST', _('Semi-transparent'), 3.0),
            RATING('T', _('Transparent'), 4.0),
        )

    def __repr__(self):
        return 'Transparency({0})'.format(self.val)
    # END_DEF: __repr__
# END_CLASS: Transparency

class Colour(object):
    def __init__(self, rgb, transparency=None, permanence=None):
        self.hcvw = HCVW(rgb)
        if transparency is None:
            transparency = Transparency('O')
        if permanence is None:
            permanence = Permanence('B')
        self.transparency = transparency if isinstance(transparency, Transparency) else Transparency(transparency)
        self.permanence = permanence if isinstance(permanence, Permanence) else Permanence(permanence)
    # END_DEF: __init

    def __str__(self):
        string = 'RGB: {0} Transparency: {1} Permanence: {2} '.format(self.rgb, self.transparency, self.permanence)
        return string + str(self.hcvw)
    # END_DEF: __str__

    def __repr__(self):
        fmt_str = 'Colour(rgb={0}, transparency={1}, permanence={2})'
        return fmt_str.format(self.rgb, self.transparency, self.permanence)
    # END_DEF: __repr__

    def __getitem__(self, i):
        return self.hcvw.rgb[i]
    # END_DEF: __getitem__

    def __iter__(self):
        """
        Iterate over colour's rgb values
        """
        for i in range(3):
            yield self.hcvw.rgb[i]
    # END_DEF: __iter__

    @property
    def rgb(self):
        return self.hcvw.rgb
    # END_DEF: rgb

    @property
    def hue_angle(self):
        return self.hcvw.hue.angle
    # END_DEF: hue_angle

    @property
    def hue(self):
        return self.hcvw.hue
    # END_DEF: hue

    @property
    def hue_rgb(self):
        return RGB(*self.hcvw.hue.rgb)
    # END_DEF: hue_rgb

    @property
    def value(self):
        return self.hcvw.value
    # END_DEF: value

    def value_rgb(self):
        return RGB_WHITE * self.hcvw.value
    # END_DEF: value_rgb

    @property
    def chroma(self):
        return self.hcvw.chroma
    # END_DEF: chroma

    @property
    def warmth(self):
        return self.hcvw.warmth
    # END_DEF: warmth

    def warmth_rgb(self):
        return (RGB_CYAN * (1 - self.hcvw.warmth) + RGB_RED * (1 + self.hcvw.warmth)) / 2
    # END_DEF: warmth_rgb

    def set_rgb(self, rgb):
        """
        Change this colours RGB values
        """
        self.hcvw = HCVW(rgb)
    # END_DEF: set_rgb

    def set_permanence(self, permanence):
        """
        Change this colours permanence value
        """
        self.permanence = permanence if isinstance(permanence, Permanence) else Permanence(permanence)
    # END_DEF: set_permanence

    def set_transparency(self, transparency):
        """
        Change this colours transparency value
        """
        self.transparency = transparency if isinstance(transparency, Transparency) else Transparency(transparency)
    # END_DEF: set_transparency
# END_CLASS: Colour

class NamedColour(Colour):
    def __init__(self, name, rgb, transparency=None, permanence=None):
        Colour.__init__(self, rgb, transparency=transparency, permanence=permanence)
        self.name = name
    # END_DEF: __init__

    def __repr__(self):
        fmt_str = 'NamedColour(name="{0}", rgb={1}, transparency="{2}", permanence="{3}")'
        return fmt_str.format(self.name, self.rgb, self.transparency, self.permanence)
    # END_DEF: __repr__

    def __str__(self):
        return self.name
    # END_DEF: __str__

    def __len__(self):
        return len(self.name)
    # END_DEF: __len__
# END_CLASS: NamedColour

WHITE, MAGENTA, RED, YELLOW, GREEN, CYAN, BLUE, BLACK = [NamedColour(name, rgb) for name, rgb in zip(IDEAl_COLOUR_NAMES, IDEAL_RGB_COLOURS)]
IDEAL_COLOURS = [WHITE, MAGENTA, RED, YELLOW, GREEN, CYAN, BLUE, BLACK]

SERIES_ID = collections.namedtuple('SERIES_ID', ['maker', 'name'])

class TubeColour(NamedColour):
    def __init__(self, series, name, rgb, transparency=None, permanence=None):
        NamedColour.__init__(self, name, rgb, transparency=transparency, permanence=permanence)
        self.series = series
    # END_DEF: __init__

    def __str__(self):
        return self.name + ' ({0}: {1})'.format(*self.series.series_id)
    # END_DEF: __str__

    def __len__(self):
        return len(str(self))
    # END_DEF: __len__
# END_CLASS: TubeColour

class Series(object):
    class ParseError(Exception):
        pass
    # END_CLASS: ParseError

    def __init__(self, maker, name, colours=None):
        self.series_id = SERIES_ID(maker=maker, name=name)
        self.tube_colours = {}
        for colour in colours:
            self.add_colour(colour)
    # END_DEF: __init__

    def add_colour(self, colour):
        tube_colour = TubeColour(self, name=colour.name, rgb=colour.rgb, transparency=colour.transparency, permanence=colour.permanence)
        self.tube_colours[tube_colour.name] = tube_colour
    # END_DEF: add_colour

    def definition_text(self):
        # No i18n for these strings
        string = 'Manufacturer: {0}\n'.format(self.series_id.maker)
        string += 'Series: {0}\n'.format(self.series_id.name)
        for colour in self.tube_colours.values():
            string += '{0}\n'.format(repr(colour))
        return string
    # END_DEF: definition_text

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
            colours = [eval(line) for line in lines[2:]]
        return Series(maker=mfkr_name, name=series_name, colours=colours)
    # END_DEF: fm_definition
# END_CLASS: Series

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
    # END_DEF: __init__

    def _components_str(self):
        string = _('\nComponents:\n')
        for blob in self.blobs:
            string += _('\t{0} Part(s): {1}\n').format(blob.parts, blob.colour)
        return string
    # END_DEF: _components_str

    def __str__(self):
        return _('Mixed Colour: ') + Colour.__str__(self) + self._components_str()
    # END_DEF: __str__

    def contains_colour(self, colour):
        for blob in self.blobs:
            if blob.colour == colour:
                return True
        return False
    # END_DEF: contains_colour
# END_CLASS: MixedColour

class NamedMixedColour(MixedColour):
    def __init__(self, blobs, name, notes=''):
        MixedColour.__init__(self, blobs)
        self.name = name
        self.notes = notes
    # END_DEF: __init__

    def __str__(self):
        return ('Name: "{0}" Notes: "{1}"').format(self.name, self.notes) + Colour.__str__(self) + self._components_str()
    # END_DEF: __str__

if __name__ == '__main__':
    doctest.testmod()
