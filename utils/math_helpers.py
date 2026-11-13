"""
Mathematical and spatial helper functions for flight physics, vector operations,
smoothing, and 3D-to-2D perspective projection.
"""

import math
from typing import Tuple, List, Optional
import numpy as np


def clamp(val: float, min_val: float, max_val: float) -> float:
    """Clamp a scalar value within [min_val, max_val]."""
    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def exp_decay(current: float, target: float, decay_rate: float, dt: float) -> float:
    """
    Frame-rate independent exponential decay smoothing.
    decay_rate: Higher means faster response (e.g., 10-25).
    """
    return target + (current - target) * math.exp(-decay_rate * dt)


def remap(val: float, in_min: float, in_max: float, out_min: float, out_max: float, clamp_out: bool = True) -> float:
    """Linearly remap a value from input range to output range."""
    if abs(in_max - in_min) < 1e-7:
        return out_min
    t = (val - in_min) / (in_max - in_min)
    if clamp_out:
        t = clamp(t, 0.0, 1.0)
    return out_min + t * (out_max - out_min)


def normalize_angle(angle_rad: float) -> float:
    """Normalize an angle in radians to [-pi, pi]."""
    while angle_rad > math.pi:
        angle_rad -= 2.0 * math.pi
    while angle_rad < -math.pi:
        angle_rad += 2.0 * math.pi
    return angle_rad


def distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Euclidean distance in 2D space."""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """Euclidean distance in 3D space."""
    return math.sqrt(
        (p2[0] - p1[0]) ** 2 +
        (p2[1] - p1[1]) ** 2 +
        (p2[2] - p1[2]) ** 2
    )


def project_3d(
    x: float,
    y: float,
    z: float,
    screen_width: int,
    screen_height: int,
    focal_length: float = 640.0,
    z_min: float = 20.0
) -> Tuple[float, float, float, bool]:
    """
    Perspective projection from 3D camera space to 2D screen coordinates.
    Returns (screen_x, screen_y, scale, is_visible).
    """
    if z < z_min:
        return (screen_width * 0.5, screen_height * 0.5, 0.0, False)

    scale = focal_length / z
    screen_x = (screen_width * 0.5) + (x * scale)
    screen_y = (screen_height * 0.5) + (y * scale)

    # Check whether within reasonable field of view bounds
    margin = 300
    is_visible = (
        -margin <= screen_x <= screen_width + margin and
        -margin <= screen_y <= screen_height + margin
    )

    return (screen_x, screen_y, scale, is_visible)


def rotate_2d(
    x: float,
    y: float,
    angle_rad: float,
    origin: Tuple[float, float] = (0.0, 0.0)
) -> Tuple[float, float]:
    """Rotate a 2D point around an origin by angle_rad."""
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    dx = x - origin[0]
    dy = y - origin[1]
    rx = origin[0] + (dx * cos_a - dy * sin_a)
    ry = origin[1] + (dx * sin_a + dy * cos_a)
    return (rx, ry)


def rotate_points_2d(
    points: List[Tuple[float, float]],
    angle_rad: float,
    origin: Tuple[float, float] = (0.0, 0.0)
) -> List[Tuple[float, float]]:
    """Rotate a list of 2D points around an origin."""
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    ox, oy = origin
    rotated = []
    for px, py in points:
        dx = px - ox
        dy = py - oy
        rx = ox + (dx * cos_a - dy * sin_a)
        ry = oy + (dx * sin_a + dy * cos_a)
        rotated.append((rx, ry))
    return rotated


def world_to_radar(
    world_x: float,
    world_z: float,
    max_range: float,
    radar_radius: float,
    radar_center: Tuple[int, int]
) -> Tuple[int, int, bool]:
    """
    Project world horizontal offset (x) and forward depth (z) onto a circular radar.
    Returns (radar_x, radar_y, is_in_range).
    """
    dist = math.hypot(world_x, world_z)
    if dist > max_range:
        # Clamp to radar edge
        ratio = radar_radius / dist
        rx = radar_center[0] + int(world_x * ratio)
        ry = radar_center[1] - int(world_z * ratio)
        return (rx, ry, False)

    ratio = radar_radius / max_range
    rx = radar_center[0] + int(world_x * ratio)
    ry = radar_center[1] - int(world_z * ratio)
    return (rx, ry, True)
