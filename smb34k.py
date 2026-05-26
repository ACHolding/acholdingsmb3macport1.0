"""
AC's id Software SMB3 Mac Port
Designed for Python 3.14+ compatibility.
Dependencies: pygame (pip install pygame)
All art is procedural inside this file — FILES=OFF (no .png, no extra .py).
"""
from __future__ import annotations

import sys

try:
    import pygame
    from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_f, K_v
except ImportError as exc:  # pragma: no cover - defensive guard
    sys.stderr.write(
        "This demo requires the 'pygame' package.\n"
        "Install it with: pip install pygame\n"
        f"Details: {exc}\n"
    )
    sys.exit(1)

FILES_OFF = True  # Procedural sprites only — nothing loaded from disk.

# SMB3 NES palette — procedural pixel art, FILES=OFF
PAL_MARIO: dict[str, tuple[int, int, int]] = {
    "K": (0, 0, 0),
    "R": (224, 0, 0),
    "r": (152, 0, 0),
    "B": (40, 72, 224),
    "b": (16, 40, 152),
    "S": (252, 188, 136),
    "s": (200, 116, 72),
    "W": (252, 252, 252),
    "Y": (252, 204, 56),
    "H": (136, 64, 0),
}

MARIO_WALK_ANIM = 7  # frames per SMB3 walk step @ 60 FPS
TILE = 16


def _px(rows: list[str], palette: dict[str, tuple[int, int, int]]) -> pygame.Surface:
    w, h = max(len(r) for r in rows), len(rows)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != "." and ch in palette:
                surf.set_at((x, y), palette[ch])
    return surf


def _g16(rows: list[str], pal: dict[str, tuple[int, int, int]], h: int = 16) -> pygame.Surface:
    """Pad pixel rows to 16×h grid (SMB3 tile/sprite size)."""
    padded = [(r + "." * 16)[:16] for r in rows]
    while len(padded) < h:
        padded.append("." * 16)
    return _px(padded[:h], pal)


def _build_mario_sprites() -> dict[str, pygame.Surface]:
    """SMB3 NES small Mario — black-outlined; FILES=OFF."""
    m = PAL_MARIO
    small: dict[str, list[str]] = {
        "mario_idle": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWBBBBWSRK..",
            "..KSYWYYYWYSK...",
            "..KBBBBBBBBBK...",
            "..KBBBBBBBBBK...",
            "...KK....KK.....",
            "....KK..KK......",
            ".....KKKK.......",
        ],
        "mario_w1": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWBBBBWSRK..",
            "..KSYWYYYWYSK...",
            "..KBBBBBBBBBK...",
            ".KKBBBBBBBBK....",
            "KK..K....KK.....",
            ".....KK.KK......",
        ],
        "mario_w2": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWBBBBWSRK..",
            "..KSYWYYYWYSK...",
            "..KBBBBBBBBBK...",
            "..KBBBBBBBBBK...",
            "...KK....KK.....",
            "...KK....KK.....",
        ],
        "mario_w3": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWBBBBWSRK..",
            "..KSYWYYYWYSK...",
            "..KBBBBBBBBBK...",
            "...KBBBBBBBBK...",
            "...KK....K.KK...",
            "..KK......KK....",
        ],
        "mario_jump": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "KKRSWBBBBWSRKK..",
            "KKSYWYYYWYSKK...",
            "..KBBBBBBBBBK...",
            "..KBBBBBBBBBK...",
            "...KK....KK.....",
        ],
        "mario_skid": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWBBBBWSRK..",
            "..KSYWYYYWYSK...",
            "..KBBBBBBBBBK...",
            "..KBBBBBBBBBK...",
            "KK.KK....KK.KK..",
            ".KK......KK.KK..",
        ],
        "mario_fall": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWBBBBWSRK..",
            "..KSYWYYYWYSK...",
            "..KBBBBBBBBBK...",
            "...KK....KK.....",
            "...KK....KK.....",
            "....KK..KK......",
            ".....KKKK.......",
        ],
    }
    out = {k: _g16(v, m) for k, v in small.items()}

    big: dict[str, list[str]] = {
        "big_idle": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            "..KBBBBBBBBBBBK...",
            "..KBBBBBBBBBBBK...",
            "...KK......KK.....",
            "....KK....KK......",
            ".....KKKKKK.......",
        ],
        "big_w1": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            "..KBBBBBBBBBBBK...",
            ".KKBBBBBBBBBBK....",
            "KK..KK....KK......",
            ".....KK.KK........",
        ],
        "big_w2": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            "..KBBBBBBBBBBBK...",
            "..KBBBBBBBBBBBK...",
            "...KK......KK.....",
            "...KK......KK.....",
        ],
        "big_w3": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            "..KBBBBBBBBBBBK...",
            "...KBBBBBBBBBK....",
            "...KK......K.KK...",
            "..KK........KK....",
        ],
        "big_jump": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "KKRRSWBBBBWSRRKK..",
            "KKKSYYYYYYYSKKK...",
            "..KBBBBBBBBBBBK...",
            "..KBBBBBBBBBBBK...",
            "...KK......KK.....",
        ],
        "big_skid": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            "..KBBBBBBBBBBBK...",
            "..KBBBBBBBBBBBK...",
            "KK.KK......KK.KK..",
            ".KK........KK.KK..",
        ],
        "big_fall": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            "..KBBBBBBBBBBBK...",
            "...KK......KK.....",
            "...KK......KK.....",
            "....KK....KK......",
            ".....KKKKKK.......",
        ],
    }
    for k, v in big.items():
        padded = [(r + "." * 20)[:20] for r in v]
        out[k] = _px(padded, m)
    return out


