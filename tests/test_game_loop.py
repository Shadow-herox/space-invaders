"""
Integration test for full Game Loop, Frame Updates, Combat State Progression,
and PiP generation over multiple simulated frames.
"""

import sys
import os
import unittest
import numpy as np
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Run pygame in dummy video driver for headless testing if needed
os.environ["SDL_VIDEODRIVER"] = "dummy"

import config
from main import VisionPilotGame
from ui.screens import GameState


class TestGameIntegration(unittest.TestCase):
    def test_full_game_lifecycle(self):
        # Initialize full game application
        game = VisionPilotGame()
        self.assertEqual(game.state, GameState.START_MENU)

        # 1. Simulate Start Menu Frames
        for _ in range(5):
            game.screens.update(0.016)
            game._render(game.gesture_detector.state, None)

        # 2. Simulate Launching Sortie
        game.reset_game()
        self.assertEqual(game.state, GameState.PLAYING)
        self.assertEqual(game.aircraft.health, 100.0)

        # 3. Simulate Flight and Weapon Discharge
        for frame_idx in range(60):
            # Set controls
            controls = game.gesture_detector.state
            controls.aim_x = config.SCREEN_WIDTH * 0.5
            controls.aim_y = config.SCREEN_HEIGHT * 0.5
            controls.throttle = 0.8
            controls.target_roll_rad = 0.1
            controls.target_pitch_rad = 0.05
            # Fire weapons every 5th frame
            controls.is_firing = (frame_idx % 5 == 0)
            controls.is_shield_active = (frame_idx % 20 > 10)

            game._update_playing(controls, dt=0.016)
            game._render(controls, None)

        # Verify lasers were discharged and aircraft moved
        self.assertGreater(game.aircraft.shots_fired, 0)
        self.assertGreater(game.aircraft.speed, config.SPEED_MIN)

        # 4. Simulate Destroying All Drones in Wave
        initial_wave = game.enemies.wave_number
        for drone in list(game.enemies.drones):
            drone.health = 0
            game.aircraft.add_score(drone.points)
        game.enemies.drones.clear()

        # Update should spawn next wave
        game.enemies.update(0.016, game.aircraft.speed, 0, 0, game.weapons)
        self.assertEqual(game.enemies.wave_number, initial_wave + 1)
        self.assertGreater(game.aircraft.score, 0)

        # 5. Clean teardown
        game.camera.stop()
        game.hand_tracker.release()
        pygame.quit()


if __name__ == '__main__':
    unittest.main()
