"""Game and physics constants."""

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
PHYSICS_STEP = 1 / 60

G = 6.67430e-11

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 60, 60)
GREEN = (50, 160, 80)
BLUE = (60, 120, 220)
YELLOW = (240, 220, 60)
CYAN = (80, 220, 220)
GRAY = (120, 120, 130)
DARK_GRAY = (40, 40, 50)
ORANGE = (240, 140, 40)

KEY_ROTATE_FINE = 5
THROTTLE_CHANGE_RATE = 0.65

DRAG_COEFFICIENT = 0.5
ROCKET_CROSS_SECTION = 4.0

EARTH = {
    "name": "Earth",
    "mass": 5.972e24,
    "radius": 6371e3,
    "soi_radius": 9.24e8,
    "atmosphere_height": 100e3,
    "color": GREEN,
}

STARTING_FUNDS = 50000
