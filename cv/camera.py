"""
Thread-safe OpenCV VideoCapture wrapper with frame mirroring, automatic recovery,
and synthetic feed fallback when no hardware webcam is present.
"""

import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np
import config


class CameraStream:
    """Non-blocking threaded webcam frame grabber with fallback support."""

    def __init__(self, cam_index: int = config.CAM_INDEX, width: int = config.CAM_WIDTH, height: int = config.CAM_HEIGHT):
        self.cam_index = cam_index
        self.width = width
        self.height = height

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_available = False
        self.running = False
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None

        self.current_frame_bgr: Optional[np.ndarray] = None
        self.current_frame_rgb: Optional[np.ndarray] = None
        self.frame_count = 0
        self.fps_tracker = 0.0
        self._last_fps_time = time.time()
        self._frames_since_fps = 0

        self._init_camera()

    def _init_camera(self):
        """Attempt to open hardware video capture."""
        try:
            # Try specified cam_index, fallback to 0 or 1
            for idx in [self.cam_index, 0, 1]:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    cap.set(cv2.CAP_PROP_FPS, config.CAM_FPS)
                    # Test reading one frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self.cap = cap
                        self.is_available = True
                        self.cam_index = idx
                        print(f"[CameraStream] Hardware webcam active on index {idx} ({self.width}x{self.height})")
                        return
                    cap.release()
        except Exception as e:
            print(f"[CameraStream] Camera probe warning: {e}")

        print("[CameraStream] No hardware camera accessible. Activating synthetic grid fallback.")
        self.is_available = False
        self.cap = None

    def start(self):
        """Start the background frame capture thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True, name="CameraCaptureThread")
        self.thread.start()

    def _generate_synthetic_frame(self) -> np.ndarray:
        """Create a stylized animated cyan cockpit radar pattern when no camera is present."""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Background dark blue-slate
        frame[:, :] = (18, 12, 8) # BGR
        t = time.time()

        # Moving cyan grid lines
        grid_spacing = 40
        offset_y = int((t * 30) % grid_spacing)
        for y in range(offset_y, self.height, grid_spacing):
            cv2.line(frame, (0, y), (self.width, y), (40, 60, 20), 1)
        for x in range(0, self.width, grid_spacing):
            cv2.line(frame, (x, 0), (x, self.height), (40, 60, 20), 1)

        # Center reticle & text
        cx, cy = self.width // 2, self.height // 2
        cv2.circle(frame, (cx, cy), 60, (180, 230, 0), 1)
        cv2.circle(frame, (cx, cy), 3, (180, 230, 0), -1)

        # Status text
        cv2.putText(frame, "SIMULATED SENSOR FEED", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 230, 0), 2)
        cv2.putText(frame, "MOUSE & KEYBOARD MODE ACTIVE", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 180, 255), 1)
        cv2.putText(frame, "TAB TO TOGGLE CONTROLS", (20, self.height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1)

        return frame

    def _capture_loop(self):
        """Background thread continually grabbing latest frame."""
        target_dt = 1.0 / config.CAM_FPS

        while self.running:
            loop_start = time.time()

            if self.is_available and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    # Mirror frame horizontally so left is left and right is right
                    frame_bgr = cv2.flip(frame, 1)
                    if frame_bgr.shape[1] != self.width or frame_bgr.shape[0] != self.height:
                        frame_bgr = cv2.resize(frame_bgr, (self.width, self.height))
                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                    with self.lock:
                        self.current_frame_bgr = frame_bgr
                        self.current_frame_rgb = frame_rgb
                        self.frame_count += 1
                else:
                    # If hardware disconnected, use synthetic
                    frame_bgr = self._generate_synthetic_frame()
                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    with self.lock:
                        self.current_frame_bgr = frame_bgr
                        self.current_frame_rgb = frame_rgb
                        self.frame_count += 1
            else:
                frame_bgr = self._generate_synthetic_frame()
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                with self.lock:
                    self.current_frame_bgr = frame_bgr
                    self.current_frame_rgb = frame_rgb
                    self.frame_count += 1

            # Update FPS calculation
            self._frames_since_fps += 1
            now = time.time()
            if now - self._last_fps_time >= 1.0:
                self.fps_tracker = self._frames_since_fps / (now - self._last_fps_time)
                self._frames_since_fps = 0
                self._last_fps_time = now

            elapsed = time.time() - loop_start
            sleep_time = max(0.001, target_dt - elapsed)
            time.sleep(sleep_time)

    def get_latest_frame(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Thread-safe retrieval of latest frame.
        Returns (frame_rgb, frame_bgr).
        """
        with self.lock:
            if self.current_frame_rgb is not None:
                return self.current_frame_rgb.copy(), self.current_frame_bgr.copy()
            return None, None

    def stop(self):
        """Stop background capture thread and release hardware resources."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
