"""
Procedural Audio Synthesizer for Vision Pilot.
Generates retro-futuristic combat & cockpit sound effects on the fly using
NumPy waveform synthesis and pygame.sndarray. Zero external audio assets required.
"""

import math
from typing import Optional, Dict
import numpy as np
import pygame


class SoundSynthesizer:
    """Procedural audio engine creating SFX and dynamic engine drone."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.enabled = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.engine_channel: Optional[pygame.mixer.Channel] = None
        self.engine_sound: Optional[pygame.mixer.Sound] = None
        self.last_engine_throttle = -1.0
        self.muted = False

        self._init_audio()

    def _init_audio(self):
        """Initialize pygame mixer and synthesize all sound buffers."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            self.enabled = True
            self._generate_all_sounds()
        except Exception as e:
            print(f"[SoundSynthesizer] Audio initialization warning: {e}. Running in silent mode.")
            self.enabled = False

    def toggle_mute(self) -> bool:
        """Toggle mute state."""
        self.muted = not self.muted
        if self.muted and self.engine_channel:
            self.engine_channel.stop()
        return self.muted

    def _create_stereo_sound(self, mono_samples: np.ndarray) -> Optional[pygame.mixer.Sound]:
        """Convert a 1D float array [-1.0, 1.0] to a 16-bit signed stereo Pygame Sound."""
        if not self.enabled:
            return None
        # Clip to safe limits
        mono_clamped = np.clip(mono_samples, -1.0, 1.0)
        int16_samples = (mono_clamped * 32767.0).astype(np.int16)
        stereo_samples = np.ascontiguousarray(np.column_stack([int16_samples, int16_samples]))
        return pygame.sndarray.make_sound(stereo_samples)

    def _generate_all_sounds(self):
        """Pre-generate procedural sound effects into memory."""
        sr = self.sample_rate

        # 1. Standard Laser Chirp (0.12s, 950Hz -> 240Hz)
        dur = 0.12
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        freq_sweep = np.linspace(950, 240, len(t))
        phase = 2 * np.pi * np.cumsum(freq_sweep) / sr
        envelope = np.exp(-18 * t)
        noise = (np.random.rand(len(t)) * 2 - 1) * 0.15 * envelope
        laser_wave = (np.sin(phase) * 0.8 + noise) * envelope
        self.sounds['laser'] = self._create_stereo_sound(laser_wave)

        # 2. Heavy Plasma Cannon (0.22s, 420Hz -> 75Hz with bass punch)
        dur = 0.22
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        freq_sweep = np.geomspace(420, 75, len(t))
        phase = 2 * np.pi * np.cumsum(freq_sweep) / sr
        sub_phase = 2 * np.pi * 55 * t
        envelope = np.exp(-12 * t)
        heavy_wave = (np.sin(phase) * 0.6 + np.sin(sub_phase) * 0.4) * envelope
        # Add subtle overdrive distortion
        heavy_wave = np.tanh(heavy_wave * 1.5)
        self.sounds['heavy_laser'] = self._create_stereo_sound(heavy_wave)

        # 3. Target Hit Spark (0.06s metallic ping)
        dur = 0.06
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        hit_wave = np.sin(2 * np.pi * 1400 * t) * np.exp(-35 * t) * 0.5
        hit_wave += (np.random.rand(len(t)) * 2 - 1) * 0.3 * np.exp(-45 * t)
        self.sounds['hit'] = self._create_stereo_sound(hit_wave)

        # 4. Small Explosion / Drone Destruction (0.35s)
        dur = 0.35
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        noise = (np.random.rand(len(t)) * 2 - 1)
        # Low frequency decay
        decay = np.exp(-8 * t)
        sub_thump = np.sin(2 * np.pi * 60 * t) * np.exp(-10 * t) * 0.6
        exp_small = (noise * 0.7 + sub_thump) * decay
        self.sounds['explosion_small'] = self._create_stereo_sound(exp_small)

        # 5. Large Boss / Dreadnought Explosion (0.75s heavy rumble)
        dur = 0.75
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        noise = (np.random.rand(len(t)) * 2 - 1)
        decay = np.exp(-4.5 * t)
        sub_rumble = np.sin(2 * np.pi * np.linspace(80, 30, len(t)) * t) * np.exp(-4 * t) * 0.8
        exp_large = (noise * 0.6 + sub_rumble) * decay
        exp_large = np.tanh(exp_large * 1.8)
        self.sounds['explosion_large'] = self._create_stereo_sound(exp_large)

        # 6. Deflector Shield Engage (0.28s rising harmonic shimmer)
        dur = 0.28
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        f_rise = np.linspace(350, 780, len(t))
        p1 = 2 * np.pi * np.cumsum(f_rise) / sr
        p2 = 2 * np.pi * np.cumsum(f_rise * 1.5) / sr
        env = np.sin(np.pi * t / dur) ** 0.5
        shield_wave = (np.sin(p1) * 0.5 + np.sin(p2) * 0.3) * env
        self.sounds['shield_up'] = self._create_stereo_sound(shield_wave)

        # 7. Shield Impact Deflection (0.15s resonant vibration)
        dur = 0.15
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        f_wobble = 550 + 120 * np.sin(2 * np.pi * 40 * t)
        p_wobble = 2 * np.pi * np.cumsum(f_wobble) / sr
        shield_hit = np.sin(p_wobble) * np.exp(-15 * t) * 0.7
        self.sounds['shield_hit'] = self._create_stereo_sound(shield_hit)

        # 8. Target Lock-On Beep (0.09s tactical twin pip)
        dur = 0.09
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        lock_wave = np.sin(2 * np.pi * 1250 * t) * 0.4
        self.sounds['lock_on'] = self._create_stereo_sound(lock_wave)

        # 9. Warning Klaxon (0.18s alarm pulse)
        dur = 0.18
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        warn_wave = (np.sin(2 * np.pi * 680 * t) * 0.5 + np.sin(2 * np.pi * 850 * t) * 0.3) * np.sin(np.pi * t / dur)
        self.sounds['warning'] = self._create_stereo_sound(warn_wave)

        # 10. UI Click / Select (0.04s)
        dur = 0.04
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        click_wave = np.sin(2 * np.pi * 880 * t) * np.exp(-40 * t) * 0.35
        self.sounds['ui_click'] = self._create_stereo_sound(click_wave)

        # Initialize looping turbine engine drone
        self._init_engine_drone()

    def _init_engine_drone(self):
        """Generate a seamless 1.0s looping turbine drone buffer."""
        if not self.enabled:
            return
        sr = self.sample_rate
        dur = 1.0
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        # Dual frequency drone with sub-rumble and subtle jet noise
        drone = (
            np.sin(2 * np.pi * 75 * t) * 0.35 +
            np.sin(2 * np.pi * 150 * t) * 0.20 +
            (np.random.rand(len(t)) * 2 - 1) * 0.06
        )
        self.engine_sound = self._create_stereo_sound(drone)

    def play(self, sound_name: str, volume: float = 1.0):
        """Play a pre-generated one-shot sound effect."""
        if not self.enabled or self.muted:
            return
        sound = self.sounds.get(sound_name)
        if sound:
            sound.set_volume(max(0.0, min(1.0, volume)))
            sound.play()

    def update_engine(self, throttle: float):
        """
        Update dynamic engine turbine sound volume and pitch based on throttle (0.0 to 1.0).
        """
        if not self.enabled or self.muted or not self.engine_sound:
            return

        throttle = max(0.0, min(1.0, throttle))
        if self.engine_channel is None or not self.engine_channel.get_busy():
            self.engine_channel = self.engine_sound.play(loops=-1)

        if self.engine_channel:
            # Volume scales dynamically with throttle
            vol = 0.15 + (throttle * 0.35)
            self.engine_channel.set_volume(vol)
