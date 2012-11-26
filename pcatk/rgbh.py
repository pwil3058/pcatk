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
Implement types to represent red/green/blue data as a tuple and hue_angle as a float
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

    @staticmethod
    def get_avg_value(rgb):
        '''
        Return the average value of the components as a fraction
        >>> RGB.get_avg_value(RGB(0, 1, 2))
        Fraction(1, 1)
        >>> RGB.get_avg_value(RGB(7, 6, 5))
        Fraction(6, 1)
        >>> RGB.get_avg_value(RGB(7, 6, 6))
        Fraction(19, 3)
        >>> RGB.get_avg_value((7, 6, 6, 56))
        Fraction(19, 3)
        '''
        return fractions.Fraction(sum(rgb[:3]), 3)
    # END_DEF: get_avg_value

    @staticmethod
    def indices_value_order(rgb):
        '''
        Return the indices in descending order by value
        >>> RGB.indices_value_order((1, 2, 3))
        (2, 1, 0)
        >>> RGB.indices_value_order((3, 2, 1))
        (0, 1, 2)
        >>> RGB.indices_value_order((3, 1, 2))
        (0, 2, 1)
        '''
        if rgb[0] > rgb[1]:
            if rgb[0] > rgb[2]:
                if rgb[1] > rgb[2]:
                    return (0, 1, 2)
                else:
                    return (0, 2, 1)
            else:
                return (2, 0, 1)
        elif rgb[1] > rgb[2]:
            if rgb[0] > rgb[2]:
                return (1, 0, 2)
            else:
                return (1, 2, 0)
        else:
            return (2, 1, 0)
    # END_DEF: indices_value_order

    @staticmethod
    def ncomps(rgb):
        '''
        Return the number of non zero components
        >>> RGB.ncomps((0, 0, 0))
        0
        >>> RGB.ncomps((1, 2, 3))
        3
        >>> RGB.ncomps((10, 0, 3))
        2
        >>> RGB.ncomps((0, 10, 3))
        2
        >>> RGB.ncomps((0, 10, 0))
        1
        '''
        return sum((1 if comp else 0) for comp in rgb)
    # END_DEF: ncomps

    @staticmethod
    def ncomps_and_indices_value_order(rgb):
        '''
        Return the number of non zero components and indices in value order
        >>> RGB.ncomps_and_indices_value_order((0, 0, 0))
        (0, (2, 1, 0))
        >>> RGB.ncomps_and_indices_value_order((1, 2, 3))
        (3, (2, 1, 0))
        >>> RGB.ncomps_and_indices_value_order((10, 0, 3))
        (2, (0, 2, 1))
        >>> RGB.ncomps_and_indices_value_order((0, 10, 3))
        (2, (1, 2, 0))
        >>> RGB.ncomps_and_indices_value_order((0, 10, 0))
        (1, (1, 2, 0))
        '''
        return (RGB.ncomps(rgb), RGB.indices_value_order(rgb))
    # END_DEF: ncomps_and_indices_value_order

    def mapped(self, map_func):
        """
        Return a copy of the RGB with components mapped by provided function
        >>> RGB(1, 2, 3).mapped(lambda x: float(x))
        RGB(red=1.0, green=2.0, blue=3.0)
        """
        return RGB(*tuple(map_func(comp) for comp in self))
    # END_DEF: mapped

    @staticmethod
    def rotated(rgb, delta_hue_angle):
        """
        Return a copy of the RGB with the same value but the hue_angle rotated
        by the specified amount and with the item types unchanged.
        NB chroma changes when less than 3 non zero components and in the
        case of 2 non zero components this change is undesirable and
        needs to be avoided by using a higher level wrapper function
        that is aware of item types and maximum allowed value per component.
        >>> RGB.rotated((1, 2, 3), HueAngle(0))
        RGB(red=1, green=2, blue=3)
        >>> RGB.rotated((1, 2, 3), PI_120)
        RGB(red=3, green=1, blue=2)
        >>> RGB.rotated((1, 2, 3), -PI_120)
        RGB(red=2, green=3, blue=1)
        >>> RGB.rotated((2, 0, 0), PI_60)
        RGB(red=1, green=1, blue=0)
        >>> RGB.rotated((2, 0, 0), -PI_60)
        RGB(red=1, green=0, blue=1)
        >>> RGB.rotated((1.0, 0.0, 0.0), PI_60)
        RGB(red=0.5, green=0.5, blue=0.0)
        >>> RGB.rotated((100, 0, 0), HueAngle(math.radians(150)))
        RGB(red=0, green=66, blue=33)
        >>> RGB.rotated((100, 0, 0), HueAngle(math.radians(-150)))
        RGB(red=0, green=33, blue=66)
        >>> RGB.rotated((100, 100, 0), -PI_60)
        RGB(red=100, green=50, blue=50)
        >>> RGB.rotated((100, 100, 10), -PI_60)
        RGB(red=100, green=55, blue=55)
        """
        def calc_ks(delta_hue_angle):
            a = math.sin(delta_hue_angle)
            b = math.sin(PI_120 - delta_hue_angle)
            c = fractions.Fraction.from_float(a + b)
            k1 = fractions.Fraction.from_float(b * c.denominator)
            k2 = fractions.Fraction.from_float(a * c.denominator)
            return (k1, k2, c.numerator)
        # END_DEF: calc_ks
        fmul = lambda x, frac: x * frac.numerator / frac.denominator
        f = lambda c1, c2: (fmul(rgb[c1], k1) + fmul(rgb[c2], k2)) / k3
        if delta_hue_angle > 0:
            if delta_hue_angle > PI_120:
                k1, k2, k3 = calc_ks(delta_hue_angle - PI_120)
                return RGB(red=f(2, 1), green=f(0, 2), blue=f(1, 0))
            else:
                k1, k2, k3 = calc_ks(delta_hue_angle)
                return RGB(red=f(0, 2), green=f(1, 0), blue=f(2, 1))
        elif delta_hue_angle < 0:
            if delta_hue_angle < -PI_120:
                k1, k2, k3 = calc_ks(abs(delta_hue_angle) - PI_120)
                return RGB(red=f(1, 2), green=f(2, 0), blue=f(0, 1))
            else:
                k1, k2, k3 = calc_ks(abs(delta_hue_angle))
                return RGB(red=f(0, 1), green=f(1, 2), blue=f(2, 0))
        else:
            return RGB(*rgb)
    # END_DEF: rotated
