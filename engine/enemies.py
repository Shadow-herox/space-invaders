"""
3D-to-2D Perspective Projected Enemy Drone Waves & Combat AI.
Generates multi-tier drone formations with wireframe rendering, evasive maneuvers,
and plasma turret attacks.
"""

from dataclasses import dataclass
from enum import Enum
import math
import random
from typing import List, Tuple, Optional
import pygame
import config
from utils.math_helpers import project_3d, rotate_2d, distance_3d, clamp


class EnemyType(Enum):
    SCOUT = "SCOUT"
    INTERCEPTOR = "INTERCEPTOR"
    DREADNOUGHT = "DREADNOUGHT"


@dataclass
class EnemyDrone:
    """A 3D autonomous combat drone."""
    drone_type: EnemyType
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float

    health: float
    max_health: float
    radius_3d: float
    points: int

    # AI Timers & Dynamics
    shoot_cooldown: float = 2.0
    evade_timer: float = 0.0
    bank_angle: float = 0.0
    oscillation_phase: float = 0.0
    is_locked_on: bool = False

    # 2D Screen Cache
    screen_x: float = 0.0
    screen_y: float = 0.0
    screen_scale: float = 1.0
    is_visible: bool = False


# Wireframe 3D relative models (Vertices & Edges)
# Scout Drone (Sleek Delta Wing)
SCOUT_VERTICES = [
    (0.0, 0.0, 35.0),    # 0: Nose
    (-40.0, 10.0, -25.0),# 1: Left Wingtip
    (40.0, 10.0, -25.0), # 2: Right Wingtip
    (0.0, -18.0, -15.0), # 3: Dorsal Fin
    (0.0, 8.0, -20.0),   # 4: Engine Core
]
SCOUT_EDGES = [
    (0, 1), (0, 2), (1, 4), (2, 4), (0, 3), (3, 4), (1, 3), (2, 3)
]

# Interceptor Drone (Heavy Twin-Boom Fighter)
INTERCEPTOR_VERTICES = [
    (0.0, 0.0, 45.0),    # 0: Center Cockpit
    (-55.0, 12.0, -15.0),# 1: Left Wing Gun
    (55.0, 12.0, -15.0), # 2: Right Wing Gun
    (-30.0, -22.0, -30.0),# 3: Left Stabilizer
    (30.0, -22.0, -30.0), # 4: Right Stabilizer
    (0.0, 15.0, -35.0),  # 5: Central Thruster
    (-55.0, 12.0, 10.0), # 6: Left Cannon Barrel
    (55.0, 12.0, 10.0),  # 7: Right Cannon Barrel
]
INTERCEPTOR_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 5), (1, 6), (2, 7), (0, 5), (3, 4)
]

# Dreadnought Boss (Massive Hexagonal Flagship)
DREADNOUGHT_VERTICES = [
    (0.0, 0.0, 75.0),    # 0: Prow
    (-95.0, -30.0, 0.0), # 1: Left Upper Flank
    (95.0, -30.0, 0.0),  # 2: Right Upper Flank
    (-95.0, 30.0, -30.0),# 3: Left Lower Flank
    (95.0, 30.0, -30.0), # 4: Right Lower Flank
    (0.0, -50.0, -40.0), # 5: Top Command Bridge
    (0.0, 50.0, -50.0),  # 6: Bottom Reactor
    (0.0, 0.0, -60.0),   # 7: Main Thruster Cluster
]
DREADNOUGHT_EDGES = [
    (0, 1), (0, 2), (1, 2), (1, 3), (2, 4), (3, 4),
    (0, 5), (1, 5), (2, 5), (0, 6), (3, 6), (4, 6),
    (5, 7), (6, 7), (3, 7), (4, 7)
]


