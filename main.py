"""
Vision Pilot — Gesture Controlled Flight Simulator & Combat Game
Main Application Entry Point, Game Loop, Event Handling, Subsystem Coordination,
and Seamless CV/Mouse Integration.
"""

import sys
import os
import time
import math
import pygame

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils.math_helpers import clamp
from utils.sound_synth import SoundSynthesizer
from cv.camera import CameraStream
from cv.hand_tracker import HandTracker
from cv.gesture_detector import GestureDetector, FlightControlsState
from engine.aircraft import PlayerAircraft
from engine.weapons import WeaponSystem
from engine.enemies import EnemyManager, EnemyType
from engine.particles import ParticleSystem
from ui.radar import TacticalRadar
from ui.hud import AviationHUD
from ui.screens import ScreenManager, GameState


class VisionPilotGame:
    """Core Game Controller coordinating CV, physics, combat, HUD, and audio."""

    def __init__(self):
        # 1. Initialize Pygame Engine
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            pygame.DOUBLEBUF | pygame.HWSURFACE
        )
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.START_MENU

        # 2. Subsystems Initialization
        print("[VisionPilot] Initializing audio synthesizer...")
        self.sound = SoundSynthesizer()

        print("[VisionPilot] Initializing camera thread...")
        self.camera = CameraStream()
        self.camera.start()

        print("[VisionPilot] Initializing MediaPipe hand tracker...")
        self.hand_tracker = HandTracker()
        self.gesture_detector = GestureDetector()

        # If camera not detected, default to mouse fallback mode
        if not self.camera.is_available:
            self.gesture_detector.mouse_mode = True

        print("[VisionPilot] Initializing simulation & combat engines...")
        self.aircraft = PlayerAircraft()
        self.weapons = WeaponSystem()
        self.enemies = EnemyManager()
        self.particles = ParticleSystem()

        print("[VisionPilot] Initializing HUD & Radar instruments...")
        self.radar = TacticalRadar()
        self.hud = AviationHUD()
        self.screens = ScreenManager()

        # Wheel scroll delta cache
        self.wheel_delta = 0

    def reset_game(self):
        """Reset player and enemy states for a new flight sortie."""
        self.aircraft = PlayerAircraft()
        self.weapons = WeaponSystem()
        self.enemies = EnemyManager()
        self.particles = ParticleSystem()
        self.state = GameState.PLAYING
        print("[VisionPilot] Flight sortie initiated.")

    def run(self):
        """Main application loop running at 60 FPS."""
        last_time = time.time()

        while self.running:
            # Calculate delta time
            now = time.time()
            dt = clamp(now - last_time, 0.001, 0.05) # Prevent physics exploding on lag
            last_time = now

            # 1. Handle Window & Input Events
            self._handle_events()

            # 2. Grab CV Frame & Extract Hand Landmarks
            frame_rgb, frame_bgr = self.camera.get_latest_frame()
            hands = self.hand_tracker.process_frame(frame_rgb)
            pip_surf = self.hand_tracker.render_pip_surface(frame_rgb)

            # 3. Extract Flight Controls State
            if self.gesture_detector.mouse_mode:
                mouse_pos = pygame.mouse.get_pos()
                mouse_btns = pygame.mouse.get_pressed()
                keys = pygame.key.get_pressed()
                controls = self.gesture_detector.process_mouse_keyboard_fallback(
                    mouse_pos=mouse_pos,
                    mouse_buttons=mouse_btns,
                    keys_pressed=keys,
                    wheel_delta=self.wheel_delta,
                    dt=dt
                )
            else:
                controls = self.gesture_detector.process_hands(hands, dt=dt)

            self.wheel_delta = 0 # Reset scroll delta

            # 4. State-Based Game Logic Updates
            if self.state == GameState.PLAYING:
                self._update_playing(controls, dt)
            elif self.state == GameState.START_MENU:
                self.screens.update(dt)
            elif self.state == GameState.PAUSED:
                self.screens.update(dt)
            elif self.state == GameState.GAME_OVER:
                self.screens.update(dt)

            # 5. Render Everything
            self._render(controls, pip_surf)

            # Flip double buffer and enforce 60 FPS
            pygame.display.flip()
            self.clock.tick(config.FPS)

        self._cleanup()

    def _handle_events(self):
        """Process keyboard, mouse, and system events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                # Global Hotkeys
                if event.key == pygame.K_TAB:
                    # Toggle Mouse / CV mode
                    self.gesture_detector.toggle_mouse_mode()
                    self.sound.play('ui_click')

                elif event.key == pygame.K_m:
                    # Toggle Audio Mute
                    is_muted = self.sound.toggle_mute()
                    print(f"[VisionPilot] Audio {'MUTED' if is_muted else 'ACTIVE'}")

                elif event.key == pygame.K_c:
                    # Recalibrate neutral yoke
                    right = self.hand_tracker.last_results.get('Right')
                    left = self.hand_tracker.last_results.get('Left')
                    self.gesture_detector.recalibrate_neutral(right, left)
                    self.sound.play('lock_on')

                elif event.key == pygame.K_ESCAPE:
                    # Pause / Unpause
                    if self.state == GameState.PLAYING:
                        self.state = GameState.PAUSED
                        self.sound.play('ui_click')
                    elif self.state == GameState.PAUSED:
                        self.state = GameState.PLAYING
                        self.sound.play('ui_click')
                    elif self.state == GameState.GAME_OVER:
                        self.state = GameState.START_MENU
                        self.sound.play('ui_click')

                # Menu Specific Key Events
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.state == GameState.START_MENU:
                        self.reset_game()
                        self.sound.play('lock_on')
                    elif self.state == GameState.GAME_OVER:
                        self.reset_game()
                        self.sound.play('lock_on')

                elif event.key == pygame.K_q and self.state == GameState.PAUSED:
                    self.state = GameState.START_MENU
                    self.sound.play('ui_click')

            elif event.type == pygame.MOUSEWHEEL:
                self.wheel_delta += event.y

    def _update_playing(self, controls: FlightControlsState, dt: float):
        """Update simulation physics, weapons, enemies, collisions, and sound effects."""
        # 1. Update Player Aircraft Flight Dynamics
        self.aircraft.update_controls(
            target_roll_rad=controls.target_roll_rad,
            target_pitch_rad=controls.target_pitch_rad,
            throttle=controls.throttle,
            shield_requested=controls.is_shield_active,
            dt=dt
        )
        self.aircraft.wave_number = self.enemies.wave_number

        # Update dynamic engine drone audio
        self.sound.update_engine(self.aircraft.throttle)

        # 2. Weapon Firing Logic
        if controls.is_firing:
            fired = self.weapons.fire_laser(
                aim_screen_x=controls.aim_x,
                aim_screen_y=controls.aim_y,
                player_speed=self.aircraft.speed,
                player_roll_rad=self.aircraft.roll_rad,
                player_pitch_rad=self.aircraft.pitch_rad
            )
            if fired:
                self.aircraft.record_shot()
                self.sound.play('laser', volume=0.7)

        # 3. Update Weapons & Projectiles in 3D
        self.weapons.update(dt=dt, player_speed=self.aircraft.speed)

        # 4. Update Enemy Drones & Combat AI
        self.enemies.update(
            dt=dt,
            player_speed=self.aircraft.speed,
            player_x=self.aircraft.x,
            player_y=self.aircraft.y,
            weapons_sys=self.weapons
        )

        # 5. Update Particles & 3D Starfield
        self.particles.update(
            dt=dt,
            player_speed=self.aircraft.speed,
            player_roll_rad=self.aircraft.roll_rad,
            player_pitch_rad=self.aircraft.pitch_rad
        )

        # 6. Update Tactical Radar & HUD timers
        self.radar.update(dt)
        self.hud.update(dt)

        # ==========================================
        # 7. Collision Detection & Combat Resolution
        # ==========================================

        # A. Player Lasers vs Enemy Drones
        for laser in self.weapons.player_lasers:
            for drone in self.enemies.drones:
                # 3D bounding sphere distance
                dist = math.sqrt(
                    (laser.x - drone.x) ** 2 +
                    (laser.y - drone.y) ** 2 +
                    (laser.z - drone.z) ** 2
                )
                if dist <= drone.radius_3d:
                    # Confirmed Hit!
                    drone.health -= laser.damage
                    laser.z = -100 # Destroy laser bolt
                    self.aircraft.record_hit()
                    self.particles.spawn_hit_sparks(drone.x, drone.y, drone.z, count=10)
                    self.sound.play('hit', volume=0.8)

                    # Check Drone Destruction
                    if drone.health <= 0:
                        is_boss = (drone.drone_type == EnemyType.DREADNOUGHT)
                        self.particles.spawn_explosion(drone.x, drone.y, drone.z, count=50 if is_boss else 35, is_boss=is_boss)
                        self.aircraft.add_score(drone.points)
                        if is_boss:
                            self.sound.play('explosion_large', volume=1.0)
                        else:
                            self.sound.play('explosion_small', volume=0.85)
                    break

        # Remove destroyed drones
        self.enemies.drones = [d for d in self.enemies.drones if d.health > 0]

        # B. Enemy Plasma vs Player Cockpit (z approaching <= 40)
        for plasma in self.weapons.enemy_projectiles:
            if plasma.z <= 45.0:
                # Check cockpit center distance
                if math.hypot(plasma.x, plasma.y) < 180.0:
                    plasma.z = -100 # Consumed
                    absorbed, fatal = self.aircraft.apply_damage(plasma.damage)
                    if absorbed:
                        self.particles.trigger_shield_impact()
                        self.sound.play('shield_hit', volume=0.9)
                    else:
                        self.particles.trigger_damage_flash()
                        self.sound.play('warning', volume=0.9)

                    if fatal:
                        self.state = GameState.GAME_OVER
                        self.sound.play('explosion_large', volume=1.0)

        # C. Direct Drone Collisions
        for drone in self.enemies.drones:
            if drone.z <= 50.0:
                if math.hypot(drone.x, drone.y) < drone.radius_3d + 60.0:
                    drone.health = 0 # Drone explodes on impact
                    self.particles.spawn_explosion(drone.x, drone.y, drone.z, count=40)
                    absorbed, fatal = self.aircraft.apply_damage(config.COLLISION_DAMAGE)
                    if absorbed:
                        self.particles.trigger_shield_impact()
                        self.sound.play('shield_hit', volume=0.9)
                    else:
                        self.particles.trigger_damage_flash()
                        self.sound.play('warning', volume=0.9)

                    if fatal:
                        self.state = GameState.GAME_OVER
                        self.sound.play('explosion_large', volume=1.0)

    def _render(self, controls: FlightControlsState, pip_surf: pygame.Surface):
        """Render complete frame according to active state."""
        # 1. Clear Cockpit Slate Canvas
        self.screen.fill(config.COLOR_BG)

        if self.state == GameState.START_MENU:
            # Start Menu Screen
            self.screens.draw_start_menu(
                surface=self.screen,
                has_right_hand=controls.has_right_hand,
                has_left_hand=controls.has_left_hand,
                mouse_mode=self.gesture_detector.mouse_mode,
                pip_surface=pip_surf
            )
            return

        # 2. Render 3D World Elements (Starfield, Enemies, Lasers, Particles)
        self.particles.draw(
            surface=self.screen,
            player_roll_rad=self.aircraft.roll_rad,
            player_pitch_rad=self.aircraft.pitch_rad,
            shield_active=self.aircraft.is_shield_active,
            shield_energy=self.aircraft.shield_energy
        )

        self.enemies.draw(
            surface=self.screen,
            player_roll_rad=self.aircraft.roll_rad,
            player_pitch_rad=self.aircraft.pitch_rad
        )

        self.weapons.draw(
            surface=self.screen,
            player_roll_rad=self.aircraft.roll_rad,
            player_pitch_rad=self.aircraft.pitch_rad
        )

        # 3. Render Tactical Aviation HUD
        locked_drone = self.hud.draw(
            surface=self.screen,
            aircraft=self.aircraft,
            controls_state=controls,
            drones=self.enemies.drones,
            pip_surface=pip_surf,
            enemy_projectiles=self.weapons.enemy_projectiles
        )

        # 4. Render 2D Tactical Radar
        self.radar.draw(
            surface=self.screen,
            drones=self.enemies.drones,
            font=self.hud.font_tiny,
            locked_drone=locked_drone
        )

        # 5. Render Wave Clear Banner
        if self.enemies.wave_clear_banner_timer > 0.0:
            self.screens.draw_wave_clear_banner(
                surface=self.screen,
                wave_number=self.enemies.wave_number,
                is_boss=self.enemies.is_boss_wave
            )

        # 6. Render Overlays (Pause / Game Over)
        if self.state == GameState.PAUSED:
            self.screens.draw_pause_menu(self.screen, self.gesture_detector.mouse_mode)
        elif self.state == GameState.GAME_OVER:
            self.screens.draw_game_over(self.screen, self.aircraft)

    def _cleanup(self):
        """Release hardware and media resources gracefully."""
        print("[VisionPilot] Shutting down systems...")
        self.camera.stop()
        self.hand_tracker.release()
        pygame.quit()
        sys.exit(0)


def main():
    """Application Entry Point."""
    app = VisionPilotGame()
    app.run()


if __name__ == "__main__":
    main()
