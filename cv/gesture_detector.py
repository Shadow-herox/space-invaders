"""
Mathematical feature extraction from MediaPipe landmarks:
Roll, Pitch, Aiming Crosshair, Laser Trigger, Throttle, and Deflector Shield.
Includes mouse & keyboard fallback input processing.
"""

from dataclasses import dataclass
import math
from typing import Optional, Dict, Tuple
import config
from cv.hand_tracker import HandData
from utils.math_helpers import clamp, lerp, exp_decay, remap, normalize_angle


@dataclass
class FlightControlsState:
    """Consolidated instantaneous flight controls state."""
    # Crosshair in screen coordinates
    aim_x: float = config.SCREEN_WIDTH * 0.5
    aim_y: float = config.SCREEN_HEIGHT * 0.5
    raw_aim_x: float = config.SCREEN_WIDTH * 0.5
    raw_aim_y: float = config.SCREEN_HEIGHT * 0.5

    # Aircraft Attitude
    target_roll_rad: float = 0.0        # Bank angle in radians (-pi/2 to pi/2)
    target_pitch_rad: float = 0.0       # Pitch angle in radians (-pi/3 to pi/3)
    target_roll_deg: float = 0.0
    target_pitch_deg: float = 0.0

    # Propulsion & Defense
    throttle: float = 0.5               # 0.0 (idle) to 1.0 (afterburner)
    is_firing: bool = False             # Primary laser trigger engaged
    is_shield_active: bool = False      # Deflector shield engaged

    # Tracking Telemetry
    has_right_hand: bool = False        # Yoke tracking lock
    has_left_hand: bool = False         # Throttle tracking lock
    mouse_mode_active: bool = False     # Whether currently operating via mouse fallback
    calibration_offset_y: float = 0.5   # Neutral pitch center


