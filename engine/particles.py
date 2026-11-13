"""
High-performance 3D vector particle engine:
Warp starfield, explosive debris, laser impact sparks, and deflector shield mesh.
"""

from dataclasses import dataclass
import math
import random
from typing import List, Tuple, Optional
import pygame
import numpy as np
import config
from utils.math_helpers import project_3d, rotate_2d, clamp


@dataclass
class Star3D:
    """A single star in the 3D warp field."""
    x: float
    y: float
    z: float
    prev_screen_x: float = 0.0
    prev_screen_y: float = 0.0
    brightness: float = 1.0


@dataclass
class Particle3D:
    """A 3D physical particle with velocity, lifespan, and color."""
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    life: float          # Remaining lifespan in seconds
    max_life: float
    color: Tuple[int, int, int]
    size: float
    is_spark: bool = False


class ParticleSystem:
    """Manages 3D starfield, explosion FX, sparks, and energy shield visuals."""

    def __init__(self, screen_w: int = config.SCREEN_WIDTH, screen_h: int = config.SCREEN_HEIGHT):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.stars: List[Star3D] = []
        self.particles: List[Particle3D] = []
        self.shield_hit_timer: float = 0.0
        self.damage_flash_timer: float = 0.0

        self._init_stars(num_stars=180)

    def _init_stars(self, num_stars: int = 180):
        """Seed 3D starfield."""
        self.stars.clear()
        for _ in range(num_stars):
            # Spread widely across X and Y
            sx = random.uniform(-1600, 1600)
            sy = random.uniform(-1000, 1000)
            sz = random.uniform(config.Z_MIN + 50, config.Z_MAX)
            bright = random.uniform(0.4, 1.0)
            self.stars.append(Star3D(x=sx, y=sy, z=sz, brightness=bright))

    def trigger_shield_impact(self):
        """Trigger shield ripple visual timer."""
        self.shield_hit_timer = 0.35

    def trigger_damage_flash(self):
        """Trigger red cockpit damage flash."""
        self.damage_flash_timer = 0.25

    def spawn_explosion(self, x: float, y: float, z: float, count: int = 40, is_boss: bool = False):
        """Spawn a multi-layer 3D vector burst explosion."""
        speed_mult = 1.6 if is_boss else 1.0
        colors = [
            config.COLOR_PRIMARY,
            config.COLOR_EMERALD,
            config.COLOR_WARNING,
            config.COLOR_DANGER,
            (255, 240, 200)
        ]

        # 1. Shrapnel debris
        for _ in range(count):
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(-math.pi * 0.5, math.pi * 0.5)
            speed = random.uniform(180, 550) * speed_mult

            vx = speed * math.cos(phi) * math.cos(theta)
            vy = speed * math.cos(phi) * math.sin(theta)
            vz = speed * math.sin(phi) + random.uniform(-80, 80)
            life = random.uniform(0.4, 0.9)
            color = random.choice(colors)
            size = random.uniform(2.5, 5.0)

            self.particles.append(Particle3D(
                x=x, y=y, z=z,
                vx=vx, vy=vy, vz=vz,
                life=life, max_life=life,
                color=color, size=size,
                is_spark=False
            ))

        # 2. Fast sparks
        for _ in range(count // 2):
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(-math.pi * 0.5, math.pi * 0.5)
            speed = random.uniform(400, 850) * speed_mult
            vx = speed * math.cos(phi) * math.cos(theta)
            vy = speed * math.cos(phi) * math.sin(theta)
            vz = speed * math.sin(phi)
            life = random.uniform(0.2, 0.45)
            self.particles.append(Particle3D(
                x=x, y=y, z=z,
                vx=vx, vy=vy, vz=vz,
                life=life, max_life=life,
                color=(255, 255, 220), size=1.5,
                is_spark=True
            ))

    def spawn_hit_sparks(self, x: float, y: float, z: float, count: int = 12):
        """Spawn compact directional sparks on laser hit."""
        for _ in range(count):
            vx = random.uniform(-250, 250)
            vy = random.uniform(-250, 250)
            vz = random.uniform(-100, 300)
            life = random.uniform(0.12, 0.3)
            self.particles.append(Particle3D(
                x=x, y=y, z=z,
                vx=vx, vy=vy, vz=vz,
                life=life, max_life=life,
                color=config.COLOR_PRIMARY, size=2.0,
                is_spark=True
            ))

    def update(
        self,
        dt: float,
        player_speed: float,
        player_roll_rad: float,
        player_pitch_rad: float
    ):
        """Update 3D positions of stars and active particles."""
        # Update timers
        if self.shield_hit_timer > 0:
            self.shield_hit_timer = max(0.0, self.shield_hit_timer - dt)
        if self.damage_flash_timer > 0:
            self.damage_flash_timer = max(0.0, self.damage_flash_timer - dt)

        # 1. Update Warp Starfield
        # Forward flight moves stars backwards in Z relative to camera
        dz = player_speed * dt
        for star in self.stars:
            star.z -= dz
            # Wrap around when star passes near plane
            if star.z < config.Z_MIN:
                star.z = config.Z_MAX - random.uniform(0, 100)
                star.x = random.uniform(-1600, 1600)
                star.y = random.uniform(-1000, 1000)

        # 2. Update 3D Particles
        alive_particles = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue

            # Apply velocity and slight drag
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.z += (p.vz - player_speed * 0.4) * dt # Camera moves forward relative to debris
            p.vx *= (1.0 - 0.5 * dt)
            p.vy *= (1.0 - 0.5 * dt)
            p.vz *= (1.0 - 0.5 * dt)

            if p.z > config.Z_MIN:
                alive_particles.append(p)

        self.particles = alive_particles

    def draw(
        self,
        surface: pygame.Surface,
        player_roll_rad: float,
        player_pitch_rad: float,
        shield_active: bool,
        shield_energy: float
    ):
        """Render starfield, vector debris, shield matrix, and damage overlays."""
        cx = self.screen_w * 0.5
        cy = self.screen_h * 0.5

        # 1. Draw Warp Stars
        for star in self.stars:
            sx, sy, scale, vis = project_3d(star.x, star.y, star.z, self.screen_w, self.screen_h, config.FOCAL_LENGTH)
            if not vis:
                continue

            # Rotate star position according to player roll
            rx, ry = rotate_2d(sx, sy, -player_roll_rad, (cx, cy))
            # Shift vertically with pitch
            ry += math.sin(player_pitch_rad) * 180.0

            # Calculate brightness and motion streak length
            z_factor = 1.0 - (star.z / config.Z_MAX)
            intensity = int(clamp(255 * star.brightness * z_factor, 40, 255))
            star_col = (intensity, int(intensity * 0.95), int(intensity * 0.9))

            streak_len = max(1.0, (1.0 - (star.z / config.Z_MAX)) * 12.0)
            if streak_len > 2.5:
                # Radial streak away from center
                angle_from_center = math.atan2(ry - cy, rx - cx)
                ex = rx + math.cos(angle_from_center) * streak_len
                ey = ry + math.sin(angle_from_center) * streak_len
                pygame.draw.line(surface, star_col, (rx, ry), (ex, ey), 1)
            else:
                surface.set_at((int(rx), int(ry)), star_col)

        # 2. Draw 3D Explosion / Spark Particles
        for p in self.particles:
            sx, sy, scale, vis = project_3d(p.x, p.y, p.z, self.screen_w, self.screen_h, config.FOCAL_LENGTH)
            if not vis:
                continue

            rx, ry = rotate_2d(sx, sy, -player_roll_rad, (cx, cy))
            ry += math.sin(player_pitch_rad) * 180.0

            life_ratio = p.life / p.max_life
            render_size = max(1.0, p.size * scale * 1.5 * life_ratio)
            # Alpha / intensity fade
            fade_col = (
                int(p.color[0] * life_ratio),
                int(p.color[1] * life_ratio),
                int(p.color[2] * life_ratio)
            )

            if p.is_spark:
                pygame.draw.circle(surface, fade_col, (int(rx), int(ry)), max(1, int(render_size)))
            else:
                # Vector diamond / poly debris
                s = max(2.0, render_size)
                pts = [
                    (rx, ry - s),
                    (rx + s, ry),
                    (rx, ry + s),
                    (rx - s, ry)
                ]
                pygame.draw.polygon(surface, fade_col, pts, 1)

        # 3. Draw Deflector Shield Matrix Overlay
        if shield_active or self.shield_hit_timer > 0:
            self._draw_shield_bubble(surface, shield_active, shield_energy)

        # 4. Cockpit Damage Flash
        if self.damage_flash_timer > 0:
            alpha = int(140 * (self.damage_flash_timer / 0.25))
            flash_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            flash_surf.fill((255, 30, 40, alpha))
            surface.blit(flash_surf, (0, 0))

    def _draw_shield_bubble(self, surface: pygame.Surface, is_active: bool, energy: float):
        """Draw glowing cyan/blue deflector shield arc & hexagonal ripple."""
        cx = self.screen_w * 0.5
        cy = self.screen_h * 0.5
        shield_surf = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)

        radius = int(min(self.screen_w, self.screen_h) * 0.44)
        alpha = 110 if is_active else int(200 * (self.shield_hit_timer / 0.35))
        shield_color = (0, 200, 255, alpha)

        # Outer arc
        pygame.draw.circle(shield_surf, shield_color, (int(cx), int(cy)), radius, 2)
        pygame.draw.circle(shield_surf, (0, 240, 255, alpha // 2), (int(cx), int(cy)), radius - 8, 1)

        # Hexagonal grid pattern in center
        hex_r = 45
        for hx in range(-2, 3):
            for hy in range(-2, 3):
                px = cx + hx * hex_r * 1.732 + (hy % 2) * (hex_r * 0.866)
                py = cy + hy * hex_r * 1.5
                if math.hypot(px - cx, py - cy) < radius - 20:
                    pts = []
                    for i in range(6):
                        angle = math.pi / 6 + i * math.pi / 3
                        pts.append((px + hex_r * 0.5 * math.cos(angle), py + hex_r * 0.5 * math.sin(angle)))
                    pygame.draw.polygon(shield_surf, (0, 210, 255, alpha // 3), pts, 1)

        surface.blit(shield_surf, (0, 0))
