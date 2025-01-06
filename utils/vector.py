import math
import random
from typing import Union, Tuple, Optional

from .math import clip, sign

def cross_product_3d(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    )

class Vector2D:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f'V2({self.x:.2f}, {self.y:.2f})'
    
    def __repr__(self) -> str:
        return f'V({self.x:.1f}, {self.y:.1f})'
    
    def __add__(self, other: Union[float, 'Vector2D']) -> 'Vector2D':
        if isinstance(other, float):
            return Vector2D(self.x + other, self.y + other)
        else:
            return Vector2D(self.x + other.x, self.y + other.y)
    
    def __neg__(self) -> 'Vector2D':
        return Vector2D(-self.x, -self.y)
    
    def __sub__(self, other: Union[float, 'Vector2D']) -> 'Vector2D':
        return self + (-other)
    
    def __mul__(self, other: float) -> 'Vector2D':
        return Vector2D(self.x * other, self.y * other)
    
    def __truediv__(self, other: float) -> 'Vector2D':
        return Vector2D(self.x / other, self.y / other)
    
    def __iadd__(self, other: Union[float, 'Vector2D']) -> 'Vector2D':
        return self + other
    
    def __isub__(self, other: Union[float, 'Vector2D']) -> 'Vector2D':
        return self - other
    
    def tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)
    
    def tuple_3d(self) -> Tuple[float, float, float]:
        return (self.x, self.y, 0)

    def mag(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)
    
    def mag_square(self) -> float:
        return self.x**2 + self.y**2

    def normalize(self, ignore_zero_mag: bool = False) -> 'Vector2D':
        if ignore_zero_mag and self.mag() == 0:
            return Vector2D.origin()
        return self / self.mag()
    
    def clip(self, min_mag: float, max_mag: float) -> 'Vector2D':
        norm = self.normalize()
        mag = self.mag()
        if mag < min_mag:
            return norm * min_mag
        if mag > max_mag:
            return norm * max_mag
        return norm * mag
    
    def dist(self, other: 'Vector2D') -> float:
        return (self - other).mag()

    def dot(self, other: 'Vector2D') -> float:
        return self.x * other.x + self.y * other.y

    def angle(self, other: 'Vector2D') -> float:
        cos_theta = self.dot(other) / (self.mag() * other.mag())
        plane_direction = self.x * other.y - self.y * other.x
        # from A X B (check cross_product_3d()) -> using right hand rule
        # negative -> into the plane (clockwise)
        # positive -> out of the plane (anti clockwise)
        return math.acos(clip(cos_theta, -1, 1)) * sign(plane_direction) # clipping to avoid math domain error due to precision issue

    def rotate(self, angle: float, origin: Optional['Vector2D'] = None) -> 'Vector2D':
        # angle is in radians
        # negative -> clockwise
        # positive -> anti clockwise
        vec = self
        if origin != None:
            vec = vec - origin
        vec_x = vec.x * math.cos(angle) - vec.y * math.sin(angle)
        vec_y = vec.x * math.sin(angle) + vec.y * math.cos(angle)
        vec = Vector2D(vec_x, vec_y)
        if origin != None:
            vec = vec + origin
        return vec
    
    def component_parallel(self, other: 'Vector2D') -> 'Vector2D':
        other_dir = other.normalize()
        return other_dir * self.dot(other_dir)
    
    def component_perpendicular(self, other: 'Vector2D') -> 'Vector2D':
        return self - self.component_parallel(other)
    
    def copy(self) -> 'Vector2D':
        return Vector2D(self.x, self.y)

    @staticmethod
    def from_tuple(coord: Tuple[float, float]) -> 'Vector2D':
        return Vector2D(coord[0], coord[1])

    @staticmethod
    def origin() -> 'Vector2D':
        return Vector2D(0, 0)
    
    @staticmethod
    def random() -> 'Vector2D':
        return Vector2D(2 * random.random() - 1, 2 * random.random() - 1)
    
    @staticmethod
    def left(mag: float = 1.0) -> 'Vector2D':
        return Vector2D(-mag, 0)
    
    @staticmethod
    def right(mag: float = 1.0) -> 'Vector2D':
        return Vector2D(mag, 0)
    
    @staticmethod
    def up(mag: float = 1.0) -> 'Vector2D':
        return Vector2D(0, mag)
    
    @staticmethod
    def down(mag: float = 1.0) -> 'Vector2D':
        return Vector2D(0, -mag)
    
    @staticmethod
    def deg2rad(val: float) -> float:
        return (val * math.pi) / 180
    
    @staticmethod
    def rad2deg(val: float) -> float:
        return (val * 180) / math.pi