class GestureDetector:
    """Extracts high-precision flight control parameters from dual hand tracking."""

    def __init__(self):
        self.state = FlightControlsState()
        self.mouse_mode = False

        # Neutral calibration points
        self.neutral_yoke_x = 0.70      # Right side of camera frame
        self.neutral_yoke_y = 0.50      # Center height of camera frame
        self.neutral_throttle_y = 0.50

        # Internal smoothed values
        self._current_roll = 0.0
        self._current_pitch = 0.0
        self._current_throttle = 0.5
        self._current_aim_x = config.SCREEN_WIDTH * 0.5
        self._current_aim_y = config.SCREEN_HEIGHT * 0.5

    def recalibrate_neutral(self, right_hand: Optional[HandData] = None, left_hand: Optional[HandData] = None):
        """Recalibrate neutral hand center positions."""
        if right_hand:
            self.neutral_yoke_x = right_hand.middle_mcp[0]
            self.neutral_yoke_y = right_hand.middle_mcp[1]
        if left_hand:
            self.neutral_throttle_y = left_hand.wrist_pos[1]
        print(f"[GestureDetector] Neutral recalibrated: Yoke=({self.neutral_yoke_x:.2f}, {self.neutral_yoke_y:.2f})")

    def toggle_mouse_mode(self) -> bool:
        """Toggle between CV gesture mode and Mouse/Keyboard fallback mode."""
        self.mouse_mode = not self.mouse_mode
        self.state.mouse_mode_active = self.mouse_mode
        print(f"[GestureDetector] Control mode: {'MOUSE/KEYBOARD' if self.mouse_mode else 'DUAL-HAND CV'}")
        return self.mouse_mode

    def process_hands(
        self,
        hands: Dict[str, Optional[HandData]],
        dt: float
    ) -> FlightControlsState:
        """Extract continuous flight parameters from detected Left and Right hands."""
        right = hands.get('Right')
        left = hands.get('Left')

        self.state.has_right_hand = (right is not None)
        self.state.has_left_hand = (left is not None)

        if self.mouse_mode:
            # In explicit mouse mode, hands are ignored
            return self.state

        # ==========================================
        # 1. Right Hand: Flight Yoke & Weapon Trigger
        # ==========================================
        if right is not None and len(right.landmarks_2d) >= 21:
            w = right.landmarks_2d[0]   # Wrist
            m = right.landmarks_2d[9]   # Middle MCP
            idx_tip = right.landmarks_2d[8] # Index tip
            mid_tip = right.landmarks_2d[12]# Middle tip
            ring_tip = right.landmarks_2d[16]# Ring tip
            pinky_tip = right.landmarks_2d[20]# Pinky tip

            palm_size = max(0.02, right.palm_size)

            # A. Aiming / Crosshair Position
            # Map palm center coordinates [0.4, 0.95] in camera to screen width
            raw_screen_x = remap(m[0], 0.35, 0.95, 0, config.SCREEN_WIDTH)
            raw_screen_y = remap(m[1], 0.15, 0.85, 0, config.SCREEN_HEIGHT)
            self.state.raw_aim_x = raw_screen_x
            self.state.raw_aim_y = raw_screen_y

            # Smooth aim with exponential decay
            self._current_aim_x = exp_decay(self._current_aim_x, raw_screen_x, 18.0, dt)
            self._current_aim_y = exp_decay(self._current_aim_y, raw_screen_y, 18.0, dt)
            self.state.aim_x = self._current_aim_x
            self.state.aim_y = self._current_aim_y

            # B. Roll Angle (θ)
            # θ = atan2(y9 - y0, x9 - x0) - pi/2
            dx = m[0] - w[0]
            dy = m[1] - w[1] # Note: in image coords, Y is positive downwards
            raw_angle = math.atan2(dy, dx) - (math.pi * 0.5)
            raw_angle = normalize_angle(raw_angle)

            # Invert so tilting hand right rolls aircraft right (clockwise)
            roll_target = clamp(raw_angle * 1.3, -math.radians(config.ROLL_MAX_DEG), math.radians(config.ROLL_MAX_DEG))

            # Apply deadzone
            if abs(roll_target) < math.radians(config.ROLL_DEADZONE_DEG):
                roll_target = 0.0

            self._current_roll = exp_decay(self._current_roll, roll_target, 12.0, dt)
            self.state.target_roll_rad = self._current_roll
            self.state.target_roll_deg = math.degrees(self._current_roll)

            # C. Pitch Angle
            # Vertical deviation from neutral center
            pitch_offset = -(m[1] - self.neutral_yoke_y) # Inverted: raising hand (smaller y) pitches up
            if abs(pitch_offset) < config.PITCH_DEADZONE:
                pitch_offset = 0.0
            else:
                pitch_offset = pitch_offset - math.copysign(config.PITCH_DEADZONE, pitch_offset)

            pitch_target = clamp(pitch_offset * 2.4, -math.radians(config.PITCH_MAX_DEG), math.radians(config.PITCH_MAX_DEG))
            self._current_pitch = exp_decay(self._current_pitch, pitch_target, 12.0, dt)
            self.state.target_pitch_rad = self._current_pitch
            self.state.target_pitch_deg = math.degrees(self._current_pitch)

            # D. Laser Trigger (Gun / Point Gesture)
            # Index tip extended > 1.25 * palm_size from wrist/MCP
            # Middle, Ring, Pinky curled (< 1.05 * palm_size)
            idx_dist = math.hypot(idx_tip[0] - w[0], idx_tip[1] - w[1])
            mid_dist = math.hypot(mid_tip[0] - w[0], mid_tip[1] - w[1])
            ring_dist = math.hypot(ring_tip[0] - w[0], ring_tip[1] - w[1])
            pinky_dist = math.hypot(pinky_tip[0] - w[0], pinky_tip[1] - w[1])

            is_index_extended = (idx_dist / palm_size) >= config.TRIGGER_EXTEND_RATIO
            is_others_curled = (
                (mid_dist / palm_size) < 1.15 and
                (ring_dist / palm_size) < 1.10 and
                (pinky_dist / palm_size) < 1.10
            )

            self.state.is_firing = is_index_extended and is_others_curled
        else:
            # Smoothly return right-hand flight parameters to neutral if lost
            self._current_roll = exp_decay(self._current_roll, 0.0, 5.0, dt)
            self._current_pitch = exp_decay(self._current_pitch, 0.0, 5.0, dt)
            self.state.target_roll_rad = self._current_roll
            self.state.target_pitch_rad = self._current_pitch
            self.state.target_roll_deg = math.degrees(self._current_roll)
            self.state.target_pitch_deg = math.degrees(self._current_pitch)
            self.state.is_firing = False

        # ==========================================
        # 2. Left Hand: Throttle & Deflector Shield
        # ==========================================
        if left is not None and len(left.landmarks_2d) >= 21:
            lw = left.landmarks_2d[0]
            palm_size = max(0.02, left.palm_size)

            # A. Throttle (0.0 to 1.0)
            # Left wrist height remapped: y=0.2 (high) -> 1.0; y=0.8 (low) -> 0.0
            raw_throttle = remap(lw[1], 0.78, 0.22, 0.0, 1.0)
            self._current_throttle = exp_decay(self._current_throttle, raw_throttle, 10.0, dt)
            self.state.throttle = self._current_throttle

            # B. Deflector Shield (Open Palm)
            # All 4 fingertips (8, 12, 16, 20) extended > 1.2 * palm_size from wrist
            l_idx = math.hypot(left.landmarks_2d[8][0] - lw[0], left.landmarks_2d[8][1] - lw[1])
            l_mid = math.hypot(left.landmarks_2d[12][0] - lw[0], left.landmarks_2d[12][1] - lw[1])
            l_rng = math.hypot(left.landmarks_2d[16][0] - lw[0], left.landmarks_2d[16][1] - lw[1])
            l_pnk = math.hypot(left.landmarks_2d[20][0] - lw[0], left.landmarks_2d[20][1] - lw[1])

            open_fingers_count = sum([
                (l_idx / palm_size) >= config.SHIELD_EXTEND_RATIO,
                (l_mid / palm_size) >= config.SHIELD_EXTEND_RATIO,
                (l_rng / palm_size) >= config.SHIELD_EXTEND_RATIO,
                (l_pnk / palm_size) >= config.SHIELD_EXTEND_RATIO
            ])

            self.state.is_shield_active = (open_fingers_count >= 3)
        else:
            self.state.is_shield_active = False

        return self.state

    def process_mouse_keyboard_fallback(
        self,
        mouse_pos: Tuple[int, int],
        mouse_buttons: Tuple[bool, bool, bool], # (Left, Middle, Right)
        keys_pressed,
        wheel_delta: int,
        dt: float
    ) -> FlightControlsState:
        """Process keyboard & mouse controls for seamless fallback gameplay."""
        import pygame

        self.state.mouse_mode_active = True
        self.state.has_right_hand = True
        self.state.has_left_hand = True

        # Mouse Aiming
        self.state.raw_aim_x = float(mouse_pos[0])
        self.state.raw_aim_y = float(mouse_pos[1])
        self._current_aim_x = exp_decay(self._current_aim_x, float(mouse_pos[0]), 22.0, dt)
        self._current_aim_y = exp_decay(self._current_aim_y, float(mouse_pos[1]), 22.0, dt)
        self.state.aim_x = self._current_aim_x
        self.state.aim_y = self._current_aim_y

        # Roll & Pitch via A/D, W/S or mouse offset from center
        cx = config.SCREEN_WIDTH * 0.5
        cy = config.SCREEN_HEIGHT * 0.5
        offset_x = (mouse_pos[0] - cx) / cx
        offset_y = -(mouse_pos[1] - cy) / cy # Pitch up when mouse above center

        # Keyboard roll override
        key_roll = 0.0
        if keys_pressed[pygame.K_a] or keys_pressed[pygame.K_LEFT]:
            key_roll -= 1.0
        if keys_pressed[pygame.K_d] or keys_pressed[pygame.K_RIGHT]:
            key_roll += 1.0

        target_roll = (key_roll * 0.8) if key_roll != 0.0 else (offset_x * 0.5)
        target_roll = clamp(target_roll, -math.radians(config.ROLL_MAX_DEG), math.radians(config.ROLL_MAX_DEG))

        key_pitch = 0.0
        if keys_pressed[pygame.K_w] or keys_pressed[pygame.K_UP]:
            key_pitch += 0.7
        if keys_pressed[pygame.K_s] or keys_pressed[pygame.K_DOWN]:
            key_pitch -= 0.7

        target_pitch = key_pitch if key_pitch != 0.0 else (offset_y * 0.45)
        target_pitch = clamp(target_pitch, -math.radians(config.PITCH_MAX_DEG), math.radians(config.PITCH_MAX_DEG))

        self._current_roll = exp_decay(self._current_roll, target_roll, 14.0, dt)
        self._current_pitch = exp_decay(self._current_pitch, target_pitch, 14.0, dt)

        self.state.target_roll_rad = self._current_roll
        self.state.target_pitch_rad = self._current_pitch
        self.state.target_roll_deg = math.degrees(self._current_roll)
        self.state.target_pitch_deg = math.degrees(self._current_pitch)

        # Throttle adjustment via Scroll Wheel / Shift / Ctrl
        if wheel_delta != 0:
            self._current_throttle = clamp(self._current_throttle + (wheel_delta * 0.08), 0.0, 1.0)

        if keys_pressed[pygame.K_LSHIFT] or keys_pressed[pygame.K_RSHIFT]:
            self._current_throttle = clamp(self._current_throttle + (0.8 * dt), 0.0, 1.0)
        elif keys_pressed[pygame.K_LCTRL] or keys_pressed[pygame.K_RCTRL]:
            self._current_throttle = clamp(self._current_throttle - (0.8 * dt), 0.0, 1.0)

        self.state.throttle = self._current_throttle

        # Primary Trigger: Mouse Left Click or Spacebar
        self.state.is_firing = mouse_buttons[0] or keys_pressed[pygame.K_SPACE]

        # Deflector Shield: Mouse Right Click, Q, or E
        self.state.is_shield_active = mouse_buttons[2] or keys_pressed[pygame.K_q] or keys_pressed[pygame.K_e]

        return self.state
