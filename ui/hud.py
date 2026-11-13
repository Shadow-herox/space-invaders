"""
Aviation Heads-Up Display (HUD):
Artificial Horizon, Moving Pitch Ladder, Dynamic Targeting Reticle,
Segmented Throttle Bar, Hull/Shield Integrity Gauges, and Telemetry Badges.
"""

import math
from typing import Optional, List
import pygame
import config
from utils.math_helpers import rotate_2d, rotate_points_2d, clamp


class AviationHUD:
    """Renders comprehensive military aviation vector HUD instruments."""

    def __init__(self, screen_w: int = config.SCREEN_WIDTH, screen_h: int = config.SCREEN_HEIGHT):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.cx = screen_w * 0.5
        self.cy = screen_h * 0.5

        # Initialize HUD fonts
        pygame.font.init()
        self.font_large = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_mid = pygame.font.SysFont("monospace", 15, bold=True)
        self.font_small = pygame.font.SysFont("monospace", 11, bold=True)
        self.font_tiny = pygame.font.SysFont("monospace", 9, bold=False)

        # Warning flash timers
        self.alert_flash_timer = 0.0

    def update(self, dt: float):
        """Update HUD animation timers."""
        self.alert_flash_timer = (self.alert_flash_timer + dt * 4.0) % (math.pi * 2)

    def draw(
        self,
        surface: pygame.Surface,
        aircraft,
        controls_state,
        drones: List,
        pip_surface: Optional[pygame.Surface],
        enemy_projectiles: List
    ):
        """Render complete HUD instrument suite."""
        # 1. Artificial Horizon & Pitch Ladder
        self._draw_horizon_and_pitch_ladder(surface, aircraft.roll_rad, aircraft.pitch_rad)

        # 2. Bank Angle Arc (Top Roll Indicator)
        self._draw_bank_angle_scale(surface, aircraft.roll_rad)

        # 3. Throttle Gauge (Left Column)
        self._draw_throttle_column(surface, aircraft.throttle, aircraft.speed, aircraft.mach)

        # 4. Altimeter & Airspeed Tape (Right Column)
        self._draw_altitude_column(surface, aircraft.altitude, aircraft.speed)

        # 5. Hull Integrity & Deflector Shield Meters (Bottom Left / Bottom Center)
        self._draw_hull_and_shield_meters(surface, aircraft.health, aircraft.max_health, aircraft.shield_energy, aircraft.max_shield, aircraft.is_shield_active)

        # 6. Combat Score & Wave Telemetry (Top Left)
        self._draw_combat_telemetry(surface, aircraft)

        # 7. Targeting Crosshair & Auto-Lock Brackets
        locked_drone = self._draw_targeting_reticle(surface, controls_state.aim_x, controls_state.aim_y, drones, aircraft.roll_rad, aircraft.pitch_rad)

        # 8. Alert & Warning Indicators
        self._draw_threat_warnings(surface, enemy_projectiles, aircraft.is_shield_active, aircraft.shield_energy)

        # 9. Picture-in-Picture (PiP) Window with Hand Tracking Telemetry (Bottom Right)
        if pip_surface:
            self._draw_pip_window(surface, pip_surface, controls_state)

        return locked_drone

    def _draw_horizon_and_pitch_ladder(self, surface: pygame.Surface, roll_rad: float, pitch_rad: float):
        """Draw rotating artificial horizon and pitch ladder steps (±10°, ±20°, ±30°)."""
        pitch_px = math.sin(pitch_rad) * 220.0
        center_y = self.cy + pitch_px

        # 1. Central Aircraft Fixed Reticle (Waterline Symbol)
        w_col = config.COLOR_PRIMARY
        # Left wing bar
        pygame.draw.line(surface, w_col, (self.cx - 50, self.cy), (self.cx - 20, self.cy), 2)
        pygame.draw.line(surface, w_col, (self.cx - 20, self.cy), (self.cx - 20, self.cy + 6), 2)
        # Right wing bar
        pygame.draw.line(surface, w_col, (self.cx + 20, self.cy), (self.cx + 50, self.cy), 2)
        pygame.draw.line(surface, w_col, (self.cx + 20, self.cy), (self.cx + 20, self.cy + 6), 2)
        # Center pip
        pygame.draw.circle(surface, w_col, (int(self.cx), int(self.cy)), 2)

        # 2. Main Artificial Horizon Line
        h_len = 220
        p1 = rotate_2d(self.cx - h_len, center_y, -roll_rad, (self.cx, self.cy))
        p2 = rotate_2d(self.cx + h_len, center_y, -roll_rad, (self.cx, self.cy))
        pygame.draw.line(surface, config.COLOR_PRIMARY_DIM, p1, p2, 1)

        # Horizon center gap
        g1 = rotate_2d(self.cx - 30, center_y, -roll_rad, (self.cx, self.cy))
        g2 = rotate_2d(self.cx + 30, center_y, -roll_rad, (self.cx, self.cy))
        # Draw dotted or colored center marks
        pygame.draw.line(surface, config.COLOR_PRIMARY, p1, g1, 2)
        pygame.draw.line(surface, config.COLOR_PRIMARY, g2, p2, 2)

        # 3. Pitch Ladder Steps
        ladder_angles = [-30, -20, -10, 10, 20, 30]
        step_px_per_deg = 5.5

        for angle in ladder_angles:
            step_offset_y = center_y - (angle * step_px_per_deg)
            is_positive = (angle > 0)
            bar_w = 42 if abs(angle) % 20 == 0 else 28
            notch_h = -6 if is_positive else 6 # Positive pitches point down toward horizon

            # Left rung
            lp1 = rotate_2d(self.cx - 60 - bar_w, step_offset_y, -roll_rad, (self.cx, self.cy))
            lp2 = rotate_2d(self.cx - 60, step_offset_y, -roll_rad, (self.cx, self.cy))
            l_notch = rotate_2d(self.cx - 60, step_offset_y + notch_h, -roll_rad, (self.cx, self.cy))

            # Right rung
            rp1 = rotate_2d(self.cx + 60, step_offset_y, -roll_rad, (self.cx, self.cy))
            rp2 = rotate_2d(self.cx + 60 + bar_w, step_offset_y, -roll_rad, (self.cx, self.cy))
            r_notch = rotate_2d(self.cx + 60, step_offset_y + notch_h, -roll_rad, (self.cx, self.cy))

            ladder_col = config.COLOR_PRIMARY if is_positive else config.COLOR_WARNING

            if is_positive:
                # Solid lines for climb
                pygame.draw.line(surface, ladder_col, lp1, lp2, 1)
                pygame.draw.line(surface, ladder_col, lp2, l_notch, 1)
                pygame.draw.line(surface, ladder_col, rp1, rp2, 1)
                pygame.draw.line(surface, ladder_col, rp1, r_notch, 1)
            else:
                # Dashed lines for dive
                pygame.draw.line(surface, ladder_col, lp1, lp2, 1)
                pygame.draw.line(surface, ladder_col, rp1, rp2, 1)

            # Degree text label
            lbl_pos = rotate_2d(self.cx + 70 + bar_w, step_offset_y - 6, -roll_rad, (self.cx, self.cy))
            lbl_surf = self.font_tiny.render(f"{abs(angle)}°", True, ladder_col)
            surface.blit(lbl_surf, lbl_pos)

    def _draw_bank_angle_scale(self, surface: pygame.Surface, roll_rad: float):
        """Draw top semi-circular bank angle roll indicator."""
        arc_cx = self.cx
        arc_cy = 130
        arc_r = 110

        # Roll ticks (0°, ±15°, ±30°, ±45°, ±60°)
        ticks = [0, 15, 30, 45, 60, -15, -30, -45, -60]
        for deg in ticks:
            rad = math.radians(deg) - (math.pi * 0.5)
            x1 = arc_cx + math.cos(rad) * arc_r
            y1 = arc_cy + math.sin(rad) * arc_r
            t_len = 8 if deg in [0, 30, 60, -30, -60] else 4
            x2 = arc_cx + math.cos(rad) * (arc_r - t_len)
            y2 = arc_cy + math.sin(rad) * (arc_r - t_len)
            pygame.draw.line(surface, config.COLOR_PRIMARY_DIM, (x1, y1), (x2, y2), 1)

        # Roll pointer chevron (rotates with player roll)
        ptr_rad = roll_rad - (math.pi * 0.5)
        px = arc_cx + math.cos(ptr_rad) * (arc_r - 12)
        py = arc_cy + math.sin(ptr_rad) * (arc_r - 12)
        pygame.draw.circle(surface, config.COLOR_PRIMARY, (int(px), int(py)), 3)

        # Bank angle numerical readout
        roll_deg = math.degrees(roll_rad)
        deg_txt = self.font_small.render(f"BANK: {roll_deg:+.1f}°", True, config.COLOR_PRIMARY)
        surface.blit(deg_txt, (arc_cx - 45, arc_cy - arc_r - 20))

    def _draw_throttle_column(self, surface: pygame.Surface, throttle: float, speed: float, mach: float):
        """Draw segmented left throttle bar with digital Mach display."""
        x = 45
        y = 210
        w = 26
        h = 240
        num_segments = 12

        # Header
        hdr = self.font_mid.render("THR", True, config.COLOR_PRIMARY)
        surface.blit(hdr, (x, y - 24))

        # Panel Backing
        pygame.draw.rect(surface, (8, 14, 20, 180), (x, y, w, h))
        pygame.draw.rect(surface, config.COLOR_PRIMARY_DIM, (x, y, w, h), 1)

        # Segments
        seg_h = (h - 4) // num_segments
        active_segs = int(throttle * num_segments)

        for i in range(num_segments):
            # Bottom to top
            seg_y = y + h - ((i + 1) * seg_h)
            if i < active_segs:
                col = config.COLOR_PRIMARY if i < num_segments - 2 else config.COLOR_WARNING
                pygame.draw.rect(surface, col, (x + 3, seg_y + 1, w - 6, seg_h - 2))
            else:
                pygame.draw.rect(surface, (20, 35, 45), (x + 3, seg_y + 1, w - 6, seg_h - 2), 1)

        # Readouts
        pct_txt = self.font_small.render(f"{int(throttle * 100)}%", True, config.COLOR_PRIMARY)
        surface.blit(pct_txt, (x, y + h + 8))

        mach_txt = self.font_small.render(f"M {mach:.2f}", True, config.COLOR_EMERALD)
        surface.blit(mach_txt, (x, y + h + 24))

        spd_txt = self.font_tiny.render(f"{int(speed)} KTS", True, config.COLOR_MUTED)
        surface.blit(spd_txt, (x, y + h + 40))

    def _draw_altitude_column(self, surface: pygame.Surface, altitude: float, speed: float):
        """Draw right altimeter tape and climb status."""
        x = self.screen_w - 75
        y = 210
        w = 30
        h = 240

        # Header
        hdr = self.font_mid.render("ALT", True, config.COLOR_PRIMARY)
        surface.blit(hdr, (x, y - 24))

        # Backing
        pygame.draw.rect(surface, (8, 14, 20, 180), (x, y, w, h))
        pygame.draw.rect(surface, config.COLOR_PRIMARY_DIM, (x, y, w, h), 1)

        # Tape ticks
        for i in range(7):
            ty = y + (i * (h // 6))
            pygame.draw.line(surface, config.COLOR_PRIMARY_DIM, (x, ty), (x + 8, ty), 1)

        # Digital Altitude Box
        alt_int = int(altitude)
        alt_box_y = y + h // 2 - 12
        pygame.draw.rect(surface, (0, 30, 25), (x - 40, alt_box_y, 70, 24))
        pygame.draw.rect(surface, config.COLOR_PRIMARY, (x - 40, alt_box_y, 70, 24), 1)

        alt_txt = self.font_small.render(f"{alt_int:,}", True, config.COLOR_WHITE)
        surface.blit(alt_txt, (x - 34, alt_box_y + 4))

        ft_txt = self.font_tiny.render("FT MSL", True, config.COLOR_MUTED)
        surface.blit(ft_txt, (x - 18, y + h + 8))

    def _draw_hull_and_shield_meters(
        self,
        surface: pygame.Surface,
        health: float,
        max_health: float,
        shield: float,
        max_shield: float,
        shield_active: bool
    ):
        """Draw bottom hull integrity bar and deflector shield power meter."""
        bx = 110
        by = self.screen_h - 65
        bar_w = 200
        bar_h = 14

        # 1. Hull Health Meter
        hp_pct = max(0.0, health / max_health)
        hp_col = config.COLOR_EMERALD if hp_pct > 0.5 else (config.COLOR_WARNING if hp_pct > 0.25 else config.COLOR_DANGER)

        lbl_hp = self.font_small.render(f"HULL INTEGRITY [{int(health)}%]", True, hp_col)
        surface.blit(lbl_hp, (bx, by - 18))

        pygame.draw.rect(surface, (15, 25, 35), (bx, by, bar_w, bar_h))
        pygame.draw.rect(surface, hp_col, (bx, by, int(bar_w * hp_pct), bar_h))
        pygame.draw.rect(surface, config.COLOR_PRIMARY_DIM, (bx, by, bar_w, bar_h), 1)

        # 2. Deflector Shield Meter
        sh_bx = bx + bar_w + 35
        sh_pct = max(0.0, shield / max_shield)
        sh_col = config.COLOR_SHIELD if shield_active else (0, 140, 210)

        sh_status_txt = "DEFLECTOR [ACTIVE]" if shield_active else f"DEFLECTOR [{int(shield)}%]"
        lbl_sh = self.font_small.render(sh_status_txt, True, sh_col)
        surface.blit(lbl_sh, (sh_bx, by - 18))

        pygame.draw.rect(surface, (15, 25, 35), (sh_bx, by, bar_w, bar_h))
        pygame.draw.rect(surface, sh_col, (sh_bx, by, int(bar_w * sh_pct), bar_h))
        pygame.draw.rect(surface, (0, 180, 255), (sh_bx, by, bar_w, bar_h), 1)

    def _draw_combat_telemetry(self, surface: pygame.Surface, aircraft):
        """Draw score, wave, combo multiplier, and kill streak in top-left."""
        x = 45
        y = 35

        # Score
        score_lbl = self.font_large.render(f"SCORE: {aircraft.score:07d}", True, config.COLOR_WHITE)
        surface.blit(score_lbl, (x, y))

        # Wave & Kills
        wave_txt = self.font_mid.render(f"WAVE: {getattr(aircraft, 'wave_number', 1):02d} | KILLS: {aircraft.kills}", True, config.COLOR_PRIMARY)
        surface.blit(wave_txt, (x, y + 28))

        # Multiplier / Streak
        if aircraft.multiplier > 1:
            multi_txt = self.font_mid.render(f"COMBO {aircraft.multiplier}X ({aircraft.streak} STREAK)", True, config.COLOR_WARNING)
            surface.blit(multi_txt, (x, y + 50))

            # Streak timer progress bar
            bar_w = 120
            t_pct = max(0.0, aircraft.streak_timer / 5.0)
            pygame.draw.rect(surface, (40, 30, 10), (x, y + 72, bar_w, 4))
            pygame.draw.rect(surface, config.COLOR_WARNING, (x, y + 72, int(bar_w * t_pct), 4))
        else:
            acc_txt = self.font_small.render(f"ACCURACY: {aircraft.accuracy:.1f}%", True, config.COLOR_MUTED)
            surface.blit(acc_txt, (x, y + 50))

    def _draw_targeting_reticle(
        self,
        surface: pygame.Surface,
        aim_x: float,
        aim_y: float,
        drones: List,
        player_roll_rad: float,
        player_pitch_rad: float
    ):
        """Draw aiming reticle with dynamic lock-on brackets on closest target."""
        # 1. Base Crosshair
        reticle_r = 16
        pygame.draw.circle(surface, config.COLOR_PRIMARY, (int(aim_x), int(aim_y)), reticle_r, 1)
        pygame.draw.circle(surface, config.COLOR_PRIMARY, (int(aim_x), int(aim_y)), 2)

        # Crosshair notches
        pygame.draw.line(surface, config.COLOR_PRIMARY, (aim_x - reticle_r - 6, aim_y), (aim_x - reticle_r + 2, aim_y), 1)
        pygame.draw.line(surface, config.COLOR_PRIMARY, (aim_x + reticle_r - 2, aim_y), (aim_x + reticle_r + 6, aim_y), 1)
        pygame.draw.line(surface, config.COLOR_PRIMARY, (aim_x, aim_y - reticle_r - 6), (aim_x, aim_y - reticle_r + 2), 1)
        pygame.draw.line(surface, config.COLOR_PRIMARY, (aim_x, aim_y + reticle_r - 2), (aim_x, aim_y + reticle_r + 6), 1)

        # 2. Find closest drone to crosshair in screen space
        best_drone = None
        min_dist = config.CROSSHAIR_LOCK_RADIUS

        for drone in drones:
            if not drone.is_visible:
                continue

            # Screen space position after player roll/pitch
            drx, dry = rotate_2d(drone.screen_x, drone.screen_y, -player_roll_rad, (self.cx, self.cy))
            dry += math.sin(player_pitch_rad) * 180.0

            dist = math.hypot(drx - aim_x, dry - aim_y)
            if dist < min_dist:
                min_dist = dist
                best_drone = drone
                drone.is_locked_on = True
            else:
                drone.is_locked_on = False

        # 3. Draw Lock-On Target Box if locked
        if best_drone is not None:
            drx, dry = rotate_2d(best_drone.screen_x, best_drone.screen_y, -player_roll_rad, (self.cx, self.cy))
            dry += math.sin(player_pitch_rad) * 180.0

            lock_box_size = max(24, int(best_drone.screen_scale * 75.0))
            half_s = lock_box_size // 2

            # Glowing emerald corner brackets
            b_col = config.COLOR_EMERALD
            blen = 7
            # Top-Left
            pygame.draw.line(surface, b_col, (drx - half_s, dry - half_s), (drx - half_s + blen, dry - half_s), 2)
            pygame.draw.line(surface, b_col, (drx - half_s, dry - half_s), (drx - half_s, dry - half_s + blen), 2)
            # Top-Right
            pygame.draw.line(surface, b_col, (drx + half_s, dry - half_s), (drx + half_s - blen, dry - half_s), 2)
            pygame.draw.line(surface, b_col, (drx + half_s, dry - half_s), (drx + half_s, dry - half_s + blen), 2)
            # Bottom-Left
            pygame.draw.line(surface, b_col, (drx - half_s, dry + half_s), (drx - half_s + blen, dry + half_s), 2)
            pygame.draw.line(surface, b_col, (drx - half_s, dry + half_s), (drx - half_s, dry + half_s - blen), 2)
            # Bottom-Right
            pygame.draw.line(surface, b_col, (drx + half_s, dry + half_s), (drx + half_s - blen, dry + half_s), 2)
            pygame.draw.line(surface, b_col, (drx + half_s, dry + half_s), (drx + half_s, dry + half_s - blen), 2)

            # Target Telemetry Tag
            rng_m = int(best_drone.z)
            lock_txt = self.font_tiny.render(f"LOCK // {best_drone.drone_type.value} {rng_m}M", True, b_col)
            surface.blit(lock_txt, (drx - half_s, dry + half_s + 4))

            # Lead Line from Crosshair to Target
            pygame.draw.line(surface, (0, 255, 140, 100), (aim_x, aim_y), (drx, dry), 1)

        return best_drone

    def _draw_threat_warnings(
        self,
        surface: pygame.Surface,
        enemy_projectiles: List,
        shield_active: bool,
        shield_energy: float
    ):
        """Draw urgent warning badges for incoming plasma and low shields."""
        # Incoming Missile / Plasma Alert
        has_close_threat = any(p.z < 350.0 for p in enemy_projectiles)

        if has_close_threat:
            # Flashing banner
            if math.sin(self.alert_flash_timer * 2.0) > 0:
                alert_surf = self.font_mid.render("! WARNING: INCOMING HOSTILE FIRE !", True, config.COLOR_DANGER)
                surface.blit(alert_surf, (self.cx - 150, self.cy - 120))

        # Shield Low Alert
        if shield_active and shield_energy < 20.0:
            if math.sin(self.alert_flash_timer * 2.0) > 0:
                warn_surf = self.font_small.render("! DEFLECTOR ENERGY CRITICAL !", True, config.COLOR_WARNING)
                surface.blit(warn_surf, (self.cx - 110, self.cy + 130))

    def _draw_pip_window(
        self,
        surface: pygame.Surface,
        pip_surface: pygame.Surface,
        controls_state
    ):
        """Draw bottom-right Picture-in-Picture window with tracking status telemetry."""
        pip_w = config.PIP_WIDTH
        pip_h = config.PIP_HEIGHT
        pip_x = self.screen_w - pip_w - config.PIP_MARGIN
        pip_y = self.screen_h - pip_h - config.PIP_MARGIN

        # Blit camera/skeleton feed
        surface.blit(pip_surface, (pip_x, pip_y))

        # Telemetry Status Bar Header
        mode_txt = "INPUT: MOUSE/KEY" if controls_state.mouse_mode_active else "INPUT: DUAL-HAND CV"
        mode_col = config.COLOR_WARNING if controls_state.mouse_mode_active else config.COLOR_PRIMARY
        lbl_mode = self.font_tiny.render(mode_txt, True, mode_col)
        surface.blit(lbl_mode, (pip_x + 6, pip_y - 14))

        # Status Indicators for Yoke, Throttle, Trigger, Shield
        status_y = pip_y + pip_h - 18

        # Yoke Status
        yoke_txt = "YOKE: OK" if controls_state.has_right_hand else "YOKE: NO"
        yoke_col = config.COLOR_EMERALD if controls_state.has_right_hand else config.COLOR_MUTED
        lbl_yoke = self.font_tiny.render(yoke_txt, True, yoke_col)
        surface.blit(lbl_yoke, (pip_x + 6, status_y))

        # Throttle Status
        thrtl_txt = "THRTL: OK" if controls_state.has_left_hand else "THRTL: NO"
        thrtl_col = config.COLOR_EMERALD if controls_state.has_left_hand else config.COLOR_MUTED
        lbl_thrtl = self.font_tiny.render(thrtl_txt, True, thrtl_col)
        surface.blit(lbl_thrtl, (pip_x + 68, status_y))

        # Trigger / Shield Active Badges
        if controls_state.is_firing:
            trig_badge = self.font_tiny.render("[FIRE]", True, config.COLOR_DANGER)
            surface.blit(trig_badge, (pip_x + 138, status_y))

        if controls_state.is_shield_active:
            shld_badge = self.font_tiny.render("[SHIELD]", True, config.COLOR_SHIELD)
            surface.blit(shld_badge, (pip_x + 185, status_y))
