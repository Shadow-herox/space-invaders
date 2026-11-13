"""
Weapon systems: Twin-wingtip laser cannons, plasma bolts, cooldowns,
and 3D spatial collision resolution.
"""

from dataclasses import dataclass
import math
from typing import List, Tuple, Optional
import pygame
import config
from utils.math_helpers import project_3d, rotate_2d, distance_3d


@dataclass
class LaserBolt:
    """A forward-traveling player laser bolt in 3D space."""
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    length_3d: float = 80.0
    damage: float = config.LASER_DAMAGE
    color: Tuple[int, int, int] = config.COLOR_PRIMARY


@dataclass
class EnemyPlasma:
    """An incoming enemy plasma projectile traveling toward player (z -> 0)."""
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    damage: float = 18.0
    radius: float = 14.0
    color: Tuple[int, int, int] = config.COLOR_DANGER


class WeaponSystem:
    """Manages player laser fire, enemy plasma, and 3D collision tracking."""

    def __init__(self, screen_w: int = config.SCREEN_WIDTH, screen_h: int = config.SCREEN_HEIGHT):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.player_lasers: List[LaserBolt] = []
        self.enemy_projectiles: List[EnemyPlasma] = []

        self.fire_cooldown_timer = 0.0
        self.alt_wing = False  # Alternates left and right wingtip for visual cadence

    def can_fire(self) -> bool:
        """Check whether primary weapon cooldown is ready."""
        return self.fire_cooldown_timer <= 0.0

    def fire_laser(
        self,
        aim_screen_x: float,
        aim_screen_y: float,
        player_speed: float,
        player_roll_rad: float,
        player_pitch_rad: float
    ) -> bool:
        """
        Fire dual wingtip laser bolts converging toward target crosshair 3D ray.
        Returns True if fired successfully.
        """
        if not self.can_fire():
            return False

        self.fire_cooldown_timer = config.LASER_FIRE_COOLDOWN

        # Convert screen aim coordinates to 3D target coordinates at convergence depth
        f = config.FOCAL_LENGTH
        z_conv = config.LASER_CONVERGENCE_Z
        scale_conv = f / z_conv

        target_3d_x = (aim_screen_x - (self.screen_w * 0.5)) / scale_conv
        target_3d_y = (aim_screen_y - (self.screen_h * 0.5)) / scale_conv

        # Wing offsets in cockpit space
        wing_offsets = [(-110.0, 45.0, 30.0), (110.0, 45.0, 30.0)]

        for ox, oy, oz in wing_offsets:
            # Direction vector to convergence point
            dx = target_3d_x - ox
            dy = target_3d_y - oy
            dz = z_conv - oz
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)

            speed = config.LASER_SPEED + player_speed
            vx = (dx / dist) * speed
            vy = (dy / dist) * speed
            vz = (dz / dist) * speed

            self.player_lasers.append(LaserBolt(
                x=ox, y=oy, z=oz,
                vx=vx, vy=vy, vz=vz,
                damage=config.LASER_DAMAGE,
                color=config.COLOR_PRIMARY
            ))

        return True

    def spawn_enemy_plasma(self, start_x: float, start_y: float, start_z: float, speed: float = config.ENEMY_PROJECTILE_SPEED, damage: float = 16.0):
        """Spawn an incoming hostile plasma bolt aiming near player cockpit."""
        # Aim toward cockpit origin (0, 0, 0) with slight random spread
        dx = -start_x
        dy = -start_y
        dz = -start_z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist < 1.0:
            return

        vx = (dx / dist) * speed
        vy = (dy / dist) * speed
        vz = (dz / dist) * speed # Negative velocity in Z (moving toward player)

        self.enemy_projectiles.append(EnemyPlasma(
            x=start_x, y=start_y, z=start_z,
            vx=vx, vy=vy, vz=vz,
            damage=damage,
            radius=12.0,
            color=config.COLOR_DANGER
        ))

    def update(self, dt: float, player_speed: float):
        """Advance laser bolts and enemy projectiles in 3D space."""
        if self.fire_cooldown_timer > 0.0:
            self.fire_cooldown_timer = max(0.0, self.fire_cooldown_timer - dt)

        # 1. Update Player Lasers
        alive_lasers = []
        for laser in self.player_lasers:
            laser.x += laser.vx * dt
            laser.y += laser.vy * dt
            laser.z += (laser.vz - player_speed) * dt # Moving forward relative to world

            # Keep while within view depth
            if laser.z < config.Z_MAX and laser.z > config.Z_MIN:
                alive_lasers.append(laser)
        self.player_lasers = alive_lasers

        # 2. Update Enemy Plasma Bolts
        alive_plasma = []
        for plasma in self.enemy_projectiles:
            plasma.x += plasma.vx * dt
            plasma.y += plasma.vy * dt
            # Relative speed approaching player
            plasma.z += (plasma.vz - player_speed) * dt

            if plasma.z > config.Z_MIN - 10:
                alive_plasma.append(plasma)
        self.enemy_projectiles = alive_plasma

    def draw(
        self,
        surface: pygame.Surface,
        player_roll_rad: float,
        player_pitch_rad: float
    ):
        """Render glowing 3D vector laser beams and enemy plasma pulses."""
        cx = self.screen_w * 0.5
        cy = self.screen_h * 0.5

        # 1. Draw Player Lasers (Cyan Vector Beams)
        for laser in self.player_lasers:
            # Front of beam
            sx1, sy1, scale1, vis1 = project_3d(laser.x, laser.y, laser.z, self.screen_w, self.screen_h, config.FOCAL_LENGTH)
            # Rear of beam
            rear_z = max(config.Z_MIN, laser.z - laser.length_3d)
            sx2, sy2, scale2, vis2 = project_3d(laser.x, laser.y, rear_z, self.screen_w, self.screen_h, config.FOCAL_LENGTH)

            if not (vis1 or vis2):
                continue

            rx1, ry1 = rotate_2d(sx1, sy1, -player_roll_rad, (cx, cy))
            ry1 += math.sin(player_pitch_rad) * 180.0

            rx2, ry2 = rotate_2d(sx2, sy2, -player_roll_rad, (cx, cy))
            ry2 += math.sin(player_pitch_rad) * 180.0

            width = max(2, int(scale1 * 10.0))

            # Draw outer glow and inner core
            pygame.draw.line(surface, config.COLOR_PRIMARY, (rx1, ry1), (rx2, ry2), width)
            pygame.draw.line(surface, (230, 255, 250), (rx1, ry1), (rx2, ry2), max(1, width - 2))

        # 2. Draw Enemy Plasma Bolts (Red/Amber Glowing Orbs)
        for plasma in self.enemy_projectiles:
            sx, sy, scale, vis = project_3d(plasma.x, plasma.y, plasma.z, self.screen_w, self.screen_h, config.FOCAL_LENGTH)
            if not vis:
                continue

            rx, ry = rotate_2d(sx, sy, -player_roll_rad, (cx, cy))
            ry += math.sin(player_pitch_rad) * 180.0

            r = max(3, int(plasma.radius * scale * 1.6))
            # Outer danger ring
            pygame.draw.circle(surface, config.COLOR_DANGER, (int(rx), int(ry)), r, 2)
            # Inner white/amber core
            pygame.draw.circle(surface, (255, 230, 180), (int(rx), int(ry)), max(2, r - 3))
