"""
User Interface Screens:
Mission Launch Briefing (Start Menu), Holographic Pause Overlay,
Mission Debrief (Game Over / High Score), and Wave Announcement Banners.
"""

from enum import Enum
import math
from typing import Optional, Tuple
import pygame
import config


class GameState(Enum):
    START_MENU = "START_MENU"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    GAME_OVER = "GAME_OVER"


class ScreenManager:
    """Manages menu navigation, instructions, high scores, and debrief overlays."""

    def __init__(self, screen_w: int = config.SCREEN_WIDTH, screen_h: int = config.SCREEN_HEIGHT):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.cx = screen_w * 0.5
        self.cy = screen_h * 0.5

        pygame.font.init()
        self.font_title = pygame.font.SysFont("monospace", 36, bold=True)
        self.font_hdr = pygame.font.SysFont("monospace", 22, bold=True)
        self.font_btn = pygame.font.SysFont("monospace", 16, bold=True)
        self.font_bold = pygame.font.SysFont("monospace", 14, bold=True)
        self.font_body = pygame.font.SysFont("monospace", 14, bold=False)
        self.font_small = pygame.font.SysFont("monospace", 11, bold=True)
        self.font_tiny = pygame.font.SysFont("monospace", 10, bold=False)

        self.high_score = 0
        self.anim_phase = 0.0

    def update(self, dt: float):
        """Update pulsing animation timers."""
        self.anim_phase = (self.anim_phase + dt * 3.0) % (math.pi * 2)

    def draw_start_menu(
        self,
        surface: pygame.Surface,
        has_right_hand: bool,
        has_left_hand: bool,
        mouse_mode: bool,
        pip_surface: Optional[pygame.Surface]
    ):
        """Render high-tech cyberpunk briefing and startup launch screen."""
        # Dark slate background with cyber grid
        surface.fill(config.COLOR_BG)

        # Ambient grid lines
        for y in range(0, self.screen_h, 50):
            pygame.draw.line(surface, (15, 25, 35), (0, y), (self.screen_w, y), 1)
        for x in range(0, self.screen_w, 50):
            pygame.draw.line(surface, (15, 25, 35), (x, 0), (x, self.screen_h), 1)

        # Title & Subtitle
        pulse = 0.85 + 0.15 * math.sin(self.anim_phase)
        title_col = (int(config.COLOR_PRIMARY[0] * pulse), int(config.COLOR_PRIMARY[1] * pulse), int(config.COLOR_PRIMARY[2] * pulse))

        title_surf = self.font_title.render("VISION PILOT", True, title_col)
        surface.blit(title_surf, (self.cx - title_surf.get_width() * 0.5, 45))

        sub_surf = self.font_hdr.render("GESTURE CONTROLLED FLIGHT SIMULATOR & COMBAT", True, config.COLOR_WHITE)
        surface.blit(sub_surf, (self.cx - sub_surf.get_width() * 0.5, 95))

        # Decorative line
        pygame.draw.line(surface, config.COLOR_PRIMARY, (self.cx - 300, 130), (self.cx + 300, 130), 2)

        # Briefing Panels
        # Panel 1: Flight Controls Guide (Left)
        p1_x, p1_y, p1_w, p1_h = 60, 150, 520, 420
        pygame.draw.rect(surface, (12, 18, 26, 220), (p1_x, p1_y, p1_w, p1_h))
        pygame.draw.rect(surface, config.COLOR_PRIMARY_DIM, (p1_x, p1_y, p1_w, p1_h), 1)

        hdr1 = self.font_hdr.render("// TACTICAL CONTROL SCHEME", True, config.COLOR_PRIMARY)
        surface.blit(hdr1, (p1_x + 18, p1_y + 18))

        instructions = [
            ("RIGHT HAND (FLIGHT YOKE & WEAPONS)", config.COLOR_EMERALD),
            (" • Aiming: Hand center moves crosshair reticle", config.COLOR_WHITE),
            (" • Roll Attitude: Tilt hand left/right to bank wings", config.COLOR_WHITE),
            (" • Pitch Attitude: Raise/lower hand for nose climb/dive", config.COLOR_WHITE),
            (" • Laser Trigger: Extend Index finger (Point / Gun)", config.COLOR_WARNING),
            ("", config.COLOR_WHITE),
            ("LEFT HAND (PROPULSION & DEFENSE)", config.COLOR_SHIELD),
            (" • Throttle (0-100%): Raise wrist for speed, lower to idle", config.COLOR_WHITE),
            (" • Deflector Shield: Open 4 fingers flat to absorb fire", config.COLOR_SHIELD),
            ("", config.COLOR_WHITE),
            ("KEYBOARD / MOUSE FALLBACK", config.COLOR_MUTED),
            (" • Mouse: Aim crosshair | LMB / Space: Fire Laser", config.COLOR_WHITE),
            (" • Wheel / Shift / Ctrl: Throttle | RMB / Q: Shield", config.COLOR_WHITE),
            (" • Press [TAB] anytime to toggle Mouse Fallback", config.COLOR_PRIMARY),
        ]

        ty = p1_y + 55
        for line, col in instructions:
            if line.startswith("RIGHT") or line.startswith("LEFT") or line.startswith("KEYBOARD"):
                txt = self.font_bold.render(line, True, col)
            else:
                txt = self.font_body.render(line, True, col)
            surface.blit(txt, (p1_x + 20, ty))
            ty += 22

        # Panel 2: Sensor Telemetry & Calibration (Right)
        p2_x, p2_y, p2_w, p2_h = self.screen_w - 580, 150, 520, 420
        pygame.draw.rect(surface, (12, 18, 26, 220), (p2_x, p2_y, p2_w, p2_h))
        pygame.draw.rect(surface, config.COLOR_PRIMARY_DIM, (p2_x, p2_y, p2_w, p2_h), 1)

        hdr2 = self.font_hdr.render("// SENSOR DIAGNOSTICS", True, config.COLOR_PRIMARY)
        surface.blit(hdr2, (p2_x + 18, p2_y + 18))

        # Sensor status tags
        r_stat = "LOCKED [ACTIVE]" if has_right_hand else "SEEKING HAND..."
        r_col = config.COLOR_EMERALD if has_right_hand else config.COLOR_WARNING
        txt_r = self.font_bold.render(f"RIGHT YOKE TRACKING: {r_stat}", True, r_col)
        surface.blit(txt_r, (p2_x + 20, p2_y + 55))

        l_stat = "LOCKED [ACTIVE]" if has_left_hand else "SEEKING HAND..."
        l_col = config.COLOR_EMERALD if has_left_hand else config.COLOR_WARNING
        txt_l = self.font_bold.render(f"LEFT THROTTLE TRACKING: {l_stat}", True, l_col)
        surface.blit(txt_l, (p2_x + 20, p2_y + 82))

        m_stat = "ACTIVE [TAB TO SWITCH]" if mouse_mode else "STANDBY [TAB TO ENABLE]"
        txt_m = self.font_bold.render(f"MOUSE OVERRIDE MODE: {m_stat}", True, config.COLOR_MUTED)
        surface.blit(txt_m, (p2_x + 20, p2_y + 109))

        # Camera PiP Box in Menu
        if pip_surface:
            pip_box_x = p2_x + 20
            pip_box_y = p2_y + 145
            surface.blit(pip_surface, (pip_box_x, pip_box_y))

            calib_tip = self.font_tiny.render("TIP: Place hands in frame and press [C] to zero neutral yoke", True, config.COLOR_MUTED)
            surface.blit(calib_tip, (pip_box_x, pip_box_y + config.PIP_HEIGHT + 10))

        # Launch Button Banner at bottom
        btn_w, btn_h = 440, 52
        btn_x = self.cx - btn_w * 0.5
        btn_y = self.screen_h - 100

        pygame.draw.rect(surface, (0, 50, 40), (btn_x, btn_y, btn_w, btn_h))
        pygame.draw.rect(surface, config.COLOR_PRIMARY, (btn_x, btn_y, btn_w, btn_h), 2)

        prompt_txt = "PRESS [SPACE / ENTER] TO LAUNCH SORTIE"
        prompt_surf = self.font_btn.render(prompt_txt, True, config.COLOR_WHITE)
        surface.blit(prompt_surf, (btn_x + (btn_w - prompt_surf.get_width()) * 0.5, btn_y + 16))

    def draw_pause_menu(self, surface: pygame.Surface, mouse_mode: bool):
        """Render holographic pause menu overlay."""
        # Frosted glass overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((8, 14, 20, 200))
        surface.blit(overlay, (0, 0))

        # Pause Box
        bw, bh = 480, 320
        bx = self.cx - bw * 0.5
        by = self.cy - bh * 0.5

        pygame.draw.rect(surface, (12, 18, 26), (bx, by, bw, bh))
        pygame.draw.rect(surface, config.COLOR_PRIMARY, (bx, by, bw, bh), 2)

        title = self.font_title.render("SIMULATION PAUSED", True, config.COLOR_PRIMARY)
        surface.blit(title, (bx + (bw - title.get_width()) * 0.5, by + 28))

        options = [
            ("RESUME FLIGHT", "[ESC] / [SPACE]"),
            (f"CONTROL MODE: {'MOUSE' if mouse_mode else 'CV GESTURE'}", "[TAB]"),
            ("RECALIBRATE SENSORS", "[C]"),
            ("ABORT SORTIE", "[Q]"),
        ]

        oy = by + 95
        for opt, key in options:
            txt_opt = self.font_hdr.render(opt, True, config.COLOR_WHITE)
            txt_key = self.font_hdr.render(key, True, config.COLOR_WARNING)
            surface.blit(txt_opt, (bx + 35, oy))
            surface.blit(txt_key, (bx + bw - txt_key.get_width() - 35, oy))
            oy += 45

    def draw_game_over(self, surface: pygame.Surface, aircraft):
        """Render mission debrief and combat performance statistics."""
        # Update high score
        if aircraft.score > self.high_score:
            self.high_score = aircraft.score

        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((10, 8, 14, 225))
        surface.blit(overlay, (0, 0))

        # Debrief Box
        bw, bh = 600, 480
        bx = self.cx - bw * 0.5
        by = self.cy - bh * 0.5

        pygame.draw.rect(surface, (16, 12, 20), (bx, by, bw, bh))
        pygame.draw.rect(surface, config.COLOR_DANGER, (bx, by, bw, bh), 2)

        # Header
        hdr = self.font_title.render("MISSION DEBRIEF", True, config.COLOR_DANGER)
        surface.blit(hdr, (bx + (bw - hdr.get_width()) * 0.5, by + 25))

        # Pilot Rank Classification
        if aircraft.score >= 8000:
            rank = "TOP GUN // FLEET COMMANDER"
            rank_col = (255, 230, 80)
        elif aircraft.score >= 4000:
            rank = "SQUADRON ACE PILOT"
            rank_col = config.COLOR_EMERALD
        elif aircraft.score >= 1500:
            rank = "FIGHTER PILOT"
            rank_col = config.COLOR_PRIMARY
        else:
            rank = "RECRUIT CADET"
            rank_col = config.COLOR_MUTED

        rank_txt = self.font_hdr.render(f"PILOT RATING: {rank}", True, rank_col)
        surface.blit(rank_txt, (bx + (bw - rank_txt.get_width()) * 0.5, by + 75))

        pygame.draw.line(surface, (80, 30, 40), (bx + 40, by + 115), (bx + bw - 40, by + 115), 1)

        # Performance Metrics Table
        stats = [
            ("FINAL COMBAT SCORE", f"{aircraft.score:07d}"),
            ("ALL-TIME HIGH SCORE", f"{self.high_score:07d}"),
            ("HOSTILES DESTROYED", f"{aircraft.kills} DRONES"),
            ("MAX COMBO STREAK", f"{aircraft.highest_streak} HITS"),
            ("WEAPONS ACCURACY", f"{aircraft.accuracy:.1f} %"),
        ]

        sy = by + 135
        for label, val in stats:
            lbl_surf = self.font_hdr.render(label, True, config.COLOR_WHITE)
            val_surf = self.font_hdr.render(val, True, config.COLOR_PRIMARY if "SCORE" in label else config.COLOR_WARNING)
            surface.blit(lbl_surf, (bx + 45, sy))
            surface.blit(val_surf, (bx + bw - val_surf.get_width() - 45, sy))
            sy += 42

        # Restart Banner
        btn_w = 420
        btn_x = self.cx - btn_w * 0.5
        btn_y = by + bh - 65

        pygame.draw.rect(surface, (50, 15, 25), (btn_x, btn_y, btn_w, 44))
        pygame.draw.rect(surface, config.COLOR_DANGER, (btn_x, btn_y, btn_w, 44), 1)

        retry_txt = self.font_btn.render("PRESS [SPACE / ENTER] TO RE-ENGAGE", True, config.COLOR_WHITE)
        surface.blit(retry_txt, (btn_x + (btn_w - retry_txt.get_width()) * 0.5, btn_y + 12))

    def draw_wave_clear_banner(self, surface: pygame.Surface, wave_number: int, is_boss: bool):
        """Render animated wave incoming banner."""
        banner_h = 50
        banner_y = 170

        banner_surf = pygame.Surface((self.screen_w, banner_h), pygame.SRCALPHA)
        bg_col = (255, 30, 80, 180) if is_boss else (0, 160, 120, 160)
        banner_surf.fill(bg_col)
        surface.blit(banner_surf, (0, banner_y))

        if is_boss:
            msg = f"⚠ ALERT: DREADNOUGHT FLAGSHIP DETECTED — WAVE {wave_number:02d} ⚠"
        else:
            msg = f"► WAVE {wave_number:02d} INCOMING — ENGAGE HOSTILE FORMATION ◄"

        msg_surf = self.font_hdr.render(msg, True, config.COLOR_WHITE)
        surface.blit(msg_surf, (self.cx - msg_surf.get_width() * 0.5, banner_y + 14))
