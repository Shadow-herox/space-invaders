"""
Vision Pilot - Configuration and Constants
Aviation-grade styling, physics tuning, and system parameters.
"""

# ==========================================
# Display & Engine Settings
# ==========================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
WINDOW_TITLE = "Vision Pilot — Gesture Controlled Flight Simulator & Combat Game"

# ==========================================
# Aviation Minimalist Palette (HUD & World)
# ==========================================
COLOR_BG = (10, 14, 20)             # Deep cockpit slate (#0A0E14)
COLOR_SPACE_VOID = (6, 9, 14)       # Deepest space background
COLOR_PRIMARY = (0, 230, 180)       # Glowing Cyan HUD (#00E6B4)
COLOR_PRIMARY_DIM = (0, 120, 95)    # Dimmed cyan
COLOR_EMERALD = (0, 255, 140)       # Target Lock & Safe Status (#00FF8C)
COLOR_WARNING = (255, 180, 0)       # Caution / Warning Amber (#FFB400)
COLOR_DANGER = (255, 55, 75)        # Enemy / Critical Damage Red (#FF374B)
COLOR_SHIELD = (0, 190, 255)        # Energy Deflector Cyan-Blue (#00BEFF)
COLOR_WHITE = (240, 245, 255)       # Crisp Text White
COLOR_MUTED = (100, 120, 140)       # Subtle secondary text
COLOR_GRID = (0, 180, 140, 30)      # Horizon background grid
COLOR_HUD_PANEL = (12, 18, 26, 210) # Translucent HUD backing

# ==========================================
# Computer Vision & Camera Pipeline
# ==========================================
CAM_INDEX = 0
CAM_WIDTH = 640
CAM_HEIGHT = 480
CAM_FPS = 30

# Picture-in-Picture (PiP) Display
PIP_WIDTH = 260
PIP_HEIGHT = 195
PIP_MARGIN = 20
PIP_BORDER_COLOR = COLOR_PRIMARY
PIP_BG_COLOR = (8, 12, 18, 230)

# MediaPipe Confidence Thresholds
MP_MAX_NUM_HANDS = 2
MP_MIN_DETECTION_CONFIDENCE = 0.70
MP_MIN_TRACKING_CONFIDENCE = 0.70

# Gesture Thresholds
TRIGGER_EXTEND_RATIO = 1.25         # Index finger extension relative to palm reference
SHIELD_EXTEND_RATIO = 1.20          # 4-fingers extension for open palm
PITCH_DEADZONE = 0.04               # Center deadzone for pitch
ROLL_DEADZONE_DEG = 4.0             # Center deadzone for hand roll
AIM_SMOOTHING = 0.22                # Lerp factor for crosshair aiming
ATTITUDE_SMOOTHING = 0.16           # Lerp factor for roll and pitch
THROTTLE_SMOOTHING = 0.12          # Lerp factor for throttle speed

# ==========================================
# Flight Physics & 3D Perspective Projection
# ==========================================
FOCAL_LENGTH = 640.0                # Perspective projection focal length
Z_MIN = 35.0                        # Near clipping plane
Z_MAX = 2200.0                      # Far clipping plane
SPEED_MIN = 220.0                   # Idle cruise speed (units/s)
SPEED_MAX = 980.0                   # Full afterburner speed (units/s)
PITCH_MAX_DEG = 35.0                # Max nose pitch angle
ROLL_MAX_DEG = 50.0                 # Max wing roll angle
YAW_FACTOR = 0.4                    # Coupled yaw turn factor

# ==========================================
# Player Aircraft Attributes
# ==========================================
PLAYER_MAX_HEALTH = 100.0
PLAYER_MAX_SHIELD = 100.0
SHIELD_DRAIN_RATE = 28.0            # Energy drained per second when active
SHIELD_REGEN_RATE = 14.0            # Energy recovered per second when idle
SHIELD_RECHARGE_DELAY = 1.2         # Delay in seconds before shield regens after use
COLLISION_DAMAGE = 35.0             # Damage received when hitting a drone directly

# ==========================================
# Weapons & Combat
# ==========================================
LASER_SPEED = 2400.0                # Laser bolt forward speed
LASER_FIRE_COOLDOWN = 0.14          # Minimum seconds between blaster shots
LASER_DAMAGE = 30.0                 # Base laser damage
LASER_CONVERGENCE_Z = 750.0         # 3D depth where twin wingtip lasers converge
ENEMY_PROJECTILE_SPEED = 900.0      # Enemy plasma bolt forward speed towards player
CROSSHAIR_LOCK_RADIUS = 90.0        # Screen-space radius for target lock-on

# ==========================================
# Tactical Radar Minimap
# ==========================================
RADAR_RADIUS = 68
RADAR_MAX_RANGE = 2000.0
RADAR_SWEEP_SPEED = 3.5             # Radians per second