class SMB3Atlas:
    """SMB3 atlas — Mario sprites; procedural, FILES=OFF."""

    _inst: SMB3Atlas | None = None

    def __init__(self) -> None:
        self._sprites = _build_mario_sprites()

    @classmethod
    def get(cls) -> SMB3Atlas:
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def get_sprite(self, name: str, flip_x: bool = False) -> pygame.Surface:
        spr = self._sprites[name]
        return pygame.transform.flip(spr, True, False) if flip_x else spr


# Global Configurations
INTERNAL_WIDTH = 256
INTERNAL_HEIGHT = 240
TARGET_FPS = 60  # NES/Famicom is ~60.1; keep it at 60 for stability

# Window scale (integer scaling keeps pixels crisp)
WINDOW_SCALE = 3
SCREEN_WIDTH = INTERNAL_WIDTH * WINDOW_SCALE
SCREEN_HEIGHT = INTERNAL_HEIGHT * WINDOW_SCALE

class RetroGameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("AC's SMB3 Mac Port (FILES=OFF)")
        self.clock = pygame.time.Clock()
        self.is_running = True

        # Render to a low-res internal surface (NES-like), then scale up.
        self.fb = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT)).convert()

        # SMB3 Mario atlas — built once at startup, FILES=OFF
        self.atlas = SMB3Atlas.get()
        self._mario_image = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        self.ground_y = 192

        # Performance/VSYNC Toggle Flag
        self.limit_fps = False

        # Initial Background Colors & Layout values
        # Palette loosely inspired by NES SMB3 grassland
        self.sky_blue = (92, 148, 252)
        self.ground_orange = (252, 152, 56)
        self.brick_brown = (188, 64, 0)
        self.brick_highlight = (252, 188, 176)
        self.pipe_green = (0, 168, 0)
        self.cloud_white = (255, 255, 255)
        self.hud_background = (0, 0, 0)
        
        # SMB3 Mario — rect.bottom anchored to ground_y (same as smb4k Player._paint)
        self.player_x = 32.0
        self.player_speed_px_s = 90.0
        self.player_facing = 1
        self.player_anim = 0
        self.player_moving = False
        self.player_on_ground = True
        self.player_vy = 0.0
        self.player_y_offset = 0.0
        self.player_skid = False
        self.player_power = 0  # 0 small, 1 super
        self._paint_mario("mario_idle")

        # Frame timing
        self.dt = 1.0 / TARGET_FPS

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.is_running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.is_running = False
                elif event.key == K_v:
                    # Toggle VSYNC / FPS Frame Capping
                    self.limit_fps = not self.limit_fps
                    print(f"FPS Limiter State: {'ON' if self.limit_fps else 'OFF'}")

    def update_logic(self):
        move = self.player_speed_px_s * self.dt
        keys = pygame.key.get_pressed()
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        jump = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]

        prev_facing = self.player_facing
        self.player_moving = False
        if left and not right:
            self.player_x -= move
            self.player_facing = -1
            self.player_moving = True
        elif right and not left:
            self.player_x += move
            self.player_facing = 1
            self.player_moving = True

        if jump and self.player_on_ground:
            self.player_vy = -220.0
            self.player_on_ground = False

        if not self.player_on_ground:
            self.player_vy = min(self.player_vy + 520.0 * self.dt, 320.0)
            self.player_y_offset += self.player_vy * self.dt
            if self.player_y_offset >= 0:
                self.player_y_offset = 0.0
                self.player_vy = 0.0
                self.player_on_ground = True
        elif self.player_moving:
            self.player_anim += 1

        if self.player_moving and prev_facing != self.player_facing:
            self.player_skid = True
        elif self.player_on_ground and not self.player_moving:
            self.player_skid = False

        sprite_w = self._mario_image.get_width()
        if self.player_x < 0:
            self.player_x = 0
        if self.player_x > INTERNAL_WIDTH - sprite_w:
            self.player_x = float(INTERNAL_WIDTH - sprite_w)

        self._paint_mario(self._mario_anim_name())

    def _draw_cloud(self, x: int, y: int) -> None:
        """Simple SMB1‑style cloud made from circles/rects."""
        pygame.draw.circle(self.fb, self.cloud_white, (x + 12, y + 12), 12)
        pygame.draw.circle(self.fb, self.cloud_white, (x + 28, y + 8), 10)
        pygame.draw.circle(self.fb, self.cloud_white, (x + 40, y + 14), 12)
        pygame.draw.rect(self.fb, self.cloud_white, (x + 8, y + 12, 36, 16))

    def _draw_pipe(self, x: int, ground_y: int) -> None:
        """Very small 1‑tile pipe."""
        pipe_height = 64
        tube_rect = pygame.Rect(x + 8, ground_y - pipe_height, 32, pipe_height)
        lip_rect = pygame.Rect(x, ground_y - pipe_height - 8, 48, 16)
        pygame.draw.rect(self.fb, self.pipe_green, tube_rect)
        pygame.draw.rect(self.fb, self.pipe_green, lip_rect)

    def _draw_brick_block(self, x: int, y: int) -> None:
        """Single SMB1‑style brick tile."""
        tile = pygame.Rect(x, y, 32, 32)
        pygame.draw.rect(self.fb, self.brick_brown, tile)
        # Horizontal highlight stripe
        pygame.draw.line(
            self.fb, self.brick_highlight, (x + 2, y + 6), (x + 30, y + 6), 2
        )
        # Vertical grooves
        pygame.draw.line(
            self.fb, (0, 0, 0), (x + 8, y + 2), (x + 8, y + 30), 1
        )
        pygame.draw.line(
            self.fb, (0, 0, 0), (x + 16, y + 2), (x + 16, y + 30), 1
        )
        pygame.draw.line(
            self.fb, (0, 0, 0), (x + 24, y + 2), (x + 24, y + 30), 1
        )

    def _resolve_sprite(self, name: str) -> str:
        if self.player_power and name.startswith("mario_"):
            alt = "big_" + name[6:]
            if alt in self.atlas._sprites:
                return alt
        return name

    def _mario_anim_name(self) -> str:
        if not self.player_on_ground:
            if self.player_vy < 0:
                return "mario_jump"
            if self.player_vy > 48:
                return "mario_fall"
            return "mario_jump"
        if not self.player_moving:
            return "mario_idle"
        if getattr(self, "player_skid", False):
            return "mario_skid"
        frame = (self.player_anim // MARIO_WALK_ANIM) % 3
        return ("mario_w1", "mario_w2", "mario_w3")[frame]

    def _paint_mario(self, name: str) -> None:
        """Match smb4k Player._paint — bottom-anchored SMB3 sprite, FILES=OFF."""
        spr_name = self._resolve_sprite(name)
        spr = self.atlas.get_sprite(spr_name, flip_x=self.player_facing < 0)
        w = max(TILE, spr.get_width())
        h = max(TILE, spr.get_height())
        if self._mario_image.get_size() != (w, h):
            self._mario_image = pygame.Surface((w, h), pygame.SRCALPHA)
        self._mario_image.fill((0, 0, 0, 0))
        self._mario_image.blit(spr, (0, h - spr.get_height()))

    def _draw_player(self) -> None:
        """SMB3 NES Mario — atlas blit with feet on ground_y."""
        x = int(self.player_x)
        y = self.ground_y - self._mario_image.get_height() + int(self.player_y_offset)
        self.fb.blit(self._mario_image, (x, y))

    def render(self):
        # 1. Clear with basic blue sky color
        self.fb.fill(self.sky_blue)

        # 2. Draw ground stripe (SMB3 grassland ground lip)
        pygame.draw.rect(
            self.fb,
            self.ground_orange,
            (0, self.ground_y, INTERNAL_WIDTH, INTERNAL_HEIGHT - self.ground_y),
        )

        # 3. Simple brick platform row
        for i in range(6):
            self._draw_brick_block(64 + i * 32, self.ground_y - 64)

        # 4. Clouds and pipe landmarks
        self._draw_cloud(80, 80)
        self._draw_cloud(260, 40)
        self._draw_cloud(160, 90)
        self._draw_pipe(176, self.ground_y)

        # 5. Render SMB3 Mario sprite (FILES=OFF)
        self._draw_player()

        # 6. Render active HUD text to monitor the engine configuration
        font = pygame.font.SysFont("Courier", 18, bold=True)
        fps_text = f"FPS: {int(self.clock.get_fps())}"
        config_text = f"FPS Limiter (V Toggle): {'ENABLED' if self.limit_fps else 'DISABLED (UNLIMITED)'}"

        # HUD background bar for readability
        pygame.draw.rect(self.fb, self.hud_background, (0, 0, INTERNAL_WIDTH, 16))

        fps_surface = font.render(fps_text, True, (255, 255, 255))
        config_surface = font.render(config_text, True, (255, 255, 255))

        # Render text to internal buffer (smaller positions for 256x240)
        self.fb.blit(fps_surface, (4, -2))
        self.fb.blit(config_surface, (72, -2))

        # Scale internal framebuffer to window
        scaled = pygame.transform.scale(self.fb, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen.blit(scaled, (0, 0))

        # "Curtains" (overscan bars) to evoke Famicom CRT framing
        curtain_w = 12
        pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, curtain_w, SCREEN_HEIGHT))
        pygame.draw.rect(
            self.screen, (0, 0, 0), (SCREEN_WIDTH - curtain_w, 0, curtain_w, SCREEN_HEIGHT)
        )

        # Double Buffer Flip
        pygame.display.flip()

    def run(self):
        while self.is_running:
            self.handle_events()
            # dt from previous frame; clamp to avoid giant jumps after pauses
            self.dt = min(self.clock.get_time() / 1000.0, 0.05) if self.clock.get_time() else (1.0 / TARGET_FPS)
            self.update_logic()
            self.render()
            
            # Control frame timings explicitly
            if self.limit_fps:
                self.clock.tick(TARGET_FPS)
            else:
                self.clock.tick() # Max performance loop execution

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = RetroGameEngine()
    game.run()