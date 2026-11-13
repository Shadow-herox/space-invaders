"""
MediaPipe Multi-Hand Pipeline for dual-hand tracking and tactical PiP rendering.
Extracts 21 3D landmarks for physical Left (Throttle/Shield) and Right (Flight Yoke/Trigger) hands.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import math
import cv2
import numpy as np
import pygame
import mediapipe as mp
import config


# MediaPipe hand skeleton connectivity
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17)                                # Palm base
]


@dataclass
class HandData:
    """Extracted features and landmarks for a single detected hand."""
    handedness: str                        # 'Right' (Flight Yoke) or 'Left' (Throttle/Shield)
    confidence: float
    landmarks_2d: List[Tuple[float, float]] = field(default_factory=list) # Normalized [0, 1]
    landmarks_3d: List[Tuple[float, float, float]] = field(default_factory=list)
    palm_size: float = 0.15                # Distance between Wrist (0) and Middle MCP (9)
    wrist_pos: Tuple[float, float] = (0.5, 0.5)
    middle_mcp: Tuple[float, float] = (0.5, 0.5)
    index_tip: Tuple[float, float] = (0.5, 0.5)


class HandTracker:
    """High-confidence dual-hand tracking engine."""

    def __init__(
        self,
        max_num_hands: int = config.MP_MAX_NUM_HANDS,
        min_detection_confidence: float = config.MP_MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence: float = config.MP_MIN_TRACKING_CONFIDENCE
    ):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        self.last_results: Dict[str, Optional[HandData]] = {
            'Right': None,  # Physical Right Hand (Flight Yoke & Weapons)
            'Left': None    # Physical Left Hand (Throttle & Shield)
        }

    def process_frame(self, frame_rgb: np.ndarray) -> Dict[str, Optional[HandData]]:
        """
        Process an RGB frame and extract structured HandData for Left and Right hands.
        Accounts for horizontal mirror compensation so physical right hand is classified as 'Right'.
        """
        results = {'Right': None, 'Left': None}
        if frame_rgb is None:
            self.last_results = results
            return results

        try:
            mp_res = self.hands.process(frame_rgb)
            if not mp_res.multi_hand_landmarks or not mp_res.multi_handedness:
                self.last_results = results
                return results

            # Map detected hands
            detected_hands = []
            for i, hand_lms in enumerate(mp_res.multi_hand_landmarks):
                # MediaPipe handedness label on horizontally mirrored image is inverted:
                # MP 'Left' label on mirrored frame = Physical Right Hand
                # MP 'Right' label on mirrored frame = Physical Left Hand
                raw_label = mp_res.multi_handedness[i].classification[0].label
                confidence = mp_res.multi_handedness[i].classification[0].score

                # Physical assignment
                physical_side = 'Right' if raw_label == 'Left' else 'Left'

                # Extract 21 landmark coords
                lms_2d = [(lm.x, lm.y) for lm in hand_lms.landmark]
                lms_3d = [(lm.x, lm.y, lm.z) for lm in hand_lms.landmark]

                w_x, w_y = lms_2d[0]
                m_x, m_y = lms_2d[9]
                palm_size = max(0.01, math.hypot(m_x - w_x, m_y - w_y))

                hand_obj = HandData(
                    handedness=physical_side,
                    confidence=confidence,
                    landmarks_2d=lms_2d,
                    landmarks_3d=lms_3d,
                    palm_size=palm_size,
                    wrist_pos=(w_x, w_y),
                    middle_mcp=(m_x, m_y),
                    index_tip=lms_2d[8]
                )
                detected_hands.append(hand_obj)

            # Assign to Left / Right without collision (if 2 hands detected)
            if len(detected_hands) == 1:
                results[detected_hands[0].handedness] = detected_hands[0]
            elif len(detected_hands) >= 2:
                # If labels are unique, assign directly
                h0, h1 = detected_hands[0], detected_hands[1]
                if h0.handedness != h1.handedness:
                    results[h0.handedness] = h0
                    results[h1.handedness] = h1
                else:
                    # Spatial fallback: The hand further to the right (higher x) is Physical Right Hand
                    if h0.wrist_pos[0] > h1.wrist_pos[0]:
                        h0.handedness = 'Right'
                        h1.handedness = 'Left'
                        results['Right'] = h0
                        results['Left'] = h1
                    else:
                        h0.handedness = 'Left'
                        h1.handedness = 'Right'
                        results['Left'] = h0
                        results['Right'] = h1

        except Exception as e:
            print(f"[HandTracker] Frame processing warning: {e}")

        self.last_results = results
        return results

    def render_pip_surface(
        self,
        frame_rgb: Optional[np.ndarray],
        pip_w: int = config.PIP_WIDTH,
        pip_h: int = config.PIP_HEIGHT
    ) -> pygame.Surface:
        """
        Create an aviation-styled glowing tactical PiP Pygame surface showing camera feed
        and glowing hand landmark skeletons.
        """
        surface = pygame.Surface((pip_w, pip_h))

        if frame_rgb is not None:
            # Resize RGB frame to PiP dimensions
            resized = cv2.resize(frame_rgb, (pip_w, pip_h))
            # Dim camera slightly for HUD contrast
            resized = (resized * 0.75).astype(np.uint8)
            # Convert to Pygame surface
            frame_surf = pygame.surfarray.make_surface(np.rot90(resized, 3)[:, ::-1])
            surface.blit(frame_surf, (0, 0))
        else:
            surface.fill((8, 12, 18))

        # Render tactical HUD grid overlay on PiP
        grid_color = (0, 180, 140, 60)
        grid_surf = pygame.Surface((pip_w, pip_h), pygame.SRCALPHA)
        pygame.draw.line(grid_surf, grid_color, (pip_w // 2, 0), (pip_w // 2, pip_h), 1)
        pygame.draw.line(grid_surf, grid_color, (0, pip_h // 2), (pip_w, pip_h // 2), 1)

        # Draw detected hand skeletons
        for side, hand in self.last_results.items():
            if hand is None:
                continue

            node_color = config.COLOR_PRIMARY if side == 'Right' else config.COLOR_SHIELD
            line_color = config.COLOR_EMERALD if side == 'Right' else (0, 160, 230)

            # Draw bones
            for start_idx, end_idx in HAND_CONNECTIONS:
                p1 = hand.landmarks_2d[start_idx]
                p2 = hand.landmarks_2d[end_idx]
                x1, y1 = int(p1[0] * pip_w), int(p1[1] * pip_h)
                x2, y2 = int(p2[0] * pip_w), int(p2[1] * pip_h)
                pygame.draw.line(grid_surf, line_color, (x1, y1), (x2, y2), 2)

            # Draw joint nodes
            for idx, lm in enumerate(hand.landmarks_2d):
                px, py = int(lm[0] * pip_w), int(lm[1] * pip_h)
                r = 4 if idx in [4, 8, 12, 16, 20] else 2 # Larger for fingertips
                pygame.draw.circle(grid_surf, node_color, (px, py), r)

            # Label hand side
            wx, wy = int(hand.wrist_pos[0] * pip_w), int(hand.wrist_pos[1] * pip_h)
            tag = "R: YOKE" if side == 'Right' else "L: THRTL"
            tag_color = config.COLOR_PRIMARY if side == 'Right' else config.COLOR_SHIELD

            # Draw tag box
            tag_x = max(10, min(pip_w - 65, wx - 25))
            tag_y = max(12, min(pip_h - 15, wy + 8))
            pygame.draw.rect(grid_surf, (5, 10, 15, 200), (tag_x - 3, tag_y - 2, 58, 14))
            # Pygame font render is blitted on the surface
            # Note: We blit simple dot indicator for speed

        surface.blit(grid_surf, (0, 0))

        # Cyber border with corner notches
        pygame.draw.rect(surface, config.COLOR_PRIMARY_DIM, (0, 0, pip_w, pip_h), 1)
        notch_len = 12
        notch_col = config.COLOR_PRIMARY
        # Top-left
        pygame.draw.line(surface, notch_col, (0, 0), (notch_len, 0), 2)
        pygame.draw.line(surface, notch_col, (0, 0), (0, notch_len), 2)
        # Top-right
        pygame.draw.line(surface, notch_col, (pip_w - 1, 0), (pip_w - 1 - notch_len, 0), 2)
        pygame.draw.line(surface, notch_col, (pip_w - 1, 0), (pip_w - 1, notch_len), 2)
        # Bottom-left
        pygame.draw.line(surface, notch_col, (0, pip_h - 1), (notch_len, pip_h - 1), 2)
        pygame.draw.line(surface, notch_col, (0, pip_h - 1), (0, pip_h - 1 - notch_len), 2)
        # Bottom-right
        pygame.draw.line(surface, notch_col, (pip_w - 1, pip_h - 1), (pip_w - 1 - notch_len, pip_h - 1), 2)
        pygame.draw.line(surface, notch_col, (pip_w - 1, pip_h - 1), (pip_w - 1, pip_h - 1 - notch_len), 2)

        return surface

    def release(self):
        """Release MediaPipe Hands resources."""
        if self.hands:
            self.hands.close()
