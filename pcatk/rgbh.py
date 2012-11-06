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
Implement types to represent red/green/blue data as a tuple and hue as a float
'''

import collections
import math
import fractions

if __name__ == '__main__':
    import doctest
    _ = lambda x: x

IRED, IGREEN, IBLUE = range(3)

class RGB(collections.namedtuple('RGB', ['red', 'green', 'blue'])):
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
        return RGB(*(self[i] * mul.numerator / mul.denominator for i in range(3)))
    # END_DEF: __mul__

    def __div__(self, div):
        '''
        Divide all components by a value preserving component type
        >>> from fractions import Fraction
        >>> RGB(1, 2, 3) / 3
        RGB(red=0, green=0, blue=1)
        >>> RGB(7.0, 2.0, 5.0) / Fraction(2)
        RGB(red=3.5, green=1.0, blue=2.5)
        >>> RGB(Fraction(7), Fraction(2, 3), Fraction(5, 2)) / 5
        RGB(red=Fraction(7, 5), green=Fraction(2, 15), blue=Fraction(1, 2))
        '''
        return RGB(*(self[i] / div for i in range(3)))
    # END_DEF: __div__

    def __str__(self):
        return 'RGB({0}, {1}, {2})'.format(*self)
    # END_DEF: __str__

    def get_avg_value(self):
        '''
        Return the average value of the components as a fraction
        >>> RGB(0, 1, 2).get_avg_value()
        Fraction(1, 1)
        >>> RGB(7, 6, 5).get_avg_value()
        Fraction(6, 1)
        '''
        return fractions.Fraction(sum(self), 3)
    # END_DEF: get_avg_value

    def indices_value_order(self):
        '''
        Return the indices in descending order by value
        >>> RGB(1, 2, 3).indices_value_order()
        (2, 1, 0)
        >>> RGB(3, 2, 1).indices_value_order()
        (0, 1, 2)
        >>> RGB(3, 1, 2).indices_value_order()
        (0, 2, 1)
        '''
        if self[0] > self[1]:
            if self[0] > self[2]:
                if self[1] > self[2]:
                    return (0, 1, 2)
                else:
                    return (0, 2, 1)
            else:
                return (2, 0, 1)
        elif self[1] > self[2]:
            if self[0] > self[2]:
                return (1, 0, 2)
            else:
                return (1, 2, 0)
        else:
            return (2, 1, 0)
    # END_DEF: indices_value_order

    def ncomps(self):
        '''
        Return the number of non zero components
        >>> RGB(0, 0, 0).ncomps()
        0
        >>> RGB(1, 2, 3).ncomps()
        3
        >>> RGB(10, 0, 3).ncomps()
        2
        >>> RGB(0, 10, 3).ncomps()
        2
        >>> RGB(0, 10, 0).ncomps()
        1
        '''
        return sum((1 if comp else 0) for comp in self)
    # END_DEF: ncomps

    def ncomps_and_indices_value_order(self):
        '''
        Return the number of non zero components and indices in value order
        >>> RGB(0, 0, 0).ncomps_and_indices_value_order()
        (0, (2, 1, 0))
        >>> RGB(1, 2, 3).ncomps_and_indices_value_order()
        (3, (2, 1, 0))
        >>> RGB(10, 0, 3).ncomps_and_indices_value_order()
        (2, (0, 2, 1))
        >>> RGB(0, 10, 3).ncomps_and_indices_value_order()
        (2, (1, 2, 0))
        >>> RGB(0, 10, 0).ncomps_and_indices_value_order()
        (1, (1, 2, 0))
        '''
        return (self.ncomps(), self.indices_value_order())
    # END_DEF: ncomps_and_indices_value_order

    def mapped(self, map_func):
        """
        Return a copy of the RGB with components mapped by provided function
        >>> RGB(1, 2, 3).mapped(lambda x: float(x))
        RGB(red=1.0, green=2.0, blue=3.0)
        """
        return RGB(*tuple(map_func(comp) for comp in self))
    # END_DEF: mapped

    def rotated(self, delta_hue):
        """
        Return a copy of the RGB with the same value but the hue rotated
        by the specified amount and with the item types unchanged.
        NB chroma changes when less than 3 non zero components and in the
        case of 2 non zero components this change is undesirable and
        needs to be avoided by using a higher level wrapper function
        that is aware of item types and maximum allowed value per component.
        >>> RGB(1, 2, 3).rotated(Hue(0))
        RGB(red=1, green=2, blue=3)
        >>> RGB(1, 2, 3).rotated(PI_120)
        RGB(red=3, green=1, blue=2)
        >>> RGB(1, 2, 3).rotated(-PI_120)
        RGB(red=2, green=3, blue=1)
        >>> RGB(2, 0, 0).rotated(PI_60)
        RGB(red=1, green=1, blue=0)
        >>> RGB(2, 0, 0).rotated(-PI_60)
        RGB(red=1, green=0, blue=1)
        >>> RGB(1.0, 0.0, 0.0).rotated(PI_60)
        RGB(red=0.5, green=0.5, blue=0.0)
        >>> RGB(100, 0, 0).rotated(Hue(math.radians(150)))
        RGB(red=0, green=66, blue=33)
        >>> RGB(100, 0, 0).rotated(Hue(math.radians(-150)))
        RGB(red=0, green=33, blue=66)
        >>> RGB(100, 100, 0).rotated(-PI_60)
        RGB(red=100, green=50, blue=50)
        >>> RGB(100, 100, 10).rotated(-PI_60)
        RGB(red=100, green=55, blue=55)
        """
        def calc_ks(delta_hue):
            a = math.sin(delta_hue)
            b = math.sin(PI_120 - delta_hue)
            c = fractions.Fraction.from_float(a + b)
            k1 = fractions.Fraction.from_float(b * c.denominator)
            k2 = fractions.Fraction.from_float(a * c.denominator)
            return (k1, k2, c.numerator)
        # END_DEF: calc_ks
        fmul = lambda x, frac: x * frac.numerator / frac.denominator
        f = lambda c1, c2: (fmul(self[c1], k1) + fmul(self[c2], k2)) / k3
        if delta_hue > 0:
            if delta_hue > PI_120:
                k1, k2, k3 = calc_ks(delta_hue - PI_120)
                return RGB(red=f(2, 1), green=f(0, 2), blue=f(1, 0))
            else:
                k1, k2, k3 = calc_ks(delta_hue)
                return RGB(red=f(0, 2), green=f(1, 0), blue=f(2, 1))
        elif delta_hue < 0:
            if delta_hue < -PI_120:
                k1, k2, k3 = calc_ks(abs(delta_hue) - PI_120)
                return RGB(red=f(1, 2), green=f(2, 0), blue=f(0, 1))
            else:
                k1, k2, k3 = calc_ks(abs(delta_hue))
                return RGB(red=f(0, 1), green=f(1, 2), blue=f(2, 0))
        else:
            return RGB(*self)
    # END_DEF: mapped
# END_CLASS: RGB

class Hue(float):
    """
    A wrapper around float type to represent hues incorporating the
    restrictions that apply to hues.
    """
    # Both of these are needed in order to get type coherence
    ONE = fractions.Fraction(1)
    ZERO = fractions.Fraction(0)

    def __new__(cls, value):
        """
        >>> Hue(2)
        Hue(2.0)
        >>> Hue(4)
        Traceback (most recent call last):
        AssertionError
        """
        #Make sure the value is between -pi and pi
        assert value >= -math.pi and value <= math.pi
        return float.__new__(cls, value)
    # END_DEF: __init__()

    def __repr__(self):
        '''
        >>> Hue(2).__repr__()
        'Hue(2.0)'
        '''
        return '{0}({1})'.format(self.__class__.__name__, float.__repr__(self))
    # END_DEF: __repr__

    @classmethod
    def normalize(cls, hue):
        """
        >>> Hue.normalize(2)
        Hue(2.0)
        >>> Hue.normalize(4)
        Hue(-2.2831853071795862)
        >>> Hue.normalize(-4)
        Hue(2.2831853071795862)
        >>> Hue.normalize(Hue(2))
        Traceback (most recent call last):
        AssertionError
        """
        assert not isinstance(hue, Hue)
        if hue > math.pi:
            return cls(hue - 2 * math.pi)
        elif hue < -math.pi:
            return cls(hue + 2 * math.pi)
        return cls(hue)
    # END_DEF: normalize_hue

    def __neg__(self):
        """
        Change sign while maintaining type
        >>> -Hue(2)
        Hue(-2.0)
        >>> -Hue(-2)
        Hue(2.0)
        """
        return type(self)(float.__neg__(self))
    # END_DEF: __neg__

    def __abs__(self):
        """
        Get absolate value while maintaining type
        >>> abs(-Hue(2))
        Hue(2.0)
        >>> abs(Hue(-2))
        Hue(2.0)
        """
        return type(self)(float.__abs__(self))
    # END_DEF: __abs__

    def __add__(self, other):
        """
        Do addition and normalize the result
        >>> Hue(2) + 2
        Hue(-2.2831853071795862)
        >>> Hue(2) + 1
        Hue(3.0)
        """
        return self.normalize(float.__add__(self, other))
    # END_DEF: __add__

    def __radd__(self, other):
        """
        Do addition and normalize the result
        >>> 2.0 + Hue(2)
        Hue(-2.2831853071795862)
        >>> 1.0 + Hue(2)
        Hue(3.0)
        >>> 1 + Hue(2)
        Hue(3.0)
        """
        return self.normalize(float.__radd__(self, other))
    # END_DEF: __radd__

    def __sub__(self, other):
        """
        Do subtraction and normalize the result
        >>> Hue(2) - 1
        Hue(1.0)
        >>> Hue(2) - 6
        Hue(2.2831853071795862)
        """
        return self.normalize(float.__sub__(self, other))
    # END_DEF: __sub__

    def __rsub__(self, other):
        """
        Do subtraction and normalize the result
        >>> 1 - Hue(2)
        Hue(-1.0)
        >>> 6 - Hue(2)
        Hue(-2.2831853071795862)
        """
        return self.normalize(float.__rsub__(self, other))
    # END_DEF: __rsub__

    def __mul__(self, other):
        """
        Do multiplication and normalize the result
        >>> Hue(1) * 4
        Hue(-2.2831853071795862)
        >>> Hue(1) * 2.5
        Hue(2.5)
        """
        return self.normalize(float.__mul__(self, other))
    # END_DEF: __mul__

    def get_index_value_order(self):
        """
        Return the size order of channels for an rgb with my hue
        >>> import math
        >>> Hue(math.radians(45)).get_index_value_order()
        (0, 1, 2)
        >>> Hue(math.radians(105)).get_index_value_order()
        (1, 0, 2)
        >>> Hue(math.radians(165)).get_index_value_order()
        (1, 2, 0)
        >>> Hue(-math.radians(45)).get_index_value_order()
        (0, 2, 1)
        >>> Hue(-math.radians(105)).get_index_value_order()
        (2, 0, 1)
        >>> Hue(-math.radians(165)).get_index_value_order()
        (2, 1, 0)
        """
        if self >= 0:
            if self <= PI_60:
                return (IRED, IGREEN, IBLUE)
            elif self <= PI_120:
                return (IGREEN, IRED, IBLUE)
            else:
                return (IGREEN, IBLUE, IRED)
        elif self >= -PI_60:
            return (IRED, IBLUE, IGREEN)
        elif self >= -PI_120:
            return (IBLUE, IRED, IGREEN)
        else:
            return (IBLUE, IGREEN, IRED)
    # END_DEF: get_index_value_order

    def get_rgb(self, value=None):
        '''
        value is None return the RGB for the max chroma for this hue
        else return the RGB for our hue with the specified value
        NB if requested value is too big for the hue the returned value
        will deviate towards the weakest component on its way to white.
        Return: an RGB() with proportion components of type Fraction()
        >>> import math
        >>> Hue(0.0).get_rgb()
        RGB(red=Fraction(1, 1), green=Fraction(0, 1), blue=Fraction(0, 1))
        >>> Hue(math.radians(120)).get_rgb()
        RGB(red=Fraction(0, 1), green=Fraction(1, 1), blue=Fraction(0, 1))
        >>> Hue(math.radians(-120)).get_rgb()
        RGB(red=Fraction(0, 1), green=Fraction(0, 1), blue=Fraction(1, 1))
        >>> Hue(0.0).get_rgb()
        RGB(red=Fraction(1, 1), green=Fraction(0, 1), blue=Fraction(0, 1))
        >>> Hue(math.radians(60)).get_rgb().mapped(lambda x: int(round(x * 100)))
        RGB(red=100, green=100, blue=0)
        >>> Hue(math.radians(180)).get_rgb().mapped(lambda x: int(round(x * 100)))
        RGB(red=0, green=100, blue=100)
        >>> Hue(math.radians(-60)).get_rgb().mapped(lambda x: int(round(x * 100)))
        RGB(red=100, green=0, blue=100)
        >>> Hue(math.radians(-125)).get_rgb().mapped(lambda x: int(round(x * 100)))
        RGB(red=0, green=10, blue=100)
        >>> Hue(math.radians(-125)).get_rgb(fractions.Fraction(8,10)).mapped(lambda x: int(round(x * 100)))
        RGB(red=68, green=72, blue=100)
        >>> Hue(math.radians(-125)).get_rgb(fractions.Fraction(2,10)).mapped(lambda x: int(round(x * 100)))
        RGB(red=0, green=5, blue=55)
        '''
        def second(rotated_hue):
            top = math.sin(rotated_hue)
            bottom = math.sin(PI_120 - rotated_hue)
            # This step is necessary part of type cohesion
            frac = fractions.Fraction.from_float(top / bottom)
            return self.ONE * frac.numerator / frac.denominator

        io = self.get_index_value_order()
        if io == (IRED, IGREEN, IBLUE):
            rgb = RGB(red=self.ONE, green=second(self), blue=self.ZERO)
        elif io == (IGREEN, IRED, IBLUE):
            rgb = RGB(red=second(abs(self - PI_120)), green=self.ONE, blue=self.ZERO)
        elif io == (IGREEN, IBLUE, IRED):
            rgb = RGB(red=self.ZERO, green=self.ONE, blue=second(self - PI_120))
        elif io == (IRED, IBLUE, IGREEN):
            rgb = RGB(red=self.ONE, green=self.ZERO, blue=second(abs(self)))
        elif io == (IBLUE, IRED, IGREEN):
            rgb = RGB(red=second(self + PI_120), green=self.ZERO, blue=self.ONE)
        else: # io == (IBLUE, IGREEN, IRED)
            rgb = RGB(red=self.ZERO, green=second(abs(self + PI_120)), blue=self.ONE)
        if value is None:
            return rgb

        # Use fractions for performance
        ireq_value = 3 * self.ONE * value.numerator / value.denominator
        iach_value = sum(rgb)
        shortfall = ireq_value - iach_value
        if shortfall <= 0:
            return RGB(*tuple(rgb[i] * ireq_value / iach_value for i in range(3)))
        else:
            result = {io[0] : self.ONE}
            # it's simpler two work out the weakest component first
            result[io[2]] = (shortfall * self.ONE) / (2 * self.ONE - rgb[io[1]])
            result[io[1]] = rgb[io[1]] + shortfall - result[io[2]]
            return RGB(*tuple(result[i] for i in range(3)))
    # END_DEF: get_rgb

    def get_chroma_correction(self):
        """
        Return the factor required to adjust xy hypotenuse to a proportion
        of the maximum chroma for this hue.
        >>> round(Hue(0).get_chroma_correction(), 4)
        1.0
        >>> round(PI_60.get_chroma_correction(), 4)
        1.0
        >>> round(PI_120.get_chroma_correction(), 4)
        1.0
        >>> round(PI_30.get_chroma_correction(), 4)
        1.1547
        >>> round(Hue(-math.radians(150)).get_chroma_correction(), 4)
        1.1547
        """
        def func(rotated_hue):
            top = fractions.Fraction.from_float(math.sin(PI_120 - rotated_hue))
            return fractions.Fraction(top, SIN_60)
        io = self.get_index_value_order()
        if io == (IRED, IGREEN, IBLUE):
            return func(self)
        elif io == (IGREEN, IRED, IBLUE):
            return func(abs(self - PI_120))
        elif io == (IGREEN, IBLUE, IRED):
            return func(self - PI_120)
        elif io == (IRED, IBLUE, IGREEN):
            return func(abs(self))
        elif io == (IBLUE, IRED, IGREEN):
            return func(self + PI_120)
        else: # io == (IBLUE, IGREEN, IRED)
            return func(abs(self + PI_120))
    # END_DEF: get_chroma_correction
PI_30 = Hue(math.pi / 6)
PI_60 = Hue(math.pi / 3)
PI_90 = Hue(math.pi / 2)
PI_120 = PI_60 * 2
PI_150 = PI_30 * 5
# END_CLASS: Hue

# Primary Colours
RED = RGB(red=fractions.Fraction(1), green=fractions.Fraction(0), blue=fractions.Fraction(0))
GREEN = RGB(red=fractions.Fraction(0), green=fractions.Fraction(1), blue=fractions.Fraction(0))
BLUE = RGB(red=fractions.Fraction(0), green=fractions.Fraction(0), blue=fractions.Fraction(1))
# Secondary Colours
CYAN = BLUE + GREEN
MAGENTA = BLUE + RED
YELLOW = RED + GREEN
# Black and White
WHITE = RED + GREEN + BLUE
BLACK = RGB(*((fractions.Fraction(0),) * 3))
# The "ideal" palette is one that contains the full range at full strength
IDEAL_COLOURS = [WHITE, MAGENTA, RED, YELLOW, GREEN, CYAN, BLUE, BLACK]
IDEAl_COLOUR_NAMES = ['WHITE', 'MAGENTA', 'RED', 'YELLOW', 'GREEN', 'CYAN', 'BLUE', 'BLACK']

SIN_60 = fractions.Fraction.from_float(math.sin(PI_60))
SIN_120 = fractions.Fraction.from_float(math.sin(PI_120))
COS_120 = fractions.Fraction(-1, 2) # math.cos(PI_120)
X_VECTOR = (fractions.Fraction(1), COS_120, COS_120)
Y_VECTOR = (fractions.Fraction(0), SIN_120, -SIN_120)

class XY(collections.namedtuple('XY', ['x', 'y'])):
    X_VECTOR = (fractions.Fraction(1), COS_120, COS_120)
    Y_VECTOR = (fractions.Fraction(0), SIN_120, -SIN_120)
    HUE_CL = Hue

    @classmethod
    def from_rgb(cls, rgb):
        """
        Return an XY instance derived from the specified rgb.
        >>> XY.from_rgb(RGB(100, 0, 0))
        XY(x=Fraction(100, 1), y=Fraction(0, 1))
        """
        x = sum(cls.X_VECTOR[i] * rgb[i] for i in range(3))
        y = sum(cls.Y_VECTOR[i] * rgb[i] for i in range(1, 3))
        return cls(x=x, y=y)
    # END_DEF: from_rgb

    def get_hue(self):
        """
        Return an instance of  Hue() for the angle represented by these coordinates
        >>> print XY.from_rgb(RGB(100, 100, 100)).get_hue()
        None
        >>> XY.from_rgb(RGB(100, 0, 0)).get_hue() == Hue(math.radians(0.0))
        True
        >>> XY.from_rgb(RGB(0, 100, 0)).get_hue() == Hue(math.radians(120.0))
        True
        >>> XY.from_rgb(RGB(0, 0, 100)).get_hue() == Hue(math.radians(-120.0))
        True
        """
        if self.x == 0 and self.y == 0:
            return None
        return self.HUE_CL(math.atan2(self.y, self.x))
    # END_DEF: get_hue

    def get_hypot(self):
        """
        Return the hypotenuse as an instance of Fraction
        >>> XY.from_rgb(RGB(100, 0, 0)).get_hypot()
        Fraction(100, 1)
        >>> round(XY.from_rgb(RGB(100, 100, 100)).get_hypot())
        0.0
        >>> round(XY.from_rgb(RGB(0, 100, 0)).get_hypot())
        100.0
        >>> round(XY.from_rgb(RGB(0, 0, 100)).get_hypot())
        100.0
        >>> round(XY.from_rgb(RGB(0, 100, 100)).get_hypot())
        100.0
        >>> round(XY.from_rgb(RGB(0, 100, 50)).get_hypot())
        87.0
        """
        return fractions.Fraction.from_float(math.hypot(self.x, self.y))
    # END_DEF: get_hypot
# END_CLASS: XY

if __name__ == '__main__':
    doctest.testmod()
