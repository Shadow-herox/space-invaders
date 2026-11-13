"""
2D Tactical Radar Minimap.
Renders circular forward-looking tactical radar with continuous 360-degree sweep,
range rings, and threat-level blip classification.
"""

import math
from typing import List, Tuple
import pygame
import config
from utils.math_helpers import world_to_radar


class TacticalRadar:
    """Circular forward radar scope."""

    def __init__(
        self,
        center_x: int = config.SCREEN_WIDTH - 110,
        center_y: int = 110,
        radius: int = config.RADAR_RADIUS,
        max_range: float = config.RADAR_MAX_RANGE
    ):
        self.cx = center_x
        self.cy = center_y
        self.radius = radius
        self.max_range = max_range
        self.sweep_angle = 0.0

    def update(self, dt: float):
        """Advance the radar sweep beam angle."""
        self.sweep_angle = (self.sweep_angle + config.RADAR_SWEEP_SPEED * dt) % (2 * math.pi)

    def draw(
        self,
        surface: pygame.Surface,
        drones: List,
        font: pygame.font.Font,
        locked_drone=None
    ):
        """Render radar housing, rings, sweep line, and threat blips."""
        radar_surf = pygame.Surface((self.radius * 2 + 30, self.radius * 2 + 30), pygame.SRCALPHA)
        rcx = self.radius + 15
        rcy = self.radius + 15

        # 1. Background scope glass
        pygame.draw.circle(radar_surf, (10, 16, 24, 210), (rcx, rcy), self.radius)

        # 2. Concentric Range Rings (500m, 1000m, 2000m)
        ring_col = (0, 180, 140, 70)
        pygame.draw.circle(radar_surf, ring_col, (rcx, rcy), int(self.radius * 0.33), 1)
        pygame.draw.circle(radar_surf, ring_col, (rcx, rcy), int(self.radius * 0.66), 1)
        pygame.draw.circle(radar_surf, config.COLOR_PRIMARY, (rcx, rcy), self.radius, 1)

        # Crosshairs
        pygame.draw.line(radar_surf, ring_col, (rcx - self.radius, rcy), (rcx + self.radius, rcy), 1)
        pygame.draw.line(radar_surf, ring_col, (rcx, rcy - self.radius), (rcx, rcy + self.radius), 1)

        # 3. Rotating Phosphor Sweep Line
        sweep_x = rcx + math.cos(self.sweep_angle) * self.radius
        sweep_y = rcy + math.sin(self.sweep_angle) * self.radius
        pygame.draw.line(radar_surf, (0, 255, 180, 180), (rcx, rcy), (sweep_x, sweep_y), 2)

        # 4. Draw Threat Blips
        for drone in drones:
            rx, ry, in_range = world_to_radar(
                world_x=drone.x,
                world_z=drone.z,
                max_range=self.max_range,
                radar_radius=self.radius - 4,
                radar_center=(rcx, rcy)
            )

            # Determine color by threat
            if drone.drone_type.value == "DREADNOUGHT":
                b_col = (255, 60, 180)
                b_size = 4
            elif drone.drone_type.value == "INTERCEPTOR":
                b_col = config.COLOR_DANGER
                b_size = 3
            else:
                b_col = config.COLOR_WARNING
                b_size = 2

            pygame.draw.circle(radar_surf, b_col, (rx, ry), b_size)

            # Highlight locked target on radar
            if locked_drone is not None and drone == locked_drone:
                pygame.draw.circle(radar_surf, config.COLOR_EMERALD, (rx, ry), b_size + 4, 1)

        # 5. Player Own-Ship Icon (Cyan Chevron at center)
        pygame.draw.polygon(radar_surf, config.COLOR_PRIMARY, [
            (rcx, rcy - 5),
            (rcx + 4, rcy + 4),
            (rcx, rcy + 2),
            (rcx - 4, rcy + 4)
        ])

        # Blit radar surface onto main display
        surface.blit(radar_surf, (self.cx - rcx, self.cy - rcy))

        # Header Tag
        tag = font.render("TACTICAL RADAR // 2.0 KM", True, config.COLOR_PRIMARY_DIM)
        surface.blit(tag, (self.cx - self.radius, self.cy - self.radius - 16))