# END_CLASS: RGB

class HueAngle(float):
    """
    A wrapper around float type to represent hue_angles incorporating the
    restrictions that apply to hue_angles.
    """
    # Both of these are needed in order to get type coherence
    ONE = fractions.Fraction(1)
    ZERO = fractions.Fraction(0)

    def __new__(cls, value):
        """
        >>> HueAngle(2)
        HueAngle(2.0)
        >>> HueAngle(4)
        Traceback (most recent call last):
        AssertionError
        """
        #Make sure the value is between -pi and pi
        assert value >= -math.pi and value <= math.pi
        return float.__new__(cls, value)
    # END_DEF: __init__()

    def __repr__(self):
        '''
        >>> HueAngle(2).__repr__()
        'HueAngle(2.0)'
        '''
        return '{0}({1})'.format(self.__class__.__name__, float.__repr__(self))
    # END_DEF: __repr__

    @classmethod
    def normalize(cls, hue_angle):
        """
        >>> HueAngle.normalize(2)
        HueAngle(2.0)
        >>> HueAngle.normalize(4)
        HueAngle(-2.2831853071795862)
        >>> HueAngle.normalize(-4)
        HueAngle(2.2831853071795862)
        >>> HueAngle.normalize(HueAngle(2))
        Traceback (most recent call last):
        AssertionError
        """
        assert not isinstance(hue_angle, HueAngle)
        if hue_angle > math.pi:
            return cls(hue_angle - 2 * math.pi)
        elif hue_angle < -math.pi:
            return cls(hue_angle + 2 * math.pi)
        return cls(hue_angle)
    # END_DEF: normalize_hue

    def __neg__(self):
        """
        Change sign while maintaining type
        >>> -HueAngle(2)
        HueAngle(-2.0)
        >>> -HueAngle(-2)
        HueAngle(2.0)
        """
        return type(self)(float.__neg__(self))
    # END_DEF: __neg__

    def __abs__(self):
        """
        Get absolate value while maintaining type
        >>> abs(-HueAngle(2))
        HueAngle(2.0)
        >>> abs(HueAngle(-2))
        HueAngle(2.0)
        """
        return type(self)(float.__abs__(self))
    # END_DEF: __abs__

    def __add__(self, other):
        """
        Do addition and normalize the result
        >>> HueAngle(2) + 2
        HueAngle(-2.2831853071795862)
        >>> HueAngle(2) + 1
        HueAngle(3.0)
        """
        return self.normalize(float.__add__(self, other))
    # END_DEF: __add__

    def __radd__(self, other):
        """
        Do addition and normalize the result
        >>> 2.0 + HueAngle(2)
        HueAngle(-2.2831853071795862)
        >>> 1.0 + HueAngle(2)
        HueAngle(3.0)
        >>> 1 + HueAngle(2)
        HueAngle(3.0)
        """
        return self.normalize(float.__radd__(self, other))
    # END_DEF: __radd__

    def __sub__(self, other):
        """
        Do subtraction and normalize the result
        >>> HueAngle(2) - 1
        HueAngle(1.0)
        >>> HueAngle(2) - 6
        HueAngle(2.2831853071795862)
        """
        return self.normalize(float.__sub__(self, other))
    # END_DEF: __sub__

    def __rsub__(self, other):
        """
        Do subtraction and normalize the result
        >>> 1 - HueAngle(2)
        HueAngle(-1.0)
        >>> 6 - HueAngle(2)
        HueAngle(-2.2831853071795862)
        """
        return self.normalize(float.__rsub__(self, other))
    # END_DEF: __rsub__

    def __mul__(self, other):
        """
        Do multiplication and normalize the result
        >>> HueAngle(1) * 4
        HueAngle(-2.2831853071795862)
        >>> HueAngle(1) * 2.5
        HueAngle(2.5)
        """
        return self.normalize(float.__mul__(self, other))
    # END_DEF: __mul__

    @staticmethod
    def get_index_value_order(hue_angle):
        """
        Return the size order of channels for an rgb with my hue_angle
        >>> import math
        >>> HueAngle.get_index_value_order(math.radians(45))
        (0, 1, 2)
        >>> HueAngle.get_index_value_order(math.radians(105))
        (1, 0, 2)
        >>> HueAngle.get_index_value_order(math.radians(165))
        (1, 2, 0)
        >>> HueAngle.get_index_value_order(-math.radians(45))
        (0, 2, 1)
        >>> HueAngle.get_index_value_order(-math.radians(105))
        (2, 0, 1)
        >>> HueAngle.get_index_value_order(-math.radians(165))
        (2, 1, 0)
        """
        if hue_angle >= 0:
            if hue_angle <= PI_60:
                return (IRED, IGREEN, IBLUE)
            elif hue_angle <= PI_120:
                return (IGREEN, IRED, IBLUE)
            elif hue_angle <= PI_180:
                return (IGREEN, IBLUE, IRED)
            else:
                raise  ValueError('Should be in range -pi to +p')
        elif hue_angle >= -PI_60:
            return (IRED, IBLUE, IGREEN)
        elif hue_angle >= -PI_120:
            return (IBLUE, IRED, IGREEN)
        elif hue_angle >= -PI_180:
            return (IBLUE, IGREEN, IRED)
        else:
            raise ValueError('Should be in range -pi to +p')
    # END_DEF: get_index_value_order

    @classmethod
    def get_rgb(cls, hue_angle, value=None):
        '''
        value is None return the RGB for the max chroma for this hue_angle
        else return the RGB for our hue_angle with the specified value
        NB if requested value is too big for the hue_angle the returned value
        will deviate towards the weakest component on its way to white.
        Return: an RGB() with proportion components of type Fraction()
        >>> import math
        >>> HueAngle.get_rgb(0.0)
        RGB(red=Fraction(1, 1), green=Fraction(0, 1), blue=Fraction(0, 1))
        >>> HueAngle.get_rgb(math.radians(120))
        RGB(red=Fraction(0, 1), green=Fraction(1, 1), blue=Fraction(0, 1))
        >>> HueAngle.get_rgb(math.radians(-120))
        RGB(red=Fraction(0, 1), green=Fraction(0, 1), blue=Fraction(1, 1))
        >>> HueAngle.get_rgb(HueAngle(0.0))
        RGB(red=Fraction(1, 1), green=Fraction(0, 1), blue=Fraction(0, 1))
        >>> HueAngle.get_rgb(math.radians(60)).mapped(lambda x: int(round(x * 100)))
        RGB(red=100, green=100, blue=0)
        >>> HueAngle.get_rgb(math.radians(180)).mapped(lambda x: int(round(x * 100)))
        RGB(red=0, green=100, blue=100)
        >>> HueAngle.get_rgb(math.radians(-60)).mapped(lambda x: int(round(x * 100)))
        RGB(red=100, green=0, blue=100)
        >>> HueAngle.get_rgb(math.radians(-125)).mapped(lambda x: int(round(x * 100)))
        RGB(red=0, green=10, blue=100)
        >>> HueAngle.get_rgb(math.radians(-125), fractions.Fraction(8,10)).mapped(lambda x: int(round(x * 100)))
        RGB(red=68, green=72, blue=100)
        >>> HueAngle.get_rgb(math.radians(-125), fractions.Fraction(2,10)).mapped(lambda x: int(round(x * 100)))
        RGB(red=0, green=5, blue=55)
        '''
        def second(rotated_hue_angle):
            top = math.sin(rotated_hue_angle)
            bottom = math.sin(PI_120 - rotated_hue_angle)
            # This step is necessary part of type cohesion
            frac = fractions.Fraction.from_float(top / bottom)
            return cls.ONE * frac.numerator / frac.denominator

        io = cls.get_index_value_order(hue_angle)
        if io == (IRED, IGREEN, IBLUE):
            rgb = RGB(red=cls.ONE, green=second(hue_angle), blue=cls.ZERO)
        elif io == (IGREEN, IRED, IBLUE):
            rgb = RGB(red=second(abs(hue_angle - PI_120)), green=cls.ONE, blue=cls.ZERO)
        elif io == (IGREEN, IBLUE, IRED):
            rgb = RGB(red=cls.ZERO, green=cls.ONE, blue=second(hue_angle - PI_120))
        elif io == (IRED, IBLUE, IGREEN):
            rgb = RGB(red=cls.ONE, green=cls.ZERO, blue=second(abs(hue_angle)))
        elif io == (IBLUE, IRED, IGREEN):
            rgb = RGB(red=second(hue_angle + PI_120), green=cls.ZERO, blue=cls.ONE)
        else: # io == (IBLUE, IGREEN, IRED)
            rgb = RGB(red=cls.ZERO, green=second(abs(hue_angle + PI_120)), blue=cls.ONE)
        if value is None:
            return rgb

        # Use fractions for performance
        ireq_value = 3 * cls.ONE * value.numerator / value.denominator
        iach_value = sum(rgb)
        shortfall = ireq_value - iach_value
        if shortfall <= 0:
            return RGB(*tuple(rgb[i] * ireq_value / iach_value for i in range(3)))
        else:
            result = {io[0] : cls.ONE}
            # it's simpler two work out the weakest component first
            result[io[2]] = (shortfall * cls.ONE) / (2 * cls.ONE - rgb[io[1]])
            result[io[1]] = rgb[io[1]] + shortfall - result[io[2]]
            return RGB(*tuple(result[i] for i in range(3)))
    # END_DEF: get_rgb

    def get_chroma_correction(self):
        """
        Return the factor required to adjust xy hypotenuse to a proportion
        of the maximum chroma for this hue_angle.
        >>> round(HueAngle(0).get_chroma_correction(), 4)
        1.0
        >>> round(PI_60.get_chroma_correction(), 4)
        1.0
        >>> round(PI_120.get_chroma_correction(), 4)
        1.0
        >>> round(PI_30.get_chroma_correction(), 4)
        1.1547
        >>> round(HueAngle(-math.radians(150)).get_chroma_correction(), 4)
        1.1547
        """
        def func(rotated_hue_angle):
            top = fractions.Fraction.from_float(math.sin(PI_120 - rotated_hue_angle))
            return fractions.Fraction(top, SIN_60)
        io = self.get_index_value_order(self)
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
PI_30 = HueAngle(math.pi / 6)
PI_60 = HueAngle(math.pi / 3)
PI_90 = HueAngle(math.pi / 2)
PI_120 = PI_60 * 2
PI_150 = PI_30 * 5
PI_180 = HueAngle(math.pi)
# END_CLASS: HueAngle

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
    HUE_CL = HueAngle

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

    def get_hue_angle(self):
        """
        Return an instance of  HueAngle() for the angle represented by these coordinates
        >>> print XY.from_rgb(RGB(100, 100, 100)).get_hue_angle()
        None
        >>> XY.from_rgb(RGB(100, 0, 0)).get_hue_angle() == HueAngle(math.radians(0.0))
        True
        >>> XY.from_rgb(RGB(0, 100, 0)).get_hue_angle() == HueAngle(math.radians(120.0))
        True
        >>> XY.from_rgb(RGB(0, 0, 100)).get_hue_angle() == HueAngle(math.radians(-120.0))
        True
        """
        if self.x == 0 and self.y == 0:
            return float('nan')
        return self.HUE_CL(math.atan2(self.y, self.x))
    # END_DEF: get_hue_angle

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