class EnemyManager:
    """Coordinates enemy wave spawning, flight AI, combat weapons, and rendering."""

    def __init__(self, screen_w: int = config.SCREEN_WIDTH, screen_h: int = config.SCREEN_HEIGHT):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.drones: List[EnemyDrone] = []
        self.wave_number: int = 1
        self.wave_timer: float = 0.0
        self.is_boss_wave: bool = False
        self.wave_clear_banner_timer: float = 0.0

        self.spawn_wave(wave_index=1)

    def spawn_wave(self, wave_index: int):
        """Spawn a tactical formation of drones based on wave number."""
        self.wave_number = wave_index
        self.is_boss_wave = (wave_index % 5 == 0)
        self.wave_clear_banner_timer = 2.5

        if self.is_boss_wave:
            # Spawn Boss Dreadnought + 2 Escort Scouts
            boss = EnemyDrone(
                drone_type=EnemyType.DREADNOUGHT,
                x=0.0, y=-40.0, z=config.Z_MAX - 100,
                vx=0.0, vy=0.0, vz=-120.0,
                health=280.0 + (wave_index * 25.0),
                max_health=280.0 + (wave_index * 25.0),
                radius_3d=85.0,
                points=1200 + (wave_index * 150),
                shoot_cooldown=1.2
            )
            self.drones.append(boss)

            # 2 Escorts
            for ox in [-220.0, 220.0]:
                self.drones.append(EnemyDrone(
                    drone_type=EnemyType.SCOUT,
                    x=ox, y=60.0, z=config.Z_MAX + 50,
                    vx=0.0, vy=0.0, vz=-180.0,
                    health=30.0, max_health=30.0,
                    radius_3d=35.0, points=200,
                    shoot_cooldown=2.5
                ))
        else:
            # Standard wave formations
            num_enemies = min(7, 3 + (wave_index // 2))
            formation_type = random.choice(["V_SHAPE", "ECHELON", "PINCER"])

            for i in range(num_enemies):
                z_base = config.Z_MAX - (i * 120.0)

                if formation_type == "V_SHAPE":
                    side = -1 if i % 2 == 0 else 1
                    ox = side * (i + 1) * 90.0
                    oy = (i % 3) * 35.0 - 20.0
                elif formation_type == "ECHELON":
                    ox = -250.0 + (i * 100.0)
                    oy = -80.0 + (i * 40.0)
                else: # PINCER
                    side = -1 if i < num_enemies // 2 else 1
                    ox = side * (180.0 + (i % 3) * 60.0)
                    oy = ((i % 2) * 2 - 1) * 70.0

                # Interceptor probability increases with wave
                is_interceptor = (i >= 2 and (wave_index >= 2))
                dtype = EnemyType.INTERCEPTOR if is_interceptor else EnemyType.SCOUT
                hp = 55.0 if is_interceptor else 25.0
                pts = 350 if is_interceptor else 150

                drone = EnemyDrone(
                    drone_type=dtype,
                    x=ox, y=oy, z=z_base,
                    vx=0.0, vy=0.0,
                    vz=-random.uniform(140.0, 220.0),
                    health=hp,
                    max_health=hp,
                    radius_3d=45.0 if is_interceptor else 35.0,
                    points=pts,
                    shoot_cooldown=random.uniform(1.8, 3.5),
                    oscillation_phase=random.uniform(0, math.pi * 2)
                )
                self.drones.append(drone)

    def update(
        self,
        dt: float,
        player_speed: float,
        player_x: float,
        player_y: float,
        weapons_sys
    ):
        """Update enemy trajectories, AI maneuvers, shooting, and cleanups."""
        if self.wave_clear_banner_timer > 0.0:
            self.wave_clear_banner_timer = max(0.0, self.wave_clear_banner_timer - dt)

        alive_drones = []
        for drone in self.drones:
            drone.oscillation_phase += dt * 2.2

            # 1. AI Flight Dynamics & Evasive Maneuvers
            if drone.drone_type == EnemyType.SCOUT:
                # Fast sinusoidal weaving
                drone.x += math.cos(drone.oscillation_phase) * 140.0 * dt
                drone.y += math.sin(drone.oscillation_phase * 0.7) * 70.0 * dt
                drone.bank_angle = math.cos(drone.oscillation_phase) * 0.45
            elif drone.drone_type == EnemyType.INTERCEPTOR:
                # Strafing pursuit
                dx = -drone.x
                drone.x += clamp(dx, -80.0, 80.0) * dt
                drone.y += math.sin(drone.oscillation_phase * 0.5) * 40.0 * dt
                drone.bank_angle = clamp(dx * 0.005, -0.3, 0.3)
            elif drone.drone_type == EnemyType.DREADNOUGHT:
                # Slow imposing advance with subtle hover sway
                drone.x += math.sin(drone.oscillation_phase * 0.4) * 45.0 * dt
                drone.y += math.cos(drone.oscillation_phase * 0.3) * 25.0 * dt

            # Forward relative movement
            drone.z += (drone.vz - player_speed * 0.4) * dt

            # 2. Combat AI: Plasma Shooting
            drone.shoot_cooldown -= dt
            if drone.shoot_cooldown <= 0.0 and drone.z > 200.0 and drone.z < 1600.0:
                if drone.drone_type == EnemyType.SCOUT:
                    weapons_sys.spawn_enemy_plasma(drone.x, drone.y, drone.z, damage=14.0)
                    drone.shoot_cooldown = random.uniform(2.5, 4.0)
                elif drone.drone_type == EnemyType.INTERCEPTOR:
                    # Dual wing shot
                    weapons_sys.spawn_enemy_plasma(drone.x - 30, drone.y, drone.z, damage=18.0)
                    weapons_sys.spawn_enemy_plasma(drone.x + 30, drone.y, drone.z, damage=18.0)
                    drone.shoot_cooldown = random.uniform(1.8, 3.0)
                elif drone.drone_type == EnemyType.DREADNOUGHT:
                    # Heavy cannon barrage
                    weapons_sys.spawn_enemy_plasma(drone.x - 50, drone.y - 15, drone.z, damage=24.0)
                    weapons_sys.spawn_enemy_plasma(drone.x + 50, drone.y - 15, drone.z, damage=24.0)
                    drone.shoot_cooldown = 1.1

            # 3. Check boundaries: Wrap around if passed behind player without being destroyed
            if drone.z <= config.Z_MIN:
                # Recycled to rear of wave
                drone.z = config.Z_MAX + random.uniform(50, 300)
                drone.x = random.uniform(-400, 400)
                drone.y = random.uniform(-200, 200)

            alive_drones.append(drone)

        self.drones = alive_drones

        # Spawn next wave when all drones are cleared
        if len(self.drones) == 0:
            self.spawn_wave(self.wave_number + 1)

    def draw(
        self,
        surface: pygame.Surface,
        player_roll_rad: float,
        player_pitch_rad: float
    ):
        """Render 3D wireframe drones sorted back-to-front (painter's algorithm)."""
        cx = self.screen_w * 0.5
        cy = self.screen_h * 0.5

        # Sort drones by Z depth (furthest first)
        sorted_drones = sorted(self.drones, key=lambda d: d.z, reverse=True)

        for drone in sorted_drones:
            # 1. Perspective project drone origin
            sx, sy, scale, vis = project_3d(drone.x, drone.y, drone.z, self.screen_w, self.screen_h, config.FOCAL_LENGTH)
            drone.screen_x = sx
            drone.screen_y = sy
            drone.screen_scale = scale
            drone.is_visible = vis

            if not vis:
                continue

            # Select model vertices & edges
            if drone.drone_type == EnemyType.SCOUT:
                verts_3d = SCOUT_VERTICES
                edges = SCOUT_EDGES
                base_color = config.COLOR_WARNING
                core_color = config.COLOR_DANGER
            elif drone.drone_type == EnemyType.INTERCEPTOR:
                verts_3d = INTERCEPTOR_VERTICES
                edges = INTERCEPTOR_EDGES
                base_color = config.COLOR_DANGER
                core_color = (255, 120, 140)
            else: # DREADNOUGHT
                verts_3d = DREADNOUGHT_VERTICES
                edges = DREADNOUGHT_EDGES
                base_color = (255, 60, 160)
                core_color = (255, 230, 100)

            # Project and transform 3D model vertices
            projected_pts = []
            cos_b = math.cos(drone.bank_angle)
            sin_b = math.sin(drone.bank_angle)

            for vx, vy, vz in verts_3d:
                # Bank roll rotation on local model
                rx_local = vx * cos_b - vy * sin_b
                ry_local = vx * sin_b + vy * cos_b
                rz_local = vz

                # World position of vertex
                wx = drone.x + rx_local
                wy = drone.y + ry_local
                wz = drone.z + rz_local

                psx, psy, pscale, pvis = project_3d(wx, wy, wz, self.screen_w, self.screen_h, config.FOCAL_LENGTH)

                # Cockpit attitude transform
                prx, pry = rotate_2d(psx, psy, -player_roll_rad, (cx, cy))
                pry += math.sin(player_pitch_rad) * 180.0

                projected_pts.append((prx, pry))

            # Draw wireframe edges
            line_width = max(1, int(scale * 3.2))
            for e1, e2 in edges:
                if e1 < len(projected_pts) and e2 < len(projected_pts):
                    p1 = projected_pts[e1]
                    p2 = projected_pts[e2]
                    pygame.draw.line(surface, base_color, p1, p2, line_width)

            # Center engine glow core
            center_rx, center_ry = rotate_2d(sx, sy, -player_roll_rad, (cx, cy))
            center_ry += math.sin(player_pitch_rad) * 180.0
            core_r = max(2, int(scale * 12.0))
            pygame.draw.circle(surface, core_color, (int(center_rx), int(center_ry)), core_r)

            # Health bar above drone if damaged
            if drone.health < drone.max_health:
                bar_w = max(24, int(scale * 80.0))
                bar_h = 3
                bar_x = center_rx - bar_w // 2
                bar_y = center_ry - max(15, int(scale * 45.0))
                hp_pct = max(0.0, drone.health / drone.max_health)

                pygame.draw.rect(surface, (40, 50, 60), (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(surface, config.COLOR_DANGER, (bar_x, bar_y, int(bar_w * hp_pct), bar_h))
