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
Implement types to represent red/green/blue data as a tuple and hue angle as a float
'''

import collections
import math

from pcatk import utils

if __name__ == '__main__':
    import doctest
    _ = lambda x: x

class RGB:
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

    @staticmethod
    def rotated(rgb, delta_hue_angle):
        """
        Return a copy of the RGB with the same value but the hue angle rotated
        by the specified amount and with the item types unchanged.
        NB chroma changes when less than 3 non zero components and in the
        case of 2 non zero components this change is undesirable and
        needs to be avoided by using a higher level wrapper function
        that is aware of item types and maximum allowed value per component.
        import utils
        >>> RGB.rotated((1, 2, 3), utils.Angle(0))
        (1, 2, 3)
        >>> RGB.rotated((1, 2, 3), utils.PI_120)
        (3, 1, 2)
        >>> RGB.rotated((1, 2, 3), -utils.PI_120)
        (2, 3, 1)
        >>> RGB.rotated((2, 0, 0), utils.PI_60)
        (1, 1, 0)
        >>> RGB.rotated((2, 0, 0), -utils.PI_60)
        (1, 0, 1)
        >>> RGB.rotated((1.0, 0.0, 0.0), utils.PI_60)
        (0.5, 0.5, 0.0)
        >>> RGB.rotated((100, 0, 0), utils.Angle(math.radians(150)))
        (0, 66, 33)
        >>> RGB.rotated((100, 0, 0), utils.Angle(math.radians(-150)))
        (0, 33, 66)
        >>> RGB.rotated((100, 100, 0), -utils.PI_60)
        (100, 50, 50)
        >>> RGB.rotated((100, 100, 10), -utils.PI_60)
        (100, 55, 55)
        """
        def calc_ks(delta_hue_angle):
            a = math.sin(delta_hue_angle)
            b = math.sin(utils.PI_120 - delta_hue_angle)
            c = a + b
            k1 = b / c
            k2 = a / c
            return (k1, k2)
        # END_DEF: calc_ks
        f = lambda c1, c2: int((rgb[c1] * k1 + rgb[c2] * k2) + 0.5)
        if delta_hue_angle > 0:
            if delta_hue_angle > utils.PI_120:
                k1, k2 = calc_ks(delta_hue_angle - utils.PI_120)
                return (f(2, 1), f(0, 2), f(1, 0))
            else:
                k1, k2 = calc_ks(delta_hue_angle)
                return (f(0, 2), f(1, 0), f(2, 1))
        elif delta_hue_angle < 0:
            if delta_hue_angle < -utils.PI_120:
                k1, k2 = calc_ks(abs(delta_hue_angle) - utils.PI_120)
                return (f(1, 2), f(2, 0), f(0, 1))
            else:
                k1, k2 = calc_ks(abs(delta_hue_angle))
                return (f(0, 1), f(1, 2), f(2, 0))
        else:
            return rgb
    # END_DEF: rotated
# END_CLASS: RGB

class Hue(collections.namedtuple('Hue', ['rgb', 'angle'])):
    @classmethod
    def from_angle(cls, angle, ONE=None):
        assert not math.isnan(angle) and abs(angle) <= math.pi
        def calc_other(oa):
            scale = math.sin(oa) / math.sin(utils.PI_120 - oa)
            return int(ONE * scale + 0.5)
        aha = abs(angle)
        if aha <= utils.PI_60:
            other = calc_other(aha)
            if angle >= 0:
                hue_rgb = (ONE, other, 0)
            else:
                hue_rgb = (ONE, 0, other)
        elif aha <= utils.PI_120:
            other = calc_other(utils.PI_120 - aha)
            if angle >= 0:
                hue_rgb = (other, ONE, 0)
            else:
                hue_rgb = (other, 0, ONE)
        else:
            other = calc_other(aha - utils.PI_120)
            if angle >= 0:
                hue_rgb = (0, ONE, other)
            else:
                hue_rgb = (0, other, ONE)
        return Hue(rgb=hue_rgb, angle=utils.Angle(angle))
    # END_DEF: from_angle

    def __eq__(self, other):
        return self.angle.__eq__(other.angle)
    # END_DEF: __eq__

    def __ne__(self, other):
        return self.angle.__ne__(other.angle)
    # END_DEF: __ne__

    def __lt__(self, other):
        return self.angle.__lt__(other.angle)
    # END_DEF: __lt__

    def __le__(self, other):
        return self.angle.__le__(other.angle)
    # END_DEF: __le__

    def __gt__(self, other):
        return self.angle.__gt__(other.angle)
    # END_DEF: __gt__

    def __ge__(self, other):
        return self.angle.__ge__(other.angle)
    # END_DEF: __ge__

    def rgb_with_total(self, req_total):
        '''
        return the RGB for this hue with the specified component total
        NB if requested value is too big for the hue the returned value
        will deviate towards the weakest component on its way to white.
        Return: a tuple with proportion components of the same type
        as our rgb
        '''
        cur_total = sum(self.rgb)
        shortfall = req_total - cur_total
        if shortfall == 0:
            return self.rgb
        elif shortfall < 0:
            return tuple(self.rgb[i] * req_total / cur_total for i in range(3))
        else:
            ONE = max(self.rgb)
            io = RGB.indices_value_order(self.rgb)
            result = {io[0] : ONE}
            # it's simpler two work out the weakest component first
            result[io[2]] = (shortfall * ONE) / (2 * ONE - self.rgb[io[1]])
            result[io[1]] = self.rgb[io[1]] + shortfall - result[io[2]]
            return tuple(result[i] for i in range(3))
    # END_DEF: rgb_with_total

    def rgb_with_value(self, value):
        '''
        return the RGB for this hue with the specified value
        NB if requested value is too big for the hue the returned value
        will deviate towards the weakest component on its way to white.
        Return: a tuple with proportion components of the same type
        as our rgb
        '''
        return self.rgb_with_total(int(value * max(self.rgb) * 3 + 0.5))
    # END_DEF: rgb_with_value

    def get_chroma_correction(self):
        io = RGB.indices_value_order(self.rgb)
        a = self.rgb[io[0]]
        b = self.rgb[io[1]]
        if a == b or b == 0: # avoid floating point inaccuracies near 1
            return 1.0
        return a / math.sqrt(a * a + b * b - a * b)
    # END_DEF: get_chroma_correction

    def is_grey(self):
        return math.isnan(self.angle)
    # END_DEF: is_grey
# END_CLASS: Hue

SIN_60 = math.sin(utils.PI_60)
SIN_120 = math.sin(utils.PI_120)
COS_120 = -0.5 # math.cos(utils.PI_120) is slightly out

class XY(collections.namedtuple('XY', ['x', 'y'])):
    X_VECTOR = (1.0, COS_120, COS_120)
    Y_VECTOR = (0.0, SIN_120, -SIN_120)
    ONE = None

    @classmethod
    def from_rgb(cls, rgb):
        """
        Return an XY instance derived from the specified rgb.
        >>> XY.from_rgb((100, 0, 0))
        XY(x=Fraction(100, 1), y=Fraction(0, 1))
        """
        x = sum(cls.X_VECTOR[i] * rgb[i] for i in range(3))
        y = sum(cls.Y_VECTOR[i] * rgb[i] for i in range(1, 3))
        return cls(x=x, y=y)
    # END_DEF: from_rgb

    def get_hue(self):
        if self.x == 0.0 and self.y == 0.0:
            return Hue(rgb=(self.ONE, self.ONE, self.ONE), angle=float('nan'))
        else:
            return Hue.from_angle(math.atan2(self.y, self.x), self.ONE)
    # END_DEF: get_hue

    def get_hypot(self):
        """
        Return the hypotenuse as an instance of Fraction
        >>> XY.from_rgb((100, 0, 0)).get_hypot()
        Fraction(100, 1)
        >>> round(XY.from_rgb((100, 100, 100)).get_hypot())
        0.0
        >>> round(XY.from_rgb((0, 100, 0)).get_hypot())
        100.0
        >>> round(XY.from_rgb((0, 0, 100)).get_hypot())
        100.0
        >>> round(XY.from_rgb((0, 100, 100)).get_hypot())
        100.0
        >>> round(XY.from_rgb((0, 100, 50)).get_hypot())
        87.0
        """
        return math.hypot(self.x, self.y)
    # END_DEF: get_hypot
# END_CLASS: XY

if __name__ == '__main__':
    doctest.testmod()
