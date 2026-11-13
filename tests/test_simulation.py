"""
Unit and Integration Test Suite for Vision Pilot.
Tests math helpers, procedural audio, gesture extraction, 3D flight physics,
combat resolution, and headless rendering loop.
"""

import sys
import os
import math
import unittest
import numpy as np
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.math_helpers import (
    clamp, lerp, exp_decay, remap, normalize_angle,
    project_3d, rotate_2d, rotate_points_2d, world_to_radar
)
from utils.sound_synth import SoundSynthesizer
from cv.hand_tracker import HandData
from cv.gesture_detector import GestureDetector, FlightControlsState
from engine.aircraft import PlayerAircraft
from engine.weapons import WeaponSystem
from engine.enemies import EnemyManager, EnemyType
from engine.particles import ParticleSystem
from ui.radar import TacticalRadar
from ui.hud import AviationHUD
from ui.screens import ScreenManager, GameState


class TestMathHelpers(unittest.TestCase):
    def test_clamp_and_lerp(self):
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(-5, 0, 10), 0)
        self.assertEqual(clamp(15, 0, 10), 10)
        self.assertAlmostEqual(lerp(0.0, 10.0, 0.5), 5.0)

    def test_project_3d(self):
        # Center object at z=640 should project to screen center
        sx, sy, scale, vis = project_3d(0, 0, 640.0, 1280, 720, 640.0)
        self.assertAlmostEqual(sx, 640.0)
        self.assertAlmostEqual(sy, 360.0)
        self.assertAlmostEqual(scale, 1.0)
        self.assertTrue(vis)

        # Offscreen object
        sx2, sy2, scale2, vis2 = project_3d(50000, 0, 640.0, 1280, 720, 640.0)
        self.assertFalse(vis2)

    def test_radar_projection(self):
        # Target at world (0, 1000) with max_range 2000 and radius 60
        rx, ry, in_range = world_to_radar(0.0, 1000.0, 2000.0, 60.0, (100, 100))
        self.assertTrue(in_range)
        self.assertEqual(rx, 100)
        self.assertEqual(ry, 100 - 30)


class TestSoundSynth(unittest.TestCase):
    def test_procedural_sounds(self):
        synth = SoundSynthesizer()
        expected_sounds = ['laser', 'heavy_laser', 'hit', 'explosion_small', 'explosion_large', 'shield_up', 'shield_hit', 'lock_on', 'warning', 'ui_click']
        for s in expected_sounds:
            self.assertIn(s, synth.sounds)
            if synth.enabled:
                self.assertIsNotNone(synth.sounds[s])


class TestGestureDetection(unittest.TestCase):
    def setUp(self):
        self.detector = GestureDetector()

    def test_right_hand_features(self):
        # Create synthetic right hand landmarks
        # Wrist at (0.7, 0.6), Middle MCP at (0.7, 0.4) -> Hand pointing straight up
        lms_2d = [(0.7, 0.6)] * 21
        lms_2d[0] = (0.7, 0.6)  # Wrist
        lms_2d[9] = (0.7, 0.4)  # Middle MCP
        # Index extended
        lms_2d[8] = (0.7, 0.1)  # Index tip extended
        # Middle, Ring, Pinky curled
        lms_2d[12] = (0.7, 0.5)
        lms_2d[16] = (0.7, 0.55)
        lms_2d[20] = (0.7, 0.58)

        right_hand = HandData(
            handedness='Right',
            confidence=0.95,
            landmarks_2d=lms_2d,
            palm_size=0.20,
            wrist_pos=(0.7, 0.6),
            middle_mcp=(0.7, 0.4),
            index_tip=(0.7, 0.1)
        )

        controls = self.detector.process_hands({'Right': right_hand, 'Left': None}, dt=0.016)
        self.assertTrue(controls.has_right_hand)
        self.assertFalse(controls.has_left_hand)
        self.assertTrue(controls.is_firing) # Trigger should be engaged!

    def test_left_hand_shield(self):
        # Create synthetic left hand open palm
        lms_2d = [(0.3, 0.5)] * 21
        lms_2d[0] = (0.3, 0.5) # Wrist
        lms_2d[8] = (0.3, 0.1) # Index tip
        lms_2d[12] = (0.32, 0.08) # Middle tip
        lms_2d[16] = (0.34, 0.12) # Ring tip
        lms_2d[20] = (0.36, 0.15) # Pinky tip

        left_hand = HandData(
            handedness='Left',
            confidence=0.95,
            landmarks_2d=lms_2d,
            palm_size=0.15,
            wrist_pos=(0.3, 0.5)
        )

        controls = self.detector.process_hands({'Right': None, 'Left': left_hand}, dt=0.016)
        self.assertTrue(controls.has_left_hand)
        self.assertTrue(controls.is_shield_active) # Shield should be active!


class TestSimulationAndCombat(unittest.TestCase):
    def test_aircraft_shield_and_damage(self):
        aircraft = PlayerAircraft()
        aircraft.is_shield_active = True
        aircraft.shield_energy = 100.0

        # Shield absorbs damage
        absorbed, fatal = aircraft.apply_damage(30.0)
        self.assertTrue(absorbed)
        self.assertFalse(fatal)
        self.assertEqual(aircraft.health, 100.0)
        self.assertLess(aircraft.shield_energy, 100.0)

        # Hull damage when shield inactive
        aircraft.is_shield_active = False
        absorbed, fatal = aircraft.apply_damage(40.0)
        self.assertFalse(absorbed)
        self.assertEqual(aircraft.health, 60.0)

    def test_weapons_and_enemies(self):
        weapons = WeaponSystem()
        enemies = EnemyManager()
        self.assertGreater(len(enemies.drones), 0)

        fired = weapons.fire_laser(640, 360, player_speed=500.0, player_roll_rad=0.0, player_pitch_rad=0.0)
        self.assertTrue(fired)
        self.assertEqual(len(weapons.player_lasers), 2) # Twin lasers


class TestHeadlessRendering(unittest.TestCase):
    def test_render_pipeline(self):
        pygame.init()
        surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        aircraft = PlayerAircraft()
        weapons = WeaponSystem()
        enemies = EnemyManager()
        particles = ParticleSystem()
        radar = TacticalRadar()
        hud = AviationHUD()
        screens = ScreenManager()
        controls = FlightControlsState()

        # Update systems
        weapons.update(0.016, aircraft.speed)
        enemies.update(0.016, aircraft.speed, 0, 0, weapons)
        particles.update(0.016, aircraft.speed, 0, 0)
        radar.update(0.016)
        hud.update(0.016)

        # Render pass
        particles.draw(surf, 0, 0, False, 100.0)
        enemies.draw(surf, 0, 0)
        weapons.draw(surf, 0, 0)
        hud.draw(surf, aircraft, controls, enemies.drones, None, weapons.enemy_projectiles)
        radar.draw(surf, enemies.drones, hud.font_tiny)
        screens.draw_start_menu(surf, True, True, False, None)

        self.assertIsNotNone(surf)


if __name__ == '__main__':
    unittest.main()
