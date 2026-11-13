"""
Player Aircraft Physics Model:
Attitude dynamics, propulsion velocity, hull integrity, energy deflector shield,
and score/combat telemetry.
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional
import config
from utils.math_helpers import clamp, lerp, exp_decay


class PlayerAircraft:
    """Simulates player aircraft dynamics, shields, and combat status."""

    def __init__(self):
        # 3D spatial state
        self.x: float = 0.0
        self.y: float = 0.0
        self.z: float = 0.0
        self.altitude: float = 1000.0   # Simulated altitude in feet

        # Attitudes (radians)
        self.roll_rad: float = 0.0
        self.pitch_rad: float = 0.0
        self.yaw_rad: float = 0.0

        # Propulsion
        self.throttle: float = 0.5      # 0.0 to 1.0
        self.speed: float = config.SPEED_MIN + (config.SPEED_MAX - config.SPEED_MIN) * 0.5
        self.mach: float = 0.65

        # Integrity & Deflector Shield
        self.health: float = config.PLAYER_MAX_HEALTH
        self.max_health: float = config.PLAYER_MAX_HEALTH
        self.shield_energy: float = config.PLAYER_MAX_SHIELD
        self.max_shield: float = config.PLAYER_MAX_SHIELD
        self.is_shield_active: bool = False
        self.shield_recharge_cooldown: float = 0.0
        self.is_destroyed: bool = False

        # Combat Telemetry & Score
        self.score: int = 0
        self.kills: int = 0
        self.shots_fired: int = 0
        self.shots_hit: int = 0
        self.streak: int = 0
        self.highest_streak: int = 0
        self.streak_timer: float = 0.0

    @property
    def accuracy(self) -> float:
        """Percentage accuracy (0% to 100%)."""
        if self.shots_fired == 0:
            return 100.0
        return min(100.0, (self.shots_hit / self.shots_fired) * 100.0)

    @property
    def multiplier(self) -> int:
        """Score multiplier based on consecutive kills."""
        if self.streak >= 15:
            return 4
        if self.streak >= 8:
            return 3
        if self.streak >= 3:
            return 2
        return 1

    def add_score(self, base_points: int):
        """Add score with active combo multiplier."""
        earned = base_points * self.multiplier
        self.score += earned
        self.kills += 1
        self.streak += 1
        self.streak_timer = 5.0  # 5 seconds to maintain combo
        if self.streak > self.highest_streak:
            self.highest_streak = self.streak

    def record_shot(self):
        """Track weapon discharge."""
        self.shots_fired += 1

    def record_hit(self):
        """Track confirmed hit on target."""
        self.shots_hit += 1

    def apply_damage(self, amount: float) -> Tuple[bool, bool]:
        """
        Apply incoming damage to aircraft.
        Returns (absorbed_by_shield, is_fatal).
        """
        if self.is_destroyed:
            return (False, False)

        # 1. Deflector Shield Absorption
        if self.is_shield_active and self.shield_energy > 5.0:
            self.shield_energy = max(0.0, self.shield_energy - (amount * 0.8))
            self.shield_recharge_cooldown = config.SHIELD_RECHARGE_DELAY
            return (True, False)

        # 2. Hull Damage
        self.health = max(0.0, self.health - amount)
        self.streak = 0  # Streak resets on hull hit
        if self.health <= 0.0:
            self.is_destroyed = True
            return (False, True)

        return (False, False)

    def update_controls(
        self,
        target_roll_rad: float,
        target_pitch_rad: float,
        throttle: float,
        shield_requested: bool,
        dt: float
    ):
        """Update flight dynamics from controls input."""
        # 1. Attitude Smoothing
        self.roll_rad = exp_decay(self.roll_rad, target_roll_rad, 14.0, dt)
        self.pitch_rad = exp_decay(self.pitch_rad, target_pitch_rad, 14.0, dt)
        # Coupled yaw turn based on bank roll
        self.yaw_rad += math.sin(self.roll_rad) * config.YAW_FACTOR * dt

        # 2. Throttle & Velocity
        self.throttle = clamp(throttle, 0.0, 1.0)
        target_speed = config.SPEED_MIN + (config.SPEED_MAX - config.SPEED_MIN) * self.throttle
        self.speed = exp_decay(self.speed, target_speed, 8.0, dt)

        # Mach calculation (Mach 0.35 at idle to Mach 1.45 at afterburner)
        self.mach = 0.35 + (self.throttle * 1.10)

        # Altitude calculation based on pitch and speed
        self.altitude += math.sin(self.pitch_rad) * self.speed * 0.15 * dt
        self.altitude = clamp(self.altitude, 150.0, 45000.0)

        # 3. Deflector Shield Energy Mechanics
        if shield_requested and self.shield_energy > 0.0:
            self.is_shield_active = True
            self.shield_energy = max(0.0, self.shield_energy - (config.SHIELD_DRAIN_RATE * dt))
            if self.shield_energy <= 0.0:
                self.is_shield_active = False
                self.shield_recharge_cooldown = config.SHIELD_RECHARGE_DELAY * 1.5
        else:
            self.is_shield_active = False

            # Shield Regeneration
            if self.shield_recharge_cooldown > 0.0:
                self.shield_recharge_cooldown = max(0.0, self.shield_recharge_cooldown - dt)
            else:
                self.shield_energy = min(self.max_shield, self.shield_energy + (config.SHIELD_REGEN_RATE * dt))

        # 4. Combo Streak Timer
        if self.streak_timer > 0.0:
            self.streak_timer = max(0.0, self.streak_timer - dt)
            if self.streak_timer <= 0.0:
                self.streak = 0
