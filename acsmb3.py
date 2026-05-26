"""
AC's id Software SMB3 Mac Port — FULL EDITION
Python 3.14+ | pygame | FILES=OFF (all sprites procedural, no external assets)
All worlds 1-8, every level, 60 FPS, single .py file.

Controls:
    Arrows / WASD : move
    Space / Up / W: jump (hold for higher)
    Shift / X     : run / fire
    Down          : crouch / enter pipe
    Esc           : quit
    V             : toggle FPS cap
    F             : toggle fullscreen
    M             : return to map (during level)
    Enter         : select on map / start
"""
from __future__ import annotations

import sys
import math
import random
import os
import ctypes
from dataclasses import dataclass, field
from typing import Optional

# Python 3.14+ on macOS needs SDL2 libraries pre-loaded before pygame
# to resolve flat-namespace symbol lookup (e.g. _SDL_DestroyWindow).
# We ONLY use pygame's bundled dylibs + local; never homebrew paths to avoid
# duplicate SDL2 class registrations (objc warnings + potential crashes).
if sys.platform == "darwin" and sys.version_info[:2] >= (3, 14):
    _pygame_dylibs = "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/pygame/.dylibs"
    # Bias dyld to prefer the pygame-bundled SDL2 (must be set before pygame imports anything)
    if os.path.isdir(_pygame_dylibs):
        _dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
        if _pygame_dylibs not in _dyld:
            os.environ["DYLD_LIBRARY_PATH"] = _pygame_dylibs + (":" + _dyld if _dyld else "")
    _sdl_dirs = []
    try:
        _sdl_dirs.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dylibs"))
    except NameError:
        pass
    if os.path.isdir(_pygame_dylibs):
        _sdl_dirs.append(_pygame_dylibs)
    _loaded = False
    for _d in _sdl_dirs:
        if not os.path.isdir(_d):
            continue
        for _f in os.listdir(_d):
            if _f.startswith("libSDL2-2") and _f.endswith(".dylib"):
                try:
                    ctypes.CDLL(os.path.join(_d, _f), mode=os.RTLD_GLOBAL | os.RTLD_LAZY)
                    _loaded = True
                    break
                except Exception:
                    continue
        if _loaded:
            break
    if _loaded:
        # Also pre-load other SDL libraries pygame needs (only from the good dirs we chose)
        _good_dirs = [d for d in _sdl_dirs if os.path.isdir(d)]
        for _lib in ("libSDL2_image", "libSDL2_mixer", "libSDL2_ttf"):
            for _d in _good_dirs:
                if not os.path.isdir(_d):
                    continue
                for _f in os.listdir(_d):
                    if _f.startswith(_lib) and _f.endswith(".dylib"):
                        try:
                            ctypes.CDLL(os.path.join(_d, _f), mode=os.RTLD_GLOBAL | os.RTLD_LAZY)
                        except Exception:
                            pass
                        break

try:
    import pygame
    from pygame.locals import (
        QUIT, KEYDOWN, KEYUP, K_ESCAPE, K_f, K_v, K_m, K_RETURN, K_SPACE,
        K_LEFT, K_RIGHT, K_UP, K_DOWN, K_a, K_d, K_w, K_s, K_LSHIFT, K_RSHIFT,
        K_x, K_z, K_p,
    )
except ImportError as exc:
    sys.stderr.write(
        "This game requires the 'pygame' package.\n"
        "Install with: pip install pygame\n"
        f"Details: {exc}\n"
    )
    sys.exit(1)

FILES_OFF = True  # Procedural only. No file I/O for sprites/sound/levels.

# =============================================================================
# CONFIG
# =============================================================================
INTERNAL_WIDTH  = 256
INTERNAL_HEIGHT = 240
TARGET_FPS      = 60
WINDOW_SCALE    = 3
SCREEN_WIDTH    = INTERNAL_WIDTH  * WINDOW_SCALE
SCREEN_HEIGHT   = INTERNAL_HEIGHT * WINDOW_SCALE
TILE            = 16
GRAVITY         = 520.0
MAX_FALL        = 320.0
JUMP_V          = -220.0
JUMP_V_RUN      = -250.0
WALK_SPEED      = 90.0
RUN_SPEED       = 150.0

# =============================================================================
# PALETTES (NES SMB3-style)
# =============================================================================
PAL = {
    # base
    "K": (0, 0, 0),
    "W": (252, 252, 252),
    "_": (0, 0, 0, 0),  # transparent

    # mario
    "R": (224, 0, 0),
    "r": (152, 0, 0),
    "B": (40, 72, 224),
    "b": (16, 40, 152),
    "S": (252, 188, 136),     # skin
    "s": (200, 116, 72),
    "Y": (252, 204, 56),      # yellow buttons
    "H": (136, 64, 0),        # brown / hair
    "O": (252, 152, 56),      # orange (fire mario)
    "o": (200, 76, 12),
    "G": (0, 168, 0),         # green
    "g": (0, 104, 0),
    "T": (252, 188, 176),     # tan / cape

    # enemies
    "M": (200, 76, 12),       # goomba brown
    "m": (140, 40, 0),
    "C": (252, 116, 96),      # koopa shell red
    "c": (152, 0, 0),
    "U": (188, 252, 188),     # piranha pale
    "P": (0, 168, 0),         # piranha green
    "p": (0, 104, 0),
    "L": (252, 252, 0),       # eyes yellow / lakitu
    "Z": (60, 60, 60),        # grey
    "z": (32, 32, 32),
    "E": (252, 60, 60),       # bullet bill red eye

    # tiles
    "1": (252, 152, 56),      # ground orange (W1)
    "2": (188, 64, 0),        # darker ground / brick
    "3": (252, 188, 176),     # highlight
    "4": (92, 148, 252),      # sky blue
    "5": (252, 252, 0),       # yellow coin
    "6": (200, 152, 0),       # coin shadow
    "7": (0, 152, 248),       # water
    "8": (0, 88, 184),        # water shade
    "9": (188, 188, 252),     # cloud platform
    "0": (252, 240, 168),     # sand
    "I": (200, 200, 252),     # ice
    "i": (160, 160, 240),     # ice shade
    "N": (60, 60, 124),       # night
    "n": (24, 24, 80),
    "F": (252, 56, 56),       # flag/fire red
    "f": (152, 0, 0),
    "Q": (252, 188, 56),      # ? block
    "q": (200, 116, 0),
    "X": (152, 80, 0),        # used block / wood
    "x": (80, 40, 0),
    "V": (104, 76, 56),       # vine brown
    "v": (56, 188, 56),       # vine green
    "J": (252, 224, 168),     # giant land tan
    "j": (188, 152, 80),
    "D": (104, 56, 24),       # dirt
    "d": (60, 28, 8),
    "A": (252, 56, 252),      # magic / star
    "a": (152, 0, 152),
    "h": (200, 200, 200),     # light grey
}

# Theme palettes per world for sky / ground tints
THEMES = {
    "grass":   {"sky": (92, 148, 252),  "ground": (252, 152, 56),  "brick": (188, 64, 0)},
    "desert":  {"sky": (252, 188, 56),  "ground": (252, 240, 168), "brick": (200, 116, 0)},
    "water":   {"sky": (0, 88, 248),    "ground": (252, 240, 168), "brick": (188, 64, 0)},
    "giant":   {"sky": (92, 148, 252),  "ground": (252, 224, 168), "brick": (188, 116, 0)},
    "sky":     {"sky": (188, 200, 252), "ground": (255, 255, 255), "brick": (200, 200, 200)},
    "ice":     {"sky": (148, 200, 252), "ground": (200, 200, 252), "brick": (160, 160, 240)},
    "pipe":    {"sky": (92, 148, 252),  "ground": (0, 168, 0),     "brick": (0, 104, 0)},
    "dark":    {"sky": (24, 24, 80),    "ground": (60, 60, 60),    "brick": (32, 32, 32)},
    "fortress":{"sky": (60, 60, 124),   "ground": (104, 104, 104), "brick": (60, 60, 60)},
    "airship": {"sky": (252, 188, 56),  "ground": (188, 116, 0),   "brick": (104, 76, 56)},
    "underground":{"sky": (0, 0, 0),    "ground": (188, 64, 0),    "brick": (200, 116, 0)},
    "night":   {"sky": (24, 24, 80),    "ground": (60, 60, 60),    "brick": (32, 32, 32)},
}

# =============================================================================
# SPRITE BUILDERS — all procedural pixel art, FILES=OFF
# =============================================================================
def _px(rows: list[str], w: Optional[int] = None, h: Optional[int] = None) -> pygame.Surface:
    if w is None:
        w = max(len(r) for r in rows)
    if h is None:
        h = len(rows)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    for y, row in enumerate(rows[:h]):
        for x, ch in enumerate(row[:w]):
            if ch != "." and ch in PAL:
                col = PAL[ch]
                if len(col) == 3:
                    surf.set_at((x, y), col)
                else:
                    if col[3] > 0:
                        surf.set_at((x, y), col)
    return surf

def _pad16(rows: list[str], h: int = 16) -> list[str]:
    out = [(r + "." * 16)[:16] for r in rows]
    while len(out) < h:
        out.append("." * 16)
    return out[:h]

# -----------------------------------------------------------------------------
# Mario sprites (small, super, fire, raccoon)
# -----------------------------------------------------------------------------
def _build_mario(pal_skin: str = "S", pal_shirt: str = "R", pal_overall: str = "B", pal_hair: str = "H") -> dict[str, pygame.Surface]:
    """Build a Mario set with given palette substitutions. Returns sprite dict."""
    def sub(rows: list[str]) -> list[str]:
        out = []
        for r in rows:
            r = r.replace("R", pal_shirt).replace("B", pal_overall)
            out.append(r)
        return out

    small = {
        "idle": [
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
        "w1": [
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
        "w2": [
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
        "w3": [
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
        "jump": [
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
        "skid": [
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
        "fall": [
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
        "crouch": [
            "................",
            "................",
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRSSSSRK....",
            "..KKRSWBBWSRKK..",
            ".KKKBBYYYYBBKKK.",
            "..KBBBBBBBBBK...",
            "..KKBBBBBBBKK...",
            ".KK..KKKK..KK...",
        ],
        "swim1": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWBBBBWSRK..",
            "..KSYWYYYWYSK...",
            "..KBBBBBBBBBK...",
            "..KBBBBBBBBBK...",
            "...KKKKKKKKK....",
        ],
        "swim2": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWBBBBWSRK..",
            "..KSYWYYYWYSK...",
            "..KBBBBBBBBBK...",
            "...KBBBBBBBK....",
            "....KKKKKKKK....",
        ],
        "die": [
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRRRRRRK....",
            "...KRRSSSSRRK...",
            "..KRSWKKKKWSRK..",
            "..KSYWKKKWYSK...",
            "..KBBBBBBBBBK...",
            "..KBBBBBBBBBK...",
            "...KK....KK.....",
            "....KK..KK......",
            ".....KKKK.......",
        ],
    }

    big = {
        "idle": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            ".RKBBBBBBBBBBBKR..",
            "..KKBBBBBBBBBKK...",
            "...KK......KK.....",
            "....KK....KK......",
            ".....KKKKKK.......",
        ],
        "w1": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            ".RKBBBBBBBBBBBK...",
            ".KKBBBBBBBBBBKK...",
            "KK..KK....KK......",
            ".....KK.KK........",
        ],
        "w2": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            ".RKBBBBBBBBBBBKR..",
            "..KKBBBBBBBBBKK...",
            "...KK......KK.....",
            "...KK......KK.....",
        ],
        "w3": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            "..KKBBBBBBBBBKK...",
            "...KBBBBBBBBBK....",
            "...KK......K.KK...",
            "..KK........KK....",
        ],
        "jump": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "KKRRSWBBBBWSRRKK..",
            "KKKSYYYYYYYSKKK...",
            ".RKBBBBBBBBBBBKR..",
            ".RKBBBBBBBBBBBKR..",
            "..KKBBBBBBBBBKK...",
            "...KK......KK.....",
        ],
        "skid": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            ".RKBBBBBBBBBBBKR..",
            "..KKBBBBBBBBBKK...",
            "KK.KK......KK.KK..",
            ".KK........KK.KK..",
        ],
        "fall": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            ".RKBBBBBBBBBBBKR..",
            "..KK......KK......",
            "...KK....KK.......",
            "....KK..KK........",
            ".....KKKK.........",
        ],
        "crouch": [
            "................",
            "................",
            "......KKKK......",
            ".....KRRRRK.....",
            "....KRSSSSRK....",
            "..KKRSWBBWSRKK..",
            ".KKKBBYYYYBBKKK.",
            ".RKBBBBBBBBBBKR.",
            "..KBBBBBBBBBBK..",
            "..KKBBBBBBBBKK..",
            ".KK..KKKK..KK...",
        ],
        "swim1": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            "..KBBBBBBBBBBBK...",
            "...KKKKKKKKKKK....",
        ],
        "swim2": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            "...KBBBBBBBBBK....",
            "....KKKKKKKKKK....",
        ],
        "raccoon_idle": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            ".RKBBBBBBBBBBBKR..",
            "HRKBBBBBBBBBBBKRH.",
            "HHKKBBBBBBBBBKKHH.",
            ".HHKK......KK.HH..",
            "...KK......KK.....",
            "....KK....KK......",
            ".....KKKKKK.......",
        ],
        "raccoon_fly": [
            "......KKKKKK......",
            ".....KRRRRRRK.....",
            "....KRRRRRRRRK....",
            "...KRRRSSSSRRRK...",
            "..KRRSWBBBBWSRRK..",
            "..KKSYYYYYYYSKK...",
            "HHKBBBBBBBBBBBKHH.",
            "HHKBBBBBBBBBBBKHH.",
            ".HKKBBBBBBBBBKKH..",
            "..HKK......KKH....",
            "...KK......KK.....",
        ],
    }

    out: dict[str, pygame.Surface] = {}
    for k, v in small.items():
        out[f"small_{k}"] = _px(_pad16(sub(v), 16), 16, 16)
    # Big (super) Mario is 16 wide x 28 tall to match the 28px hitbox.
    # Rows are top-padded so the feet stay anchored to the bottom edge.
    BIG_W, BIG_H = 16, 28
    for k, v in big.items():
        rows = [(r + "." * BIG_W)[:BIG_W] for r in sub(v)]
        while len(rows) < BIG_H:
            rows.insert(0, "." * BIG_W)
        out[f"big_{k}"] = _px(rows[-BIG_H:], BIG_W, BIG_H)
    return out

# -----------------------------------------------------------------------------
# Enemy sprites — procedural
# -----------------------------------------------------------------------------
def _build_enemies() -> dict[str, pygame.Surface]:
    out: dict[str, pygame.Surface] = {}
    goomba1 = [
        "....KKKKKKKK....",
        "..KKMMMMMMMMKK..",
        ".KMMMMMMMMMMMMK.",
        ".KMmMWmmWmMWmMK.",
        ".KMMWWMMMMWWMMK.",
        ".KMMMMMMMMMMMMK.",
        ".KMMMMMMMMMMMMK.",
        ".KKMMMMMMMMMMKK.",
        "..SSKKSSSSKKSS..",
        ".SSS..SSSS..SSS.",
    ]
    goomba2 = [
        "....KKKKKKKK....",
        "..KKMMMMMMMMKK..",
        ".KMMMMMMMMMMMMK.",
        ".KMmMWmmWmMWmMK.",
        ".KMMWWMMMMWWMMK.",
        ".KMMMMMMMMMMMMK.",
        ".KMMMMMMMMMMMMK.",
        ".KKMMMMMMMMMMKK.",
        "..SSSS.KK.SSSS..",
        ".SSSSS....SSSSS.",
    ]
    goomba_squish = [
        "................",
        "................",
        "................",
        "....KKKKKKKK....",
        "..KKMMMMMMMMKK..",
        ".KMmMWmmWmMWmMK.",
        ".KMMMMMMMMMMMMK.",
        ".KKMMMMMMMMMMKK.",
        "..SSSSSSSSSSSS..",
    ]
    out["goomba1"] = _px(_pad16(goomba1, 16))
    out["goomba2"] = _px(_pad16(goomba2, 16))
    out["goomba_squish"] = _px(_pad16(goomba_squish, 16))

    # Koopa Troopa (green)
    koopa_g1 = [
        "................",
        "....KKKKKK......",
        "...KGGGGGGK.....",
        "...KGLWLWLGK....",
        "...KGGGGGGGK....",
        "....KSSSSSK.....",
        "..KKGGGGGGGKK...",
        ".KGgWGGggGWGGK..",
        ".KGGWGGGGGWGGK..",
        ".KGGGGGGGGGGGK..",
        ".KKGGGGGGGGGKK..",
        "..SS..SSSS..SS..",
        ".SSS..SSSS..SSS.",
    ]
    koopa_g2 = [
        "................",
        "....KKKKKK......",
        "...KGGGGGGK.....",
        "...KGLWLWLGK....",
        "...KGGGGGGGK....",
        "....KSSSSSK.....",
        "..KKGGGGGGGKK...",
        ".KGgWGGggGWGGK..",
        ".KGGWGGGGGWGGK..",
        ".KGGGGGGGGGGGK..",
        ".KKGGGGGGGGGKK..",
        "...SSSS.KKSSSS..",
        "..SSSSS..SSSSSS.",
    ]
    out["koopa_g1"] = _px(_pad16(koopa_g1, 16))
    out["koopa_g2"] = _px(_pad16(koopa_g2, 16))

    # Koopa shell
    shell = [
        "................",
        "...KKKKKKKKKK...",
        "..KGGGGGGGGGGK..",
        ".KGGgggggggggGK.",
        ".KgGGggGGggGGgK.",
        ".KGgGGggGGggGGK.",
        ".KgGGgggggggGGK.",
        ".KGgGgGgGgGgGGK.",
        ".KGgggggggggggK.",
        ".KKKGGGGGGGGKKK.",
        "..KKKKKKKKKKKK..",
    ]
    out["shell_g"] = _px(_pad16(shell, 16))
    # Red shell variant
    rshell = [r.replace("G", "C").replace("g", "c") for r in shell]
    out["shell_r"] = _px(_pad16(rshell, 16))

    # Red Koopa
    koopa_r1 = [r.replace("G", "C").replace("g", "c") for r in koopa_g1]
    out["koopa_r1"] = _px(_pad16(koopa_r1, 16))
    out["koopa_r2"] = _px(_pad16([r.replace("G", "C").replace("g", "c") for r in koopa_g2], 16))

    # Piranha Plant
    piranha = [
        ".....KKKKKKK....",
        "....KPPPPPPPK...",
        "...KPUWWWWWUPK..",
        "...KUWWWWWWWUK..",
        "...KPWKKWKKWPK..",
        "...KPWWWWWWWPK..",
        "...KPUWWWWWUPK..",
        "....KPPPPPPPK...",
        ".....KPPPPPK....",
        ".....KvvvvvK....",
        ".....KvvvvvK....",
        ".....KvvvvvK....",
        ".....KvvvvvK....",
        ".....KvvvvvK....",
    ]
    out["piranha"] = _px(_pad16(piranha, 16))
    piranha_open = [
        ".....KKKKKKK....",
        "....KPPPPPPPK...",
        "...KPWWWWWWWPK..",
        "...KPWKKKKKWPK..",
        "...KPWKWWKWPK...",
        "...KPWWWWWWWPK..",
        "...KPPPPPPPPPK..",
        "....KFFFFFFFK...",
        ".....KFFFFFK....",
        ".....KvvvvvK....",
        ".....KvvvvvK....",
        ".....KvvvvvK....",
        ".....KvvvvvK....",
        ".....KvvvvvK....",
    ]
    out["piranha_open"] = _px(_pad16(piranha_open, 16))

    # Bullet Bill
    bullet = [
        "................",
        "....KKKKKKKKK...",
        "..KKZZZZZZZZZK..",
        ".KZZZZZZZZZZZZK.",
        "KZZZZZZZZZZZZZK.",
        "KZZZZZZZZZZZZZK.",
        "KZZZZZZZZZZZZZK.",
        ".KZZZZZZZZZZZZK.",
        "..KKZZZZZZZZZK..",
        "....KKKKKKKKK...",
    ]
    out["bullet"] = _px(_pad16(bullet, 16))

    # Hammer Bro
    hammerbro = [
        ".....KKKKKK.....",
        "....KZZZZZZK....",
        "...KZWWWWWWZK...",
        "...KZWLWLWLZK...",
        "...KZWWWWWWZK...",
        "....KSSSSSSK....",
        "..KKZGGGGGGZKK..",
        ".KZGZGGGGGGZGZK.",
        ".KZGGGGGGGGGGZK.",
        ".KZGGZGGGGZGGZK.",
        "..KKGGGGGGGGGKK.",
        "..SSGG.KK.GGSS..",
        ".SSSSS.KK.SSSSS.",
    ]
    out["hammerbro"] = _px(_pad16(hammerbro, 16))

    # Lakitu
    lakitu = [
        "....9999999.....",
        "...999999999....",
        "..99GGGGGGGG99..",
        ".9GLWLWLWLWLG9..",
        "..9GGGGGGGGGG9..",
        "..9SSSSSSSSSS9..",
        "..9GGGGGGGGGG9..",
        "...9GGGGGGGG9...",
        "....9SSSSSS9....",
        ".....KKSSKK.....",
        "....9.99999.....",
        "...99999999.....",
        "..999999999.....",
    ]
    out["lakitu"] = _px(_pad16(lakitu, 16))

    # Spiny
    spiny = [
        "..K..K..K..K....",
        ".KCK.KCK.KCK....",
        "KCCCKCCCKCCCK...",
        ".CCCCCCCCCCC....",
        ".CCFLCFFCFLCC...",
        ".CCCCCCCCCCC....",
        "..CCCCCCCCC.....",
        "...CCKKKCC......",
        "..SS.....SS.....",
        ".SSS.....SSS....",
    ]
    out["spiny"] = _px(_pad16(spiny, 16))

    # Cheep Cheep
    cheep = [
        "................",
        "....KKKKKKK.....",
        "..KKFFFFFFFKK...",
        ".KFFFWWFFFFFFK..",
        ".KFFWLWFFFFFKKK.",
        ".KFFFWWFFFFFFFK.",
        "KFFFFFFFFFFFFKK.",
        ".KFFFFFFFFFFK...",
        "..KKKFFFKKKK....",
        "....KKKKK.......",
    ]
    out["cheep"] = _px(_pad16(cheep, 16))

    # Boo
    boo = [
        "....WWWWWWWW....",
        "..WWWWWWWWWWWW..",
        ".WWWWWWWWWWWWWW.",
        ".WWKKWWWWWWKKWW.",
        ".WWKKWWWWWWKKWW.",
        ".WWWWWWWWWWWWWW.",
        ".WWWWWWKKWWWWWW.",
        ".WWWWWWWWWWWWWW.",
        ".WWWWWWWWWWWWWW.",
        ".WWW.W.WW.W.WWW.",
        ".WW...W..W...WW.",
    ]
    out["boo"] = _px(_pad16(boo, 16))

    # Dry Bones / Bone
    dry = [
        "................",
        "....WWWWWW......",
        "...WhhhhhhW.....",
        "...WhKKhKKhW....",
        "...WhhhhhhW.....",
        "....WhWhWh......",
        "..WWWhhhhhhWW...",
        ".WhWhhWWhhWhWh..",
        ".WhWhhWWhhWhWh..",
        ".WWWWWWWWWWWW...",
        "..WW.WWWW.WW....",
    ]
    out["drybones"] = _px(_pad16(dry, 16))

    # Thwomp
    thwomp = [
        "ZZZZZZZZZZZZZZZZ",
        "ZhhhhhhhhhhhhhhZ",
        "ZhWZZhhhhhhZZWhZ",
        "ZhWZZhhhhhhZZWhZ",
        "ZhhhhhhhhhhhhhhZ",
        "ZhhhFFhhhhFFhhhZ",
        "ZhhhhhFFFFhhhhhZ",
        "ZhhhhhhhhhhhhhhZ",
        "ZZZhhhhhhhhhhZZZ",
        "..ZZZZZZZZZZZZ..",
    ]
    out["thwomp"] = _px(_pad16(thwomp, 16))

    # Boss Koopaling (Bowser-style)
    boss = [
        "....KKKKKKKK....",
        "...KGGGGGGGGK...",
        "..KGYYGYYGYYGK..",
        "..KGGGGGGGGGGK..",
        "..KGLWLGLWLGK...",
        "..KGGGGRRGGGK...",
        "..KGGGGGGGGGK...",
        ".KCGGGGGGGGGCK..",
        ".KCCCGGGGGGCCK..",
        ".KCCCCGGGGCCCK..",
        ".KKCCGCCCCGCCKK.",
        ".KK.GG.KK.GG.KK.",
        "..KKK..KK..KKK..",
    ]
    out["boss"] = _px(_pad16(boss, 16))
    return out

# -----------------------------------------------------------------------------
# Tile builders — procedural 16x16
# -----------------------------------------------------------------------------
def _build_tiles() -> dict[str, pygame.Surface]:
    out: dict[str, pygame.Surface] = {}

    # Ground brick (W1 grassland orange)
    ground = pygame.Surface((16, 16))
    ground.fill(PAL["1"])
    pygame.draw.rect(ground, PAL["2"], (0, 0, 16, 3))
    pygame.draw.line(ground, PAL["3"], (0, 4), (15, 4))
    for y in (6, 11):
        for x in range(0, 16, 4):
            pygame.draw.line(ground, PAL["2"], (x, y), (x, y + 4))
    pygame.draw.line(ground, PAL["2"], (0, 15), (15, 15))
    out["ground"] = ground

    # Desert ground (sand)
    sand = pygame.Surface((16, 16))
    sand.fill(PAL["0"])
    pygame.draw.rect(sand, PAL["q"], (0, 0, 16, 3))
    for y in (6, 11):
        for x in range(0, 16, 4):
            pygame.draw.line(sand, PAL["q"], (x, y), (x, y + 4))
    out["sand"] = sand

    # Ice
    ice = pygame.Surface((16, 16))
    ice.fill(PAL["I"])
    pygame.draw.rect(ice, PAL["i"], (0, 0, 16, 2))
    pygame.draw.line(ice, PAL["W"], (1, 3), (14, 3))
    for y in (8, 13):
        for x in range(0, 16, 4):
            pygame.draw.line(ice, PAL["i"], (x, y), (x, y + 2))
    out["ice"] = ice

    # Castle/fortress brick (grey)
    castle = pygame.Surface((16, 16))
    castle.fill(PAL["Z"])
    pygame.draw.rect(castle, PAL["z"], (0, 0, 16, 1))
    pygame.draw.rect(castle, PAL["z"], (0, 7, 16, 1))
    pygame.draw.rect(castle, PAL["z"], (0, 15, 16, 1))
    for x in (0, 8):
        pygame.draw.line(castle, PAL["z"], (x, 0), (x, 7))
    for x in (4, 12):
        pygame.draw.line(castle, PAL["z"], (x, 8), (x, 15))
    out["castle"] = castle

    # Brick
    brick = pygame.Surface((16, 16))
    brick.fill(PAL["2"])
    pygame.draw.line(brick, PAL["3"], (0, 1), (15, 1))
    pygame.draw.line(brick, PAL["K"], (0, 7), (15, 7))
    pygame.draw.line(brick, PAL["K"], (0, 15), (15, 15))
    pygame.draw.line(brick, PAL["K"], (0, 0), (0, 15))
    pygame.draw.line(brick, PAL["K"], (4, 0), (4, 7))
    pygame.draw.line(brick, PAL["K"], (12, 0), (12, 7))
    pygame.draw.line(brick, PAL["K"], (8, 8), (8, 15))
    out["brick"] = brick

    # Question block (frame 1)
    qblock = pygame.Surface((16, 16))
    qblock.fill(PAL["Q"])
    pygame.draw.rect(qblock, PAL["q"], (0, 0, 16, 16), 1)
    pygame.draw.rect(qblock, PAL["W"], (1, 1, 14, 2))
    pygame.draw.rect(qblock, PAL["K"], (0, 14, 16, 2))
    # ? character
    font = pygame.font.SysFont(None, 14, bold=True)
    q_surf = font.render("?", True, PAL["K"])
    qblock.blit(q_surf, (5, 2))
    out["qblock"] = qblock

    # Used block
    used = pygame.Surface((16, 16))
    used.fill(PAL["X"])
    pygame.draw.rect(used, PAL["x"], (0, 0, 16, 16), 1)
    pygame.draw.rect(used, PAL["W"], (1, 1, 14, 1))
    pygame.draw.rect(used, PAL["K"], (0, 14, 16, 2))
    out["used"] = used

    # Pipe parts (top-left, top-right, body-left, body-right)
    pipe_tl = pygame.Surface((16, 16))
    pipe_tl.fill(PAL["G"])
    pygame.draw.rect(pipe_tl, PAL["g"], (0, 0, 16, 16), 1)
    pygame.draw.rect(pipe_tl, PAL["W"], (2, 2, 4, 8))
    pygame.draw.rect(pipe_tl, PAL["g"], (10, 2, 4, 8))
    out["pipe_tl"] = pipe_tl
    pipe_tr = pygame.transform.flip(pipe_tl, True, False)
    out["pipe_tr"] = pipe_tr
    pipe_bl = pygame.Surface((16, 16))
    pipe_bl.fill(PAL["G"])
    pygame.draw.line(pipe_bl, PAL["W"], (3, 0), (3, 15))
    pygame.draw.line(pipe_bl, PAL["W"], (5, 0), (5, 15))
    pygame.draw.line(pipe_bl, PAL["g"], (10, 0), (10, 15))
    pygame.draw.line(pipe_bl, PAL["g"], (13, 0), (13, 15))
    pygame.draw.line(pipe_bl, PAL["g"], (0, 0), (0, 15))
    out["pipe_bl"] = pipe_bl
    pipe_br = pygame.transform.flip(pipe_bl, True, False)
    out["pipe_br"] = pipe_br

    # Coin (animated 3 frames)
    coin1 = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(coin1, PAL["5"], (3, 1, 10, 14))
    pygame.draw.ellipse(coin1, PAL["6"], (3, 1, 10, 14), 1)
    pygame.draw.line(coin1, PAL["6"], (8, 4), (8, 11))
    out["coin1"] = coin1
    coin2 = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(coin2, PAL["5"], (6, 1, 4, 14))
    pygame.draw.ellipse(coin2, PAL["6"], (6, 1, 4, 14), 1)
    out["coin2"] = coin2
    coin3 = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.line(coin3, PAL["5"], (8, 1), (8, 14), 2)
    out["coin3"] = coin3

    # Cloud
    cloud = pygame.Surface((48, 24), pygame.SRCALPHA)
    pygame.draw.circle(cloud, PAL["W"], (12, 16), 10)
    pygame.draw.circle(cloud, PAL["W"], (24, 12), 10)
    pygame.draw.circle(cloud, PAL["W"], (36, 16), 10)
    pygame.draw.rect(cloud, PAL["W"], (8, 14, 32, 8))
    out["cloud"] = cloud

    # Bush
    bush = pygame.Surface((48, 16), pygame.SRCALPHA)
    pygame.draw.circle(bush, PAL["G"], (10, 12), 8)
    pygame.draw.circle(bush, PAL["G"], (24, 8), 8)
    pygame.draw.circle(bush, PAL["G"], (38, 12), 8)
    pygame.draw.rect(bush, PAL["G"], (6, 10, 36, 6))
    pygame.draw.line(bush, PAL["g"], (0, 15), (47, 15))
    out["bush"] = bush

    # Hill
    hill = pygame.Surface((64, 32), pygame.SRCALPHA)
    pygame.draw.polygon(hill, PAL["G"], [(0, 32), (32, 0), (64, 32)])
    pygame.draw.polygon(hill, PAL["g"], [(12, 24), (16, 20), (20, 24)])
    pygame.draw.polygon(hill, PAL["g"], [(40, 20), (44, 16), (48, 20)])
    out["hill"] = hill

    # Mushroom platform
    mushroom = pygame.Surface((48, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(mushroom, PAL["R"], (0, 0, 48, 12))
    pygame.draw.ellipse(mushroom, PAL["K"], (0, 0, 48, 12), 1)
    pygame.draw.circle(mushroom, PAL["W"], (12, 4), 3)
    pygame.draw.circle(mushroom, PAL["W"], (36, 4), 3)
    pygame.draw.rect(mushroom, PAL["S"], (20, 10, 8, 6))
    out["mushroom_p"] = mushroom

    # Wood platform
    wood = pygame.Surface((16, 16))
    wood.fill(PAL["X"])
    pygame.draw.rect(wood, PAL["x"], (0, 0, 16, 2))
    pygame.draw.rect(wood, PAL["x"], (0, 14, 16, 2))
    pygame.draw.line(wood, PAL["x"], (4, 2), (4, 13))
    pygame.draw.line(wood, PAL["x"], (10, 2), (10, 13))
    out["wood"] = wood

    # Vine
    vine = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.line(vine, PAL["v"], (6, 0), (6, 15), 2)
    pygame.draw.line(vine, PAL["v"], (10, 0), (10, 15), 2)
    for y in range(2, 16, 4):
        pygame.draw.circle(vine, PAL["v"], (8, y), 3)
    out["vine"] = vine

    # Water surface
    water = pygame.Surface((16, 16), pygame.SRCALPHA)
    water.fill((*PAL["7"], 180))
    pygame.draw.line(water, PAL["8"], (0, 2), (15, 2))
    pygame.draw.line(water, PAL["W"], (2, 0), (5, 0))
    pygame.draw.line(water, PAL["W"], (10, 1), (13, 1))
    out["water"] = water

    # Spike
    spike = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.polygon(spike, PAL["Z"], [(0, 16), (4, 8), (8, 16)])
    pygame.draw.polygon(spike, PAL["Z"], [(8, 16), (12, 8), (16, 16)])
    pygame.draw.polygon(spike, PAL["W"], [(2, 14), (4, 10), (6, 14)])
    out["spike"] = spike

    # Goal/flagpole
    flag = pygame.Surface((16, 192), pygame.SRCALPHA)
    pygame.draw.line(flag, PAL["W"], (8, 0), (8, 191), 2)
    pygame.draw.circle(flag, PAL["F"], (8, 4), 4)
    pygame.draw.polygon(flag, PAL["F"], [(8, 12), (0, 16), (8, 22)])
    out["flag"] = flag

    # Goal card (level end)
    goal_card = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(goal_card, PAL["K"], (0, 0, 32, 32))
    pygame.draw.rect(goal_card, PAL["W"], (2, 2, 28, 28))
    pygame.draw.rect(goal_card, PAL["F"], (8, 8, 16, 16))
    out["goal"] = goal_card

    # Castle building (decoration)
    castle_big = pygame.Surface((80, 80), pygame.SRCALPHA)
    castle_big.fill((0, 0, 0, 0))
    pygame.draw.rect(castle_big, PAL["Z"], (0, 16, 80, 64))
    pygame.draw.rect(castle_big, PAL["z"], (0, 16, 80, 64), 1)
    # battlements
    for x in range(0, 80, 16):
        pygame.draw.rect(castle_big, PAL["Z"], (x, 8, 8, 8))
        pygame.draw.rect(castle_big, PAL["z"], (x, 8, 8, 8), 1)
    # door
    pygame.draw.rect(castle_big, PAL["K"], (32, 48, 16, 32))
    # windows
    pygame.draw.rect(castle_big, PAL["K"], (8, 32, 8, 8))
    pygame.draw.rect(castle_big, PAL["K"], (64, 32, 8, 8))
    out["castle_big"] = castle_big

    return out

# -----------------------------------------------------------------------------
# Atlas singleton
# -----------------------------------------------------------------------------
class Atlas:
    _inst: Optional["Atlas"] = None

    def __init__(self) -> None:
        # Mario palette variants
        self.mario_small = _build_mario("S", "R", "B")
        # Super (same colors here; could vary outfit)
        self.mario_super = self.mario_small
        # Fire mario: white shirt, red overalls
        self.mario_fire  = _build_mario("S", "W", "R")
        # Raccoon: same as super but raccoon_idle/fly sprites are used
        self.enemies = _build_enemies()
        self.tiles   = _build_tiles()

    @classmethod
    def get(cls) -> "Atlas":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def mario_sprite(self, power: int, name: str, flip: bool = False) -> pygame.Surface:
        if power == 0:
            spr = self.mario_small.get(f"small_{name}", self.mario_small["small_idle"])
        elif power == 2:
            spr = self.mario_fire.get(f"big_{name}", self.mario_fire["big_idle"])
        elif power == 3:
            # Raccoon
            key = f"big_raccoon_{name}" if name in ("idle", "fly") else f"big_{name}"
            spr = self.mario_super.get(key, self.mario_super["big_idle"])
        else:
            spr = self.mario_super.get(f"big_{name}", self.mario_super["big_idle"])
        return pygame.transform.flip(spr, True, False) if flip else spr

    def enemy(self, name: str, flip: bool = False) -> pygame.Surface:
        spr = self.enemies.get(name, self.enemies["goomba1"])
        return pygame.transform.flip(spr, True, False) if flip else spr

    def tile(self, name: str) -> pygame.Surface:
        return self.tiles.get(name, self.tiles["ground"])


# =============================================================================
# LEVEL ENCODING
# Each level is a list of horizontal strings, each char = 1 tile (16 px)
# Levels are typically 14-15 tiles tall, variable width.
# Legend:
#   . = empty / sky
#   # = ground/solid
#   B = brick
#   ? = question block (coin)
#   M = question block (mushroom)
#   F = question block (fire flower)
#   L = question block (1-up)
#   * = question block (star)
#   = = used block / wood platform
#   X = solid block (decorative)
#   P = pipe top-left (auto pair with right + body below)
#   p = pipe body marker (auto)
#   T = tall pipe top (height set by adjacent)
#   c = coin
#   g = goomba spawn
#   k = green koopa spawn
#   r = red koopa spawn
#   h = hammer bro spawn
#   y = piranha plant (in pipe)
#   b = bullet bill cannon
#   l = lakitu spawn (right edge enter)
#   z = boo spawn
#   d = dry bones spawn
#   t = thwomp spawn
#   s = spike
#   ^ = upward platform (wood)
#   ~ = water
#   v = vine
#   G = goal/end of level
#   S = mario start (auto leftmost if missing)
#   I = ice block (slippery)
#   J = giant block (3x scale)
#   N = note block (bouncy)
#   @ = boss spawn (fortress)
#   ! = axe (defeat boss)
#   - = cloud platform
# =============================================================================

def _make_level(width: int, height: int = 14, theme: str = "grass", ground_h: int = 2) -> list[list[str]]:
    """Create empty level grid filled with '.', ground at bottom."""
    grid = [["."] * width for _ in range(height)]
    for y in range(height - ground_h, height):
        for x in range(width):
            grid[y][x] = "#"
    return grid

def _str_grid(strs: list[str]) -> list[list[str]]:
    h = len(strs)
    # Idempotent: if already list-of-lists, normalize widths and return.
    if strs and isinstance(strs[0], list):
        w = max(len(r) for r in strs)
        return [(r + ["."] * w)[:w] for r in strs]
    w = max(len(r) for r in strs)
    out = []
    for r in strs:
        row = list((r + "." * w)[:w])
        out.append(row)
    return out

# -----------------------------------------------------------------------------
# Level table: every SMB3 level encoded compactly
# Format key: (world, level_num, kind, theme, strings)
#   kind: 'normal', 'fortress', 'airship', 'tower', 'castle'
# -----------------------------------------------------------------------------
LEVELS: list[dict] = []

def _addlvl(world: int, lvl: str, kind: str, theme: str, rows: list[str], music: str = "overworld", time: int = 300) -> None:
    LEVELS.append({
        "world": world, "lvl": lvl, "kind": kind, "theme": theme,
        "grid": _str_grid(rows), "music": music, "time": time,
    })

# ============= WORLD 1: GRASS LAND =============
_addlvl(1, "1-1", "normal", "grass", [
    "..............................................................................................................................................................",
    "..............................................................................................................................................................",
    "..............................................................................................................................................................",
    "..............................................................................................................................................................",
    "..............................................................................................................................................................",
    "..............................................................................................................................................................",
    "..............................................................................................................................................................",
    ".......................?...M.?....................c.c.c.c.c................................................................................G..................",
    ".....................................BB?B....................................BBBBB...BB...............BBB.....................................................",
    "..............................................................................................................................................................",
    ".............................................................c.c....................c.c.c..............................c.c....BBB............................",
    "..............................g........g..g..............ggg.........y.....g..g.......................gg............g.g................gg....................",
    "..............................................P...........###..P.....##.................P.....##.....P.................P.....#####.....##...P................",
    "##############################################pp##########################pp#################pp########################pp###############pp###pp################",
])
_addlvl(1, "1-2", "normal", "underground", [
    "........................................................................................",
    "........................................................................................",
    "........................................................................................",
    "########################################################################################",
    "........................................................................................",
    "........c.c.c.....M..........c.c.c.....F.....c.c.c..........c.c.c....c.c.c......G.......",
    "................BBBBB....BBB......BBBBB.....BBB..........BBBB......BBB.................",
    "........................................................................................",
    "..........c.c..........BBB....................BB?B........c......BB?B......c.c.........",
    "..............g..g........g........g..g.......g.....g.k........g..g.k.....g.............",
    "..#####...........##........###........##........###..........##.......###...#####......",
    "##########################################################################pp############",
    "###########################################P############################################",
    "########################################################################################",
])
_addlvl(1, "1-3", "normal", "grass", [
    "................................................................................................................................",
    "................................................................................................................................",
    "................................................................................................................................",
    "................................................................................................................................",
    "....-----......--------......-----....---------......-----------.....----........----------......-----................G..........",
    "................................................................................................................................",
    "..............c..c..........c.c.c...............c.c.................c..c.................c.c..c.c.................c.c...........",
    "....=====.........====....=========.......======......==========.....=====........=========......======............=====.........",
    "..............g.................r.r.................g..k.......................r.k........................g..g..................",
    "......?M....=====.....=...======...=.....==.....=========......===.........=========...........==========........============....",
    "..........................................................................................l...................................",
    "................................................................................................................................",
    "................................................................................................................................",
    "................................................................................................................................",
])
_addlvl(1, "1-4", "normal", "grass", [
    "..........................................................................................................................................",
    "..........................................................................................................................................",
    "..........................................................................................................................................",
    "..........................................................................................................................................",
    ".....................c.c.c....................M............................c.c.c......?...................................................",
    "...................BBBBBBB...................BBB...........................BBBBBBB...BBB..................................................",
    "..........................................................................................................................................",
    "..............................c..c............................c..c...................................c..c......B?B........G.............",
    ".............................========.........................========..............................========...................JJJ.......",
    "..............................................................................................................................JJJJJ......",
    "...........y...........g..g....................y....g.....k............y......g.g..............g..k.................g..g.....JJJJJJJ.....",
    "............P............................P............................P.....................P............P...................JJJJJJJJ...",
    "############pp########################pp#######################pp##########pp################pp#############pp##############################",
    "############################################################################################################################################",
])
_addlvl(1, "1-5", "normal", "grass", [
    "....................................................................................................................................................",
    "....................................................................................................................................................",
    "....................................................................................................................................................",
    "....................................................................................................................................................",
    "....................................................................................................................................................",
    "...........c.c.c..............................................c.c....................M..............c.c.c......................G...............",
    "..........BBBBBBB.............c.c.c..........c.c.c...........BBBBB...c.c.c.........BBB?BB.........BBBBBBBB....................................",
    "........................................................................................................................BBB...................",
    "...................c.c..............................c.c....................c.c..............c.c..............................................",
    "..................========.........=====...........========.............========..........========...........................................",
    "...y....g....g...........k.....g.......g....h.................r.....k.........g.....g....h............g.g..g...............JJJJJJJJJJJJ......",
    "....P............................................................................................................JJJJ...JJJJJJJJJJJJJJJJ....",
    "####pp###############################################################################################################################################",
    "####################################################################################################################################################",
])
_addlvl(1, "1-6", "normal", "grass", [
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    "........................................................................................................................",
    ".....c..c..c.....F............c..c..............c.c.c..........M.........c.c.c..............................G..........",
    "...BBBBBBBBBBB................BBBBBB............BBBBBB......BBBBBBB....BBBBBBBB................BBB....................",
    "........................................................................................................................",
    "..................c..c....................c..c..................c..c................c.c.c............................",
    ".................========................========..............========............========.........................",
    "....g..g.....g..............k..r.........g..g..............k...........g.....g..g...........h.........g...........",
    "............................................................................P...................................JJJJ.",
    "##############################################################################pp####################################JJJJ",
    "####################################################################################################################JJJJ",
])
_addlvl(1, "1-Fort", "fortress", "fortress", [
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "Z.....................................................................................Z",
    "Z.....................................................................................Z",
    "Z..........c.c.c...........M............c.c.c.........F....................!.........Z",
    "Z........ZZZZZZZ........ZZZZZZ.........ZZZZZZZ......ZZZZZZ..............ZZZZZ........Z",
    "Z.....................................................................................Z",
    "Z..........d...d............d...........d..t......d.......t...d.........@..........Z",
    "Z.......ZZZZZZZ.........ZZZZZZZ.....ZZZZZZZZ...ZZZZZZZZZZZZZZZZZ...ZZZZZZZZZZZZ.....Z",
    "Z.....................................................................................Z",
    "Z........s........s..........s.s.........s.s........s.s.s.....................Z......Z",
    "Z......ZZZZZ.....ZZZZ......ZZZZZZ......ZZZZ......ZZZZZZZZZZ..............ZZZZZZZ.....Z",
    "Z.....................................................................................Z",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
], music="fortress", time=300)

_addlvl(1, "1-Air", "airship", "airship", [
    "..............................................................................................................",
    "..............................................................................................................",
    "..............................................................................................................",
    "..............................................................................................................",
    "..............................................................................................................",
    "...........XXXX..............XXXX..............XXXX..............XXXX.................................!.......",
    "..........XXXXXXX...........XXXXXX............XXXXXXX...........XXXXXXX..................................@....",
    "..........X.b...X..........X.b.h.X............X.b...X..........X.h..b.X............................XXXXXXX....",
    "..........X.....X..........X.....X............X.....X..........X......X...........................XXXXXXXXXX.",
    "..........XXXXXXX..........XXXXXXX............XXXXXXX..........XXXXXXXX...........................XXXXXXXXXX.",
    "..............XX...............XX..................XX...............XX............................XX.....XX.",
    "..............XX...............XX..................XX...............XX............................XX.....XX.",
    "..............XX...............XX..................XX...............XX............................XX.....XX.",
    "..............................................................................................................",
], music="airship", time=300)


# ============= WORLD 2: DESERT LAND =============
_addlvl(2, "2-1", "normal", "desert", [
    "..............................................................................................................................",
    "..............................................................................................................................",
    "..............................................................................................................................",
    "..............................................................................................................................",
    ".........c.c.c.........M..............c.c.c................F..........c.c.c......................................G..........",
    ".......BBBBBBBB......BBBBB............BBBBBBB..........BBBBBBB......BBBBBBBB................BBB............................",
    "..............................................................................................................................",
    ".....s.....s.s....s............s..............s.s.....s..............s..s....s.....s.s..............s....................",
    "..............................................................................................................................",
    ".......g.....g.....k....r........g.g....g........k....r...........h..............g.....k.r.......g.g.....h....g..........",
    "...............P.....................P..........................P.....................P..........................JJJJJ....",
    "###############pp###################pp##########################pp###################pp#########################################",
    "###############################################################################################################################",
    "###############################################################################################################################",
])
_addlvl(2, "2-2", "normal", "desert", [
    "....................................................................................................................",
    "....................................................................................................................",
    "....................................................................................................................",
    "....................................................................................................................",
    "....................................................................................................................",
    "..........c..c.......M..........c.c.c..........F............c..c..........c..c.....M................G.............",
    "........BBBBBB......BBB.........BBBBBB.........BBBB.........BBBBBB........BBBBBB...BBB.................JJJ........",
    "....................................................................................................................",
    "................................-----.........................-----........................---..................",
    ".....c..c..........c.c.c..........c.c..............c..c..........c.c................c..c....JJJ..................",
    "...========.......========.....=======...........=======........========...........========.....JJJJJ............",
    "....g....k.........k...r........g..g.k............h..k............g.g.k............g..g.r.....JJJJJJJJJJJ........",
    "####################################################################################################################",
    "####################################################################################################################",
])
_addlvl(2, "2-3", "normal", "desert", [
    "...........................................................................................................................",
    "...........................................................................................................................",
    "...........................................................................................................................",
    "...........................................................................................................................",
    ".......c.c......M..........c.c.c..........F..........c.c.c......L.........c.c.c.......................G................",
    ".....BBBBBB...BBB.........BBBBBBB........BBBB.......BBBBBBB....BBBB......BBBBBBBB................BBB.....................",
    "...........................................................................................................................",
    ".................b...........b................b...........b................b......................b...................",
    "...........................................................................................................................",
    "......g....g..k..r...........g.g.h.........k..r......h..........g.h..k....r.......h.......g.....k..r.....g.h...........",
    "...........................................................................................................................",
    "###########################################################################################################################",
    "###########################################################################################################################",
    "###########################################################################################################################",
], music="overworld"),

_addlvl(2, "2-4", "normal", "desert", [
    "............................................................................................................",
    "............................................................................................................",
    "............................................................................................................",
    "............................................................................................................",
    "............................................................................................................",
    ".......c.c.c......M..........c.c.c......F.........c.c.c.......!......c.c.c................G..............",
    ".....BBBBBBBB....BBB.........BBBBBBB....BBBB.....BBBBBBBB.....BB....BBBBBBBB.........BBB..................",
    "............................................................................................................",
    "...........s.s....s.s..s.s..............s.s.s....s.s.s....s.s..............s.s....s..s.....s.s.s..s....",
    "............................................................................................................",
    ".....g..g....k..g.r......h....g....g..k...r.....g.g..k....r......g.g.g..k....h......g.g.k....r..........",
    "............................................................................................................",
    "############################################################################################################",
    "############################################################################################################",
])
_addlvl(2, "2-5", "normal", "desert", [
    "..........................................................................................................................",
    "..........................................................................................................................",
    "..........................................................................................................................",
    "..........................................................................................................................",
    "............c.c..........M.........c.c.c.......F.........c.c.c......L.......c.c.c....M..................G............",
    "..........BBBBB.........BBB........BBBBBBB.....BBBB......BBBBBBB....BBBB....BBBBBBB...BBB.............................",
    "..........................................................................................................................",
    ".................-----..............-----...................-----...........-----................-----................",
    "............c..c.............c.c.c......................c..c................c..c............c.c.c.....................",
    "..........========.........========......c..c.........========............========.........========...................",
    "....g..k...........h...g..g........k...========.........g..r..k...........g..g..k.r.....g..r..k.........h..g.k.....",
    "..........................................................................................................................",
    "##########################################################################################################################",
    "##########################################################################################################################",
])
_addlvl(2, "2-Pyramid", "fortress", "desert", [
    "....................................................................................",
    "....................................................................................",
    "....................................................................................",
    "....................................................................................",
    ".......c.c.c......M.........c.c.c......F........!......c.c.c.....................",
    ".....BBBBBBBB....BBB........BBBBBBB....BBBB....BBBBB...BBBBBBBB.....@......BBB....",
    "....................................................................................",
    ".......d...d.....t.....d........t...d......d......t...d........d............s..s.",
    "......BBBBBBB...BBBBB...BBBBB.....BBBBBB...BBBB....BBBBB....BBBBBBBBBBBBBBBBBBBBB.",
    "....................................................................................",
    "....s..s.s..........s.s.s..s..............s.s....s.s.s..............................",
    "....................................................................................",
    "####################################################################################",
    "####################################################################################",
], music="fortress"),

_addlvl(2, "2-Fort", "fortress", "fortress", [
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "Z..............................................................................Z",
    "Z..............................................................................Z",
    "Z........c..c..........M.........c.c.c......F............!..................Z",
    "Z......ZZZZZZ........ZZZ.........ZZZZZZZ....ZZZZ........ZZZZZ......@........Z",
    "Z..............................................................................Z",
    "Z..t.....d....d.....t.......d........t...d......d......t...d........d.......Z",
    "Z..ZZZZZZZZZZZ.....ZZZZ.....ZZZZ.......ZZZZ..ZZZZ.....ZZZZ......ZZZZZZZZZ...Z",
    "Z..............................................................................Z",
    "Z....s..s.s..........s.s.s..s..............s.s....s.s.s.....................Z",
    "Z..............................................................................Z",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
], music="fortress"),

_addlvl(2, "2-Air", "airship", "airship", [
    "..............................................................................................................",
    "..............................................................................................................",
    "..............................................................................................................",
    "..............................................................................................................",
    "..............................................................................................................",
    "...........XXXX..............XXXX..............XXXX..............XXXX...................................@....",
    "..........XXXXXXX...........XXXXXX............XXXXXXX...........XXXXXXX..........!.................XXXXXXX....",
    "..........X.b.h.X..........X.b.b.X............X.h.h.X..........X.h..b.X.........XXXX..............XXXXXXXXXX.",
    "..........X.....X..........X.....X............X.....X..........X......X.........XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "..........XXXXXXX..........XXXXXXX............XXXXXXX..........XXXXXXXX.........XX.............................",
    "..............XX...............XX..................XX...............XX............XX.............................",
    "..............XX...............XX..................XX...............XX............................................",
    "..............................................................................................................",
    "..............................................................................................................",
], music="airship"),


# ============= WORLD 3: WATER LAND =============
_W3_TIME = 350
for _ln, _theme, _kind in [
    ("3-1", "water", "normal"),
    ("3-2", "water", "normal"),
    ("3-3", "water", "normal"),
    ("3-4", "water", "normal"),
    ("3-5", "water", "normal"),
    ("3-6", "water", "normal"),
    ("3-7", "water", "normal"),
    ("3-8", "water", "normal"),
    ("3-9", "water", "normal"),
]:
    pass

def _gen_water_level(name: str, seed: int) -> None:
    rng = random.Random(seed)
    width = 130
    rows = []
    sky = "." * width
    rows.append(sky)
    rows.append(sky)
    rows.append(sky)
    # cloud row
    cloud_row = list(sky)
    for x in range(5, width - 5, rng.randint(8, 20)):
        for off, ch in enumerate("---"):
            if x + off < width:
                cloud_row[x + off] = "-"
    rows.append("".join(cloud_row))
    # coins / blocks
    item_row = list(sky)
    for x in range(8, width - 8, rng.randint(10, 18)):
        kind = rng.choice(["?M", "BB?B", "B?B", "BBB", "BB"])
        for i, c in enumerate(kind):
            if x + i < width:
                item_row[x + i] = c
    rows.append("".join(item_row))
    rows.append(sky)
    coin_row = list(sky)
    for x in range(3, width - 3, rng.randint(4, 7)):
        if rng.random() < 0.6:
            coin_row[x] = "c"
    rows.append("".join(coin_row))
    # platform/water mix
    plat = list(sky)
    for x in range(5, width - 5, rng.randint(14, 22)):
        run = rng.randint(3, 7)
        for i in range(run):
            if x + i < width:
                plat[x + i] = "="
    rows.append("".join(plat))
    # enemy row
    enemy_row = list(sky)
    enemies = "kkrgggchy"
    for x in range(6, width - 6, rng.randint(8, 14)):
        enemy_row[x] = rng.choice(list(enemies))
    rows.append("".join(enemy_row))
    # water and ground
    water_row = list("~" * width)
    # gaps with water below
    ground = list("#" * width)
    last_g = width - 3
    for _ in range(rng.randint(3, 6)):
        gap_x = rng.randint(15, last_g - 8)
        gap_w = rng.randint(3, 5)
        for i in range(gap_w):
            ground[gap_x + i] = "."
    rows.append("".join(ground))
    rows.append("".join(water_row))
    rows.append("".join(["#" if c == "#" else "~" for c in ground]))
    # goal
    rows_str = []
    for r in rows:
        rows_str.append(r)
    # mark goal somewhere near end
    rl = list(rows_str[7])
    if width - 8 < len(rl):
        rl[width - 8] = "G"
    rows_str[7] = "".join(rl)
    while len(rows_str) < 14:
        rows_str.append("#" * width)
    _addlvl(3, name, "normal", "water", rows_str, time=350)

# Generate 9 water levels with varying seeds
for i, name in enumerate(["3-1","3-2","3-3","3-4","3-5","3-6","3-7","3-8","3-9"]):
    _gen_water_level(name, 1000 + i * 17)

# W3 fortresses (2)
_addlvl(3, "3-Fort1", "fortress", "fortress", [
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "Z..............................................................................Z",
    "Z......c..c.......M.........c.c.c......F............c..c.................!.....Z",
    "Z....ZZZZZZ......ZZZ.........ZZZZZZ....ZZZZ.........ZZZZZZ............ZZZ.....Z",
    "Z.........................................................................@....Z",
    "Z..t....d.....d......t.......d........t...d......d......t..d.....d.....Z......Z",
    "Z..ZZZZZZZZZZZ.....ZZZZ.....ZZZZ.......ZZZZ..ZZZZ.....ZZZZ......ZZZZZZZZZ.....Z",
    "Z..............................................................................Z",
    "Z...s..s.s..........s.s.s..s..............s.s....s.s.s........................Z",
    "Z..............................................................................Z",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
], music="fortress")
_addlvl(3, "3-Fort2", "fortress", "fortress", [
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "Z........c.c..........F............M.........c..c.......c..c.................Z",
    "Z......ZZZZZZ......ZZZZ............ZZZ........ZZZZZZ.....ZZZZ.................Z",
    "Z..............................................................................Z",
    "Z..d..t...d.....d.....t......d........t...d......d......t...d.....!.@.......Z",
    "Z..ZZZZZZZZZZ.....ZZZZ.....ZZZZ.......ZZZZ..ZZZZ.....ZZZZ......ZZZZZZZZZ.....Z",
    "Z..............................................................................Z",
    "Z...s..s.s..........s.s.s..s..............s.s....s.s.s........................Z",
    "Z..............................................................................Z",
    "Z..............................................................................Z",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
], music="fortress")

# Generic airship for each remaining world
def _gen_airship(world: int, name: str) -> None:
    _addlvl(world, name, "airship", "airship", [
        "..............................................................................................................",
        "..............................................................................................................",
        "..............................................................................................................",
        "..............................................................................................................",
        "...........XXXX..............XXXX..............XXXX..............XXXX...................................@....",
        "..........XXXXXXX...........XXXXXX............XXXXXXX...........XXXXXXX..........!.................XXXXXXX....",
        "..........X.b.h.X..........X.b.b.X............X.h.h.X..........X.h..b.X.........XXXX..............XXXXXXXXXX.",
        "..........X.....X..........X.....X............X.....X..........X......X.........XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "..........XXXXXXX..........XXXXXXX............XXXXXXX..........XXXXXXXX.........XX.............................",
        "..............XX...............XX..................XX...............XX............................................",
        "..............XX...............XX..................XX...............XX............................................",
        "..............................................................................................................",
        "..............................................................................................................",
        "..............................................................................................................",
    ], music="airship", time=300)

_gen_airship(3, "3-Air")


# ============= WORLDS 4-7: PROCEDURAL FROM THEMES =============
def _gen_themed_level(world: int, name: str, theme: str, seed: int, special: str = "") -> None:
    """Procedurally generate a level for the given theme."""
    rng = random.Random(seed)
    width = rng.randint(120, 180)
    rows = [["."] * width for _ in range(14)]

    # Decorations row
    deco_y = 11
    # Ground (last 2 rows)
    for y in (12, 13):
        for x in range(width):
            rows[y][x] = "#"
    # gaps
    n_gaps = rng.randint(2, 5)
    for _ in range(n_gaps):
        gx = rng.randint(20, width - 25)
        gw = rng.randint(2, 4)
        for i in range(gw):
            rows[12][gx + i] = "."
            rows[13][gx + i] = "."

    # Block patterns
    n_blocks = rng.randint(6, 12)
    for _ in range(n_blocks):
        x = rng.randint(8, width - 12)
        y = rng.randint(5, 9)
        kind = rng.choice(["BB?B", "?M?", "BBB", "BB?B", "B?B", "BBBB", "BBBBB"])
        # avoid overlap with existing
        for i, c in enumerate(kind):
            if x + i < width and rows[y][x + i] == ".":
                rows[y][x + i] = c

    # Pipes
    n_pipes = rng.randint(2, 5)
    for _ in range(n_pipes):
        px = rng.randint(15, width - 8)
        ph = rng.randint(2, 4)
        # check clear
        ok = all(rows[12 - ph][px] == "." for _ in range(1))
        if ok:
            for i in range(ph):
                rows[12 - i][px] = "p"
            rows[12 - ph][px] = "P"
            # piranha sometimes
            if rng.random() < 0.5 and 12 - ph - 1 >= 0:
                rows[12 - ph - 1][px] = "y"

    # Platforms
    n_platforms = rng.randint(4, 9)
    for _ in range(n_platforms):
        px = rng.randint(8, width - 10)
        plen = rng.randint(3, 7)
        py = rng.randint(4, 9)
        for i in range(plen):
            if px + i < width and rows[py][px + i] == ".":
                rows[py][px + i] = "=" if rng.random() < 0.6 else "-"

    # Coins
    for _ in range(rng.randint(15, 30)):
        x = rng.randint(2, width - 3)
        y = rng.randint(3, 10)
        if rows[y][x] == ".":
            rows[y][x] = "c"

    # Enemies
    enemy_pool = {
        "grass": ["g", "k", "g", "r", "g"],
        "desert": ["g", "k", "r", "h", "g"],
        "water": ["k", "g", "h", "k"],
        "giant": ["g", "k", "r", "k"],
        "sky": ["g", "k", "l", "k"],
        "ice": ["g", "k", "r", "g"],
        "pipe": ["g", "y", "k", "h"],
        "dark": ["d", "z", "d", "t"],
        "night": ["z", "d", "g", "z"],
    }
    enemies = enemy_pool.get(theme, ["g", "k", "r"])
    for _ in range(rng.randint(6, 14)):
        x = rng.randint(12, width - 8)
        if rows[11][x] == "." and rows[12][x] == "#":
            rows[11][x] = rng.choice(enemies)

    # Specials based on theme
    if theme == "ice":
        # ice patches on ground
        for _ in range(rng.randint(3, 6)):
            ix = rng.randint(10, width - 10)
            iw = rng.randint(4, 8)
            for i in range(iw):
                if ix + i < width:
                    rows[12][ix + i] = "I"

    if theme == "giant":
        # giant blocks scattered
        for _ in range(rng.randint(2, 4)):
            gx = rng.randint(15, width - 15)
            gy = rng.randint(8, 10)
            for dx in range(2):
                for dy in range(2):
                    if 0 <= gy + dy < 14 and gx + dx < width and rows[gy + dy][gx + dx] == ".":
                        rows[gy + dy][gx + dx] = "J"

    if theme == "sky":
        # Lots of cloud platforms
        for _ in range(rng.randint(6, 10)):
            cx = rng.randint(5, width - 8)
            cw = rng.randint(3, 6)
            cy = rng.randint(5, 10)
            for i in range(cw):
                if cx + i < width and rows[cy][cx + i] == ".":
                    rows[cy][cx + i] = "-"

    # Power-up guarantee: at least one mushroom or fire flower
    placed_power = any("M" in "".join(r) or "F" in "".join(r) for r in rows)
    if not placed_power:
        for y in range(5, 10):
            for x in range(5, width - 10):
                if rows[y][x] == ".":
                    rows[y][x] = "M"
                    placed_power = True
                    break
            if placed_power:
                break

    # Goal at right
    rows[11][width - 4] = "G"

    # Start at left
    rows[11][2] = "S"

    rows_str = ["".join(r) for r in rows]
    _addlvl(world, name, "normal", theme, rows_str, time=300)


# WORLD 4: GIANT LAND (6 levels)
for i, name in enumerate(["4-1","4-2","4-3","4-4","4-5","4-6"]):
    _gen_themed_level(4, name, "giant", 4000 + i * 23)
_addlvl(4, "4-Fort1", "fortress", "fortress", LEVELS[5]["grid"] if False else _str_grid([
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "Z..............c.c.....F............M.........c..c.......c..c....!.....@....Z",
    "Z..............ZZZZZZ......ZZZZ............ZZZ........ZZZZZZ.....ZZZZ.........Z",
    "Z..............................................................................Z",
    "Z..d..t...d.....d.....t......d........t...d......d......t...d................Z",
    "Z..ZZZZZZZZZZ.....ZZZZ.....ZZZZ.......ZZZZ..ZZZZ.....ZZZZ......ZZZZZZZZZ.....Z",
    "Z..............................................................................Z",
    "Z...s..s.s..........s.s.s..s..............s.s....s.s.s........................Z",
    "Z..............................................................................Z",
    "Z..............................................................................Z",
    "Z..............................................................................Z",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
])[0] if False else [
    list("ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"),
])
# Cleaner: just call fortress generator
def _gen_fortress(world: int, name: str, seed: int) -> None:
    rng = random.Random(seed)
    width = rng.randint(80, 120)
    rows = [["Z"] * width if y == 0 or y == 13 else (["Z"] + ["."] * (width - 2) + ["Z"]) for y in range(14)]
    # bottom ground rows
    for y in (12, 13):
        for x in range(width):
            rows[y][x] = "Z"
    # platforms
    for _ in range(rng.randint(5, 9)):
        x = rng.randint(3, width - 8)
        plen = rng.randint(3, 6)
        py = rng.randint(4, 10)
        for i in range(plen):
            if x + i < width - 1:
                rows[py][x + i] = "Z"
    # enemies: dry bones, thwomps
    for _ in range(rng.randint(4, 8)):
        x = rng.randint(5, width - 10)
        rows[11][x] = rng.choice(["d", "d", "t", "d"])
    # power-up
    rows[6][10 if 10 < width - 2 else width - 5] = "F"
    # axe
    rows[10][width - 8] = "!"
    # boss
    rows[11][width - 5] = "@"
    rows[11][1] = "S"
    # outer walls maintained
    for y in range(14):
        rows[y][0] = "Z"
        rows[y][width - 1] = "Z"
    rows_str = ["".join(r) for r in rows]
    _addlvl(world, name, "fortress", "fortress", rows_str, music="fortress", time=300)

_gen_fortress(4, "4-Fort1", 4100)
_gen_fortress(4, "4-Fort2", 4101)
_gen_airship(4, "4-Air")

# WORLD 5: SKY LAND (9 levels: ground levels + sky levels)
for i, name in enumerate(["5-1","5-2","5-3","5-4","5-5","5-6","5-7","5-8","5-9"]):
    theme = "sky" if i >= 3 else "grass"
    _gen_themed_level(5, name, theme, 5000 + i * 31)
_gen_fortress(5, "5-Fort1", 5100)
_gen_fortress(5, "5-Fort2", 5101)
# Tower
_addlvl(5, "5-Tower", "tower", "fortress", [
    "ZZZZZZZZZZZZZZZZZZZZ",
    "Z.......!.........Z",
    "Z.................Z",
    "Z....ZZZZZZ.......Z",
    "Z.d............ZZ.Z",
    "Z........t........Z",
    "Z.ZZZZ............Z",
    "Z..........ZZZZ...Z",
    "Z....d............Z",
    "Z.ZZZZZZ......t...Z",
    "Z.................Z",
    "Z.....@...........Z",
    "Z.................Z",
    "ZZZZZZZZZZZZZZZZZZZZ",
], music="fortress")
_gen_airship(5, "5-Air")

# WORLD 6: ICE LAND (10 levels)
for i, name in enumerate(["6-1","6-2","6-3","6-4","6-5","6-6","6-7","6-8","6-9","6-10"]):
    _gen_themed_level(6, name, "ice", 6000 + i * 37)
_gen_fortress(6, "6-Fort1", 6100)
_gen_fortress(6, "6-Fort2", 6101)
_gen_fortress(6, "6-Fort3", 6102)
_gen_airship(6, "6-Air")

# WORLD 7: PIPE LAND (9 levels)
for i, name in enumerate(["7-1","7-2","7-3","7-4","7-5","7-6","7-7","7-8","7-9"]):
    _gen_themed_level(7, name, "pipe", 7000 + i * 41)
_gen_fortress(7, "7-Fort1", 7100)
_gen_fortress(7, "7-Fort2", 7101)
_addlvl(7, "7-Plant", "fortress", "pipe", [
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "P..................................................!.....@P",
    "P..........y..........y.........y............y.............P",
    "P.PPPP....P..........P........P............P.....PPPP.....P",
    "P.........................................................P",
    "P....c.c.c......c.c.c......c.c.c......c.c.c......c.c.c....P",
    "P..PPPPPPPP....PPPPPPPP....PPPPPPP....PPPPPPP....PPPPPPP..P",
    "P.........................................................P",
    "P....g....k....r....g....k....r....g....k....r....g.......P",
    "P..........................................................P",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
], music="overworld")
_gen_airship(7, "7-Air")

# WORLD 8: DARK LAND (final world)
for i, name in enumerate(["8-Tank1","8-Navy","8-Hand1","8-Tank2","8-Hand2","8-Air"]):
    if "Tank" in name or "Navy" in name:
        _addlvl(8, name, "airship", "airship", [
            "..............................................................................................................",
            "..............................................................................................................",
            "..........bb...............bb..............bb..............bb..............bb..........................@.....",
            "..XXXXX..XXXXXX...XXXXX..XXXXXX...XXXXX..XXXXXX..XXXXX..XXXXXX..XXXXX..XXXXXX............!........XXXXXXX.....",
            "..XbbbX..X.b.h.X..XbbbX..X.b.b.X..XbbbX..X.h.h.X..XbbbX..X.h..bX..XbbbX..X.b.bX...........XXXXXX....XXXXXXXXXX",
            "..X...X..X.....X..X...X..X.....X..X...X..X.....X..X...X..X....X..X...X..X....X...........XXXXXXXXXXXXXXXXXXXXX",
            "..XXXXX..XXXXXXX..XXXXX..XXXXXXX..XXXXX..XXXXXXX..XXXXX..XXXXXXX..XXXXX..XXXXXX...........XX..................",
            "....XX.......XX......XX......XX......XX......XX......XX......XX......XX......XX...........XX..................",
            "....XX.......XX......XX......XX......XX......XX......XX......XX......XX......XX...........XX..................",
            "..............................................................................................................",
            "..............................................................................................................",
            "..............................................................................................................",
            "..............................................................................................................",
            "..............................................................................................................",
        ], music="airship", time=400)
    elif "Hand" in name:
        _addlvl(8, name, "airship", "dark", [
            "..............................................................................................................",
            "..............................................................................................................",
            "..............................................................................................................",
            "..............................................................................................................",
            "..............................................................................................................",
            "............................................................................................................G.",
            "..-----..........-----.............-----...........-----.........-----.............-----........-----........",
            "...............................c...........c.....................c..............c...........c................",
            "...........k........g.........h............r......g.........k........r.........h.................g..........",
            "...-----.........-----..............-----..........-----.......-----..............-----........-----.........",
            "..............................................................................................................",
            "..............................................................................................................",
            "##############################################################################################################",
            "##############################################################################################################",
        ], music="overworld", time=400)
    else:
        _gen_airship(8, name)

# Bowser's castle
_addlvl(8, "8-Bowser", "castle", "dark", [
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "Z..........................................................................................Z",
    "Z..........c.c.c......F.........!....c.c.c......M.........c.c.c..................@........Z",
    "Z........ZZZZZZZ.....ZZZZ.....ZZZZ...ZZZZZZZ...ZZZZ.....ZZZZZZZZ............ZZZZZZZZZ.....Z",
    "Z..........................................................................................Z",
    "Z..t...d......d.....t.......d........t...d......d......t...d..d...t....d.................Z",
    "Z..ZZZZZZZZZZZ.....ZZZZ.....ZZZZ.......ZZZZ..ZZZZ.....ZZZZ......ZZZZZZZZZ..ZZZZZZZZ.......Z",
    "Z..........................................................................................Z",
    "Z..s..s.s..........s.s.s..s..............s.s....s.s.s.....s.s.s.....s.s.s.................Z",
    "Z..........................................................................................Z",
    "Z..........................................................................................Z",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
    "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ",
], music="fortress", time=500)


# =============================================================================
# ENTITY CLASSES
# =============================================================================
@dataclass
class Entity:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    w: int = 16
    h: int = 16
    alive: bool = True
    on_ground: bool = False
    facing: int = -1
    kind: str = "entity"
    timer: float = 0.0
    state: str = "walk"  # walk, stunned, dead, shell, fly, swim
    anim: float = 0.0

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)


class Goomba(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, vx=-30.0, w=16, h=16, kind="goomba")

    def update(self, dt: float, level: "Level") -> None:
        if self.state == "dead":
            self.timer -= dt
            if self.timer <= 0:
                self.alive = False
            return
        self.anim += dt
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        _move_entity(self, dt, level, can_drop=False)

    def stomp(self) -> None:
        self.state = "dead"
        self.timer = 0.5
        self.vx = 0


class Koopa(Entity):
    def __init__(self, x: float, y: float, red: bool = False):
        super().__init__(x, y, vx=-30.0, w=16, h=24, kind=("koopa_r" if red else "koopa_g"))
        self.red = red

    def update(self, dt: float, level: "Level") -> None:
        if self.state == "dead":
            self.timer -= dt
            if self.timer <= 0:
                self.alive = False
            return
        self.anim += dt
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        _move_entity(self, dt, level, can_drop=not self.red)

    def stomp(self) -> None:
        if self.state == "walk":
            self.state = "shell"
            self.vx = 0
            self.h = 16
            self.timer = 5.0
        elif self.state == "shell":
            self.state = "kicked"
            self.vx = 200.0
            self.timer = 8.0

    def kick(self, dir: int) -> None:
        self.state = "kicked"
        self.vx = 220.0 * dir
        self.timer = 8.0


class Piranha(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, w=16, h=24, kind="piranha")
        self.base_y = y
        self.timer = 0.0
        self.state = "rising"
        self.y_off = 0.0

    def update(self, dt: float, level: "Level") -> None:
        self.timer += dt
        # 2s up, 2s down cycle
        cycle = self.timer % 4.0
        if cycle < 2.0:
            self.y_off = -24.0 * (cycle / 2.0)
        else:
            self.y_off = -24.0 * (1.0 - (cycle - 2.0) / 2.0)
        self.y = self.base_y + self.y_off
        self.anim += dt


class HammerBro(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, vx=-20.0, w=16, h=24, kind="hammerbro")
        self.hammer_timer = 1.0
        self.jump_timer = 2.0

    def update(self, dt: float, level: "Level") -> None:
        if self.state == "dead":
            self.timer -= dt
            if self.timer <= 0:
                self.alive = False
            return
        self.anim += dt
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        # bobble in small range
        if self.on_ground:
            self.jump_timer -= dt
            if self.jump_timer <= 0:
                self.vy = -150
                self.jump_timer = 2.0
        _move_entity(self, dt, level, can_drop=False)

    def stomp(self) -> None:
        self.state = "dead"
        self.timer = 0.5


class Bullet(Entity):
    def __init__(self, x: float, y: float, dir: int):
        super().__init__(x, y, vx=80.0 * dir, w=16, h=16, kind="bullet")
        self.facing = dir

    def update(self, dt: float, level: "Level") -> None:
        self.x += self.vx * dt


class Lakitu(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, w=16, h=16, kind="lakitu")
        self.drop_timer = 2.0

    def update(self, dt: float, level: "Level") -> None:
        if self.state == "dead":
            self.timer -= dt
            if self.timer <= 0:
                self.alive = False
            return
        self.anim += dt
        # Follow player
        target = level.player.x + 100
        self.x += (target - self.x) * dt * 0.5
        self.drop_timer -= dt
        if self.drop_timer <= 0:
            self.drop_timer = 3.0
            level.entities.append(Spiny(self.x, self.y + 16))

    def stomp(self) -> None:
        self.state = "dead"
        self.timer = 0.5


class Spiny(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, vx=-50.0, w=16, h=16, kind="spiny")

    def update(self, dt: float, level: "Level") -> None:
        if self.state == "dead":
            self.timer -= dt
            if self.timer <= 0:
                self.alive = False
            return
        self.anim += dt
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        _move_entity(self, dt, level, can_drop=True)


class DryBones(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, vx=-25.0, w=16, h=24, kind="drybones")

    def update(self, dt: float, level: "Level") -> None:
        if self.state == "dead":
            self.timer -= dt
            if self.timer <= 0:
                self.alive = False
            return
        self.anim += dt
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        _move_entity(self, dt, level, can_drop=False)

    def stomp(self) -> None:
        # Dry bones reassemble - just push back
        self.state = "stunned"
        self.timer = 2.0


class Thwomp(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, w=16, h=16, kind="thwomp")
        self.base_y = y
        self.state = "wait"
        self.timer = 0.0

    def update(self, dt: float, level: "Level") -> None:
        self.timer += dt
        if self.state == "wait":
            if abs(level.player.x - self.x) < 32 and self.timer > 1.0:
                self.state = "fall"
                self.timer = 0
        elif self.state == "fall":
            self.vy = min(self.vy + GRAVITY * 1.5 * dt, MAX_FALL)
            self.y += self.vy * dt
            if self.y > self.base_y + 80:
                self.state = "return"
                self.vy = 0
                self.timer = 1.0
        elif self.state == "return":
            self.timer -= dt
            if self.timer <= 0:
                self.y -= 30 * dt
                if self.y <= self.base_y:
                    self.y = self.base_y
                    self.state = "wait"
                    self.timer = 0


class Boss(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, vx=-40.0, w=24, h=24, kind="boss")
        self.hp = 3
        self.jump_timer = 1.5

    def update(self, dt: float, level: "Level") -> None:
        if self.state == "dead":
            self.timer -= dt
            if self.timer <= 0:
                self.alive = False
            return
        self.anim += dt
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        self.jump_timer -= dt
        if self.jump_timer <= 0 and self.on_ground:
            self.vy = -200
            self.jump_timer = random.uniform(1.0, 2.5)
            self.vx = random.choice([-50, -30, 30, 50])
        _move_entity(self, dt, level, can_drop=False)

    def hit(self) -> bool:
        self.hp -= 1
        if self.hp <= 0:
            self.state = "dead"
            self.timer = 1.0
            return True
        return False


# Item entities
class Mushroom(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, vx=60.0, w=16, h=16, kind="mushroom")

    def update(self, dt: float, level: "Level") -> None:
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        _move_entity(self, dt, level, can_drop=True)


class FireFlower(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, w=16, h=16, kind="fireflower")


class Star(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, vx=60.0, vy=-120.0, w=16, h=16, kind="star")

    def update(self, dt: float, level: "Level") -> None:
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        _move_entity(self, dt, level, can_drop=True)
        if self.on_ground:
            self.vy = -180


class OneUp(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, vx=60.0, w=16, h=16, kind="1up")

    def update(self, dt: float, level: "Level") -> None:
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        _move_entity(self, dt, level, can_drop=True)


class Fireball(Entity):
    def __init__(self, x: float, y: float, dir: int):
        super().__init__(x, y, vx=180.0 * dir, vy=100.0, w=8, h=8, kind="fireball")
        self.life = 1.5

    def update(self, dt: float, level: "Level") -> None:
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
        old_x = self.x
        self.x += self.vx * dt
        if _solid_at(level, self.x + (self.w if self.vx > 0 else 0), self.y + 4):
            self.alive = False
            return
        self.y += self.vy * dt
        if _solid_at(level, self.x + 4, self.y + self.h):
            self.y = (int((self.y + self.h) / TILE)) * TILE - self.h
            self.vy = -200  # bounce


# =============================================================================
# COLLISION HELPERS
# =============================================================================
def _solid_at(level: "Level", x: float, y: float) -> bool:
    tx = int(x // TILE)
    ty = int(y // TILE)
    if tx < 0 or ty < 0 or ty >= level.height or tx >= level.width:
        return False
    t = level.grid[ty][tx]
    return t in SOLID_TILES


SOLID_TILES = set(["#", "B", "?", "M", "F", "L", "*", "=", "X", "P", "p", "I", "J", "N", "Z", "Q"])
COIN_TILES = set(["c"])
DEADLY_TILES = set(["s", "~"])
ITEM_BLOCKS = {"?": "coin", "M": "mushroom", "F": "fire", "L": "1up", "*": "star"}


def _move_entity(e: Entity, dt: float, level: "Level", can_drop: bool = True) -> None:
    # Horizontal
    new_x = e.x + e.vx * dt
    if e.vx > 0:
        if _solid_at(level, new_x + e.w, e.y + 1) or _solid_at(level, new_x + e.w, e.y + e.h - 1):
            new_x = (int((new_x + e.w) / TILE)) * TILE - e.w - 0.01
            e.vx = -abs(e.vx)
            e.facing = -1
    else:
        if _solid_at(level, new_x, e.y + 1) or _solid_at(level, new_x, e.y + e.h - 1):
            new_x = (int(new_x / TILE) + 1) * TILE + 0.01
            e.vx = abs(e.vx)
            e.facing = 1
    e.x = new_x

    # Vertical
    new_y = e.y + e.vy * dt
    if e.vy > 0:
        if _solid_at(level, e.x + 1, new_y + e.h) or _solid_at(level, e.x + e.w - 1, new_y + e.h):
            new_y = (int((new_y + e.h) / TILE)) * TILE - e.h - 0.01
            e.vy = 0
            e.on_ground = True
        else:
            e.on_ground = False
    else:
        if _solid_at(level, e.x + 1, new_y) or _solid_at(level, e.x + e.w - 1, new_y):
            new_y = (int(new_y / TILE) + 1) * TILE + 0.01
            e.vy = 0
    e.y = new_y

    # Edge-of-platform check (don't fall off for goombas / red koopas)
    if e.on_ground and not can_drop:
        if e.vx < 0 and not _solid_at(level, e.x - 1, e.y + e.h + 1):
            e.vx = abs(e.vx)
            e.facing = 1
        elif e.vx > 0 and not _solid_at(level, e.x + e.w + 1, e.y + e.h + 1):
            e.vx = -abs(e.vx)
            e.facing = -1


# =============================================================================
# PLAYER
# =============================================================================
class Player:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.w = 16
        self.h = 16
        self.facing = 1
        self.on_ground = False
        self.power = 0  # 0=small, 1=super, 2=fire, 3=raccoon
        self.crouching = False
        self.anim = 0.0
        self.state = "idle"  # idle, walk, run, jump, fall, skid, swim, fly, dead
        self.invuln = 0.0
        self.star_timer = 0.0
        self.skid = False
        self.dead = False
        self.dead_timer = 0.0
        self.fire_cooldown = 0.0
        self.p_meter = 0.0  # raccoon
        self.flying = False
        self.fly_timer = 0.0
        self.run_held = False

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def grow(self) -> None:
        if self.power == 0:
            self.power = 1
            self.h = 28
            self.y -= 12
        elif self.power == 1:
            pass  # already super; could upgrade further outside of mushroom

    def get_fire(self) -> None:
        if self.power < 2:
            self.power = 2
            if self.h < 28:
                self.h = 28
                self.y -= 12
        else:
            self.power = 2

    def damage(self) -> bool:
        """Returns True if player died."""
        if self.invuln > 0 or self.star_timer > 0:
            return False
        if self.power > 0:
            self.power = 0
            self.h = 16
            self.y += 12
            self.invuln = 2.0
            return False
        self.dead = True
        self.dead_timer = 2.0
        self.vy = -250
        self.state = "dead"
        return True

    def update(self, dt: float, level: "Level", keys) -> None:
        if self.dead:
            self.dead_timer -= dt
            self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)
            self.y += self.vy * dt
            return

        if self.invuln > 0:
            self.invuln -= dt
        if self.star_timer > 0:
            self.star_timer -= dt
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt

        left = keys[K_LEFT] or keys[K_a]
        right = keys[K_RIGHT] or keys[K_d]
        jump = keys[K_SPACE] or keys[K_w] or keys[K_UP]
        down = keys[K_DOWN] or keys[K_s]
        run = keys[K_LSHIFT] or keys[K_RSHIFT] or keys[K_x] or keys[K_z]
        self.run_held = run

        prev_facing = self.facing

        # Crouch (only super or above)
        self.crouching = down and self.on_ground and self.power > 0

        # Horizontal movement
        max_speed = RUN_SPEED if run else WALK_SPEED
        accel = 400.0
        decel = 600.0
        if left and not right and not self.crouching:
            self.vx = max(self.vx - accel * dt, -max_speed)
            self.facing = -1
        elif right and not left and not self.crouching:
            self.vx = min(self.vx + accel * dt, max_speed)
            self.facing = 1
        else:
            if self.vx > 0:
                self.vx = max(0, self.vx - decel * dt)
            elif self.vx < 0:
                self.vx = min(0, self.vx + decel * dt)

        # P-meter (for raccoon)
        if abs(self.vx) >= RUN_SPEED * 0.95 and self.on_ground:
            self.p_meter = min(1.0, self.p_meter + dt * 0.5)
        else:
            self.p_meter = max(0.0, self.p_meter - dt * 0.3)

        # Jump
        if jump and self.on_ground:
            jv = JUMP_V_RUN if run else JUMP_V
            self.vy = jv - abs(self.vx) * 0.3
            self.on_ground = False
        # variable jump height (gravity reduced while holding jump on ascent)
        if not jump and self.vy < 0:
            self.vy += GRAVITY * dt * 0.8

        # Raccoon flight
        if self.power == 3 and jump and self.p_meter >= 1.0:
            if not self.on_ground:
                if self.fly_timer <= 0 and self.vy > -60:
                    self.vy = -200
                    self.fly_timer = 0.3
                self.flying = True
        if self.fly_timer > 0:
            self.fly_timer -= dt
        if self.on_ground:
            self.flying = False

        # Fire
        if self.power == 2 and run and self.fire_cooldown <= 0:
            self.fire_cooldown = 0.4
            level.entities.append(Fireball(self.x + (self.w if self.facing > 0 else -4),
                                          self.y + 4, self.facing))

        # Gravity
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL)

        # Move and collide (with item-block interactions)
        self._move_x(dt, level)
        self._move_y(dt, level)

        # Skid
        self.skid = (right and self.vx < -20) or (left and self.vx > 20)

        # Coin pickup
        cx1, cy1 = int(self.x // TILE), int(self.y // TILE)
        cx2, cy2 = int((self.x + self.w - 1) // TILE), int((self.y + self.h - 1) // TILE)
        for ty in range(cy1, cy2 + 1):
            for tx in range(cx1, cx2 + 1):
                if 0 <= ty < level.height and 0 <= tx < level.width:
                    t = level.grid[ty][tx]
                    if t == "c":
                        level.grid[ty][tx] = "."
                        level.coins += 1
                        level.score += 200
                        if level.coins >= 100:
                            level.coins -= 100
                            level.lives += 1
                    elif t == "G":
                        level.complete = True
                    elif t == "!":
                        # Axe — kill all enemies on screen, complete fortress
                        level.complete = True
                    elif t in DEADLY_TILES:
                        if t == "s":
                            self.damage()
                        elif t == "~" and level.theme != "water":
                            self.damage()

        # Anim
        self.anim += dt * (1.0 + abs(self.vx) / 60.0)

    def _move_x(self, dt: float, level: "Level") -> None:
        new_x = self.x + self.vx * dt
        if self.vx > 0:
            if _solid_at(level, new_x + self.w, self.y + 2) or _solid_at(level, new_x + self.w, self.y + self.h - 2):
                new_x = (int((new_x + self.w) / TILE)) * TILE - self.w - 0.01
                self.vx = 0
        else:
            if _solid_at(level, new_x, self.y + 2) or _solid_at(level, new_x, self.y + self.h - 2):
                new_x = (int(new_x / TILE) + 1) * TILE + 0.01
                self.vx = 0
        if new_x < 0:
            new_x = 0
        if new_x > level.width * TILE - self.w:
            new_x = level.width * TILE - self.w
        self.x = new_x

    def _move_y(self, dt: float, level: "Level") -> None:
        new_y = self.y + self.vy * dt
        if self.vy > 0:
            if _solid_at(level, self.x + 2, new_y + self.h) or _solid_at(level, self.x + self.w - 2, new_y + self.h):
                new_y = (int((new_y + self.h) / TILE)) * TILE - self.h - 0.01
                self.vy = 0
                self.on_ground = True
            else:
                self.on_ground = False
        else:
            # Hit head — check block types
            for px in (self.x + 2, self.x + self.w - 2):
                ty = int(new_y // TILE)
                tx = int(px // TILE)
                if 0 <= ty < level.height and 0 <= tx < level.width:
                    t = level.grid[ty][tx]
                    if t in SOLID_TILES:
                        # Item block hit
                        if t in ITEM_BLOCKS:
                            item = ITEM_BLOCKS[t]
                            level.grid[ty][tx] = "="  # used
                            self._spawn_item(item, tx, ty, level)
                            new_y = (int(new_y / TILE) + 1) * TILE + 0.01
                            self.vy = 0
                            break
                        elif t == "B" and self.power > 0:
                            # Break brick
                            level.grid[ty][tx] = "."
                            level.score += 50
                            new_y = (int(new_y / TILE) + 1) * TILE + 0.01
                            self.vy = 0
                            break
                        else:
                            new_y = (int(new_y / TILE) + 1) * TILE + 0.01
                            self.vy = 0
                            break
        self.y = new_y

    def _spawn_item(self, item: str, tx: int, ty: int, level: "Level") -> None:
        px = tx * TILE
        py = (ty - 1) * TILE
        if item == "coin":
            level.coins += 1
            level.score += 200
        elif item == "mushroom":
            if self.power == 0:
                level.entities.append(Mushroom(px, py))
            else:
                level.entities.append(FireFlower(px, py))
        elif item == "fire":
            if self.power == 0:
                level.entities.append(Mushroom(px, py))
            else:
                level.entities.append(FireFlower(px, py))
        elif item == "1up":
            level.entities.append(OneUp(px, py))
        elif item == "star":
            level.entities.append(Star(px, py))


# =============================================================================
# LEVEL
# =============================================================================
class Level:
    def __init__(self, data: dict, lives: int = 3, score: int = 0):
        self.name = f"{data['world']}-{data['lvl'].split('-')[1] if '-' in data['lvl'] else data['lvl']}"
        self.full_name = data["lvl"]
        self.world_num = data["world"]
        self.kind = data["kind"]
        self.theme = data["theme"]
        self.grid = [list(r) for r in data["grid"]]
        self.height = len(self.grid)
        self.width = max(len(r) for r in self.grid)
        # pad rows
        for r in self.grid:
            while len(r) < self.width:
                r.append(".")
        self.entities: list[Entity] = []
        self.player = Player(32.0, (self.height - 4) * TILE)
        self.coins = 0
        self.score = score
        self.lives = lives
        self.time = data.get("time", 300)
        self.time_f = float(self.time)
        self.music = data.get("music", "overworld")
        self.complete = False
        self.failed = False
        self.camera_x = 0.0
        self.camera_y = 0.0
        self._parse_entities()
        # Tile lookup: convert spawn markers to plain tiles
        for y in range(self.height):
            for x in range(self.width):
                c = self.grid[y][x]
                if c in ("g", "k", "r", "h", "y", "b", "l", "z", "d", "t", "@", "S"):
                    self.grid[y][x] = "."

    def _parse_entities(self) -> None:
        # Find start
        for y in range(self.height):
            for x in range(self.width):
                c = self.grid[y][x]
                if c == "S":
                    self.player.x = x * TILE
                    self.player.y = y * TILE
        # Spawn enemies
        for y in range(self.height):
            for x in range(self.width):
                c = self.grid[y][x]
                px, py = x * TILE, y * TILE
                if c == "g":
                    self.entities.append(Goomba(px, py))
                elif c == "k":
                    self.entities.append(Koopa(px, py, red=False))
                elif c == "r":
                    self.entities.append(Koopa(px, py, red=True))
                elif c == "h":
                    self.entities.append(HammerBro(px, py))
                elif c == "y":
                    self.entities.append(Piranha(px, py))
                elif c == "b":
                    self.entities.append(Bullet(px, py, -1))
                elif c == "l":
                    self.entities.append(Lakitu(px, py))
                elif c == "d":
                    self.entities.append(DryBones(px, py))
                elif c == "t":
                    self.entities.append(Thwomp(px, py))
                elif c == "@":
                    self.entities.append(Boss(px, py))

    def update(self, dt: float, keys) -> None:
        self.time_f -= dt
        if self.time_f <= 0:
            self.player.dead = True
            self.player.dead_timer = 1.0
        if self.player.dead and self.player.dead_timer <= 0:
            self.failed = True

        self.player.update(dt, self, keys)

        for e in self.entities:
            if e.alive:
                if hasattr(e, "update"):
                    e.update(dt, self)
                # collide with player
                if not self.player.dead and self.player.invuln <= 0:
                    if e.rect().colliderect(self.player.rect()):
                        self._handle_player_enemy(e)

        # Fireball vs enemies
        for fb in [e for e in self.entities if e.kind == "fireball" and e.alive]:
            for en in self.entities:
                if en.kind in ("goomba", "koopa_g", "koopa_r", "hammerbro", "spiny", "drybones", "lakitu") and en.alive and en.state != "dead":
                    if fb.rect().colliderect(en.rect()):
                        en.alive = False
                        fb.alive = False
                        self.score += 100
                        break
                if en.kind == "boss" and en.alive:
                    if fb.rect().colliderect(en.rect()):
                        fb.alive = False
                        if en.hit():
                            self.score += 5000

        # Cull dead
        self.entities = [e for e in self.entities if e.alive]

        # Camera follow
        target_cx = self.player.x - INTERNAL_WIDTH / 2 + 8
        self.camera_x += (target_cx - self.camera_x) * 0.2
        self.camera_x = max(0, min(self.camera_x, self.width * TILE - INTERNAL_WIDTH))
        target_cy = self.player.y - INTERNAL_HEIGHT / 2
        self.camera_y += (target_cy - self.camera_y) * 0.15
        self.camera_y = max(0, min(self.camera_y, max(0, self.height * TILE - INTERNAL_HEIGHT)))

        # Pit death
        if self.player.y > self.height * TILE + 16:
            self.player.dead = True
            self.player.dead_timer = 0.5

    def _handle_player_enemy(self, e: Entity) -> None:
        if e.kind in ("mushroom",):
            e.alive = False
            self.player.grow()
            self.score += 1000
            return
        if e.kind == "fireflower":
            e.alive = False
            self.player.get_fire()
            self.score += 1000
            return
        if e.kind == "1up":
            e.alive = False
            self.lives += 1
            return
        if e.kind == "star":
            e.alive = False
            self.player.star_timer = 8.0
            return
        if e.kind == "fireball":
            return  # handled separately

        # Star mode: kill anything
        if self.player.star_timer > 0:
            e.alive = False
            self.score += 200
            return

        # Stomp logic
        if self.player.vy > 0 and self.player.y + self.player.h - 6 < e.y + 6:
            if hasattr(e, "stomp"):
                e.stomp()
                self.player.vy = -180
                self.score += 100
                return
            if e.kind == "boss":
                if e.hit():
                    self.score += 5000
                self.player.vy = -200
                return
            if e.kind == "thwomp":
                self.player.damage()
                return
            if e.kind == "spiny":
                self.player.damage()
                return

        # Side / bottom collision
        if e.kind == "koopa_g" or e.kind == "koopa_r":
            if e.state == "shell":
                # kick it
                dir = 1 if self.player.x < e.x else -1
                e.kick(dir)
                self.score += 100
                return
            elif e.state == "kicked":
                self.player.damage()
                return
        if e.kind == "spiny" or e.kind == "thwomp" or e.kind == "bullet" or e.kind == "piranha" or e.kind == "boss" or e.kind == "hammerbro" or e.kind == "drybones" or e.kind == "lakitu" or e.kind == "goomba":
            self.player.damage()


# =============================================================================
# RENDERER
# =============================================================================
class Renderer:
    def __init__(self):
        self.atlas = Atlas.get()
        self.fb = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT)).convert()
        self.font_small = pygame.font.SysFont("Courier", 8, bold=True)
        self.font = pygame.font.SysFont("Courier", 14, bold=True)
        self.font_big = pygame.font.SysFont("Courier", 24, bold=True)

    def draw_level(self, level: Level) -> pygame.Surface:
        theme = THEMES.get(level.theme, THEMES["grass"])
        self.fb.fill(theme["sky"])

        cx = int(level.camera_x)
        cy = int(level.camera_y)

        # Background decorations (parallax)
        if level.theme not in ("fortress", "underground", "dark", "night"):
            self._draw_background(level, theme, cx)

        # Tiles
        tx0 = max(0, cx // TILE)
        tx1 = min(level.width, (cx + INTERNAL_WIDTH) // TILE + 1)
        ty0 = max(0, cy // TILE)
        ty1 = min(level.height, (cy + INTERNAL_HEIGHT) // TILE + 1)

        coin_anim = int(pygame.time.get_ticks() / 150) % 3

        for ty in range(ty0, ty1):
            for tx in range(tx0, tx1):
                c = level.grid[ty][tx]
                if c == "." or c in ("S", "g", "k", "r", "h", "b", "l", "z", "d", "t", "@"):
                    continue
                px = tx * TILE - cx
                py = ty * TILE - cy
                self._draw_tile(c, px, py, theme, coin_anim, level.theme)

        # Entities
        for e in level.entities:
            self._draw_entity(e, cx, cy)

        # Player
        self._draw_player(level.player, cx, cy)

        # HUD
        self._draw_hud(level)

        return self.fb

    def _draw_background(self, level: Level, theme: dict, cx: int) -> None:
        # Hills (parallax)
        hill = self.atlas.tile("hill")
        for i, hx in enumerate([20, 200, 380, 560, 740, 920]):
            x = (hx - cx // 3) % (level.width * TILE + 200) - 100
            if -hill.get_width() < x < INTERNAL_WIDTH:
                self.fb.blit(hill, (x, INTERNAL_HEIGHT - 32 - hill.get_height() + 16))
        # Bushes (mid-parallax)
        bush = self.atlas.tile("bush")
        for i, bx in enumerate([50, 130, 240, 320, 450, 600, 780, 900, 1100]):
            x = (bx - cx // 2) % (level.width * TILE + 100) - 50
            if -bush.get_width() < x < INTERNAL_WIDTH:
                self.fb.blit(bush, (x, INTERNAL_HEIGHT - 32 - 8))
        # Clouds
        cloud = self.atlas.tile("cloud")
        for i, cx_off in enumerate([30, 150, 250, 380, 500, 620, 760, 880]):
            x = (cx_off - cx // 4) % (level.width * TILE + 100) - 50
            y = 20 + ((i * 17) % 30)
            if -cloud.get_width() < x < INTERNAL_WIDTH:
                self.fb.blit(cloud, (x, y))

    def _draw_tile(self, c: str, px: int, py: int, theme: dict, coin_anim: int, theme_name: str) -> None:
        # ground variants by theme
        if c == "#":
            if theme_name == "desert":
                self.fb.blit(self.atlas.tile("sand"), (px, py))
            elif theme_name == "ice":
                self.fb.blit(self.atlas.tile("ice"), (px, py))
            elif theme_name in ("fortress", "dark", "night"):
                self.fb.blit(self.atlas.tile("castle"), (px, py))
            else:
                self.fb.blit(self.atlas.tile("ground"), (px, py))
        elif c == "Z":
            self.fb.blit(self.atlas.tile("castle"), (px, py))
        elif c == "B":
            self.fb.blit(self.atlas.tile("brick"), (px, py))
        elif c in ("?", "M", "F", "L", "*"):
            self.fb.blit(self.atlas.tile("qblock"), (px, py))
        elif c == "=":
            self.fb.blit(self.atlas.tile("used"), (px, py))
        elif c == "X":
            self.fb.blit(self.atlas.tile("wood"), (px, py))
        elif c == "P":
            self.fb.blit(self.atlas.tile("pipe_tl"), (px, py))
            self.fb.blit(self.atlas.tile("pipe_tr"), (px + TILE, py))
        elif c == "p":
            self.fb.blit(self.atlas.tile("pipe_bl"), (px, py))
            self.fb.blit(self.atlas.tile("pipe_br"), (px + TILE, py))
        elif c == "c":
            sprites = ["coin1", "coin2", "coin3"]
            self.fb.blit(self.atlas.tile(sprites[coin_anim]), (px, py))
        elif c == "I":
            self.fb.blit(self.atlas.tile("ice"), (px, py))
        elif c == "J":
            ground = self.atlas.tile("ground")
            big = pygame.transform.scale(ground, (TILE * 2, TILE * 2))
            self.fb.blit(big, (px, py))
        elif c == "-":
            cloud_plat = pygame.Surface((TILE, 8), pygame.SRCALPHA)
            cloud_plat.fill(PAL["9"])
            pygame.draw.rect(cloud_plat, PAL["W"], (0, 0, TILE, 2))
            self.fb.blit(cloud_plat, (px, py + 4))
        elif c == "~":
            self.fb.blit(self.atlas.tile("water"), (px, py))
        elif c == "s":
            self.fb.blit(self.atlas.tile("spike"), (px, py))
        elif c == "v":
            self.fb.blit(self.atlas.tile("vine"), (px, py))
        elif c == "G":
            self.fb.blit(self.atlas.tile("goal"), (px, py - 16))
        elif c == "!":
            # axe
            ax = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.polygon(ax, PAL["W"], [(2, 4), (14, 4), (14, 12), (2, 12)])
            pygame.draw.line(ax, PAL["X"], (7, 12), (7, 20), 2)
            self.fb.blit(ax, (px, py))
        elif c == "N":
            note = pygame.Surface((16, 16))
            note.fill((252, 200, 252))
            pygame.draw.rect(note, PAL["K"], (0, 0, 16, 16), 1)
            self.fb.blit(note, (px, py))

    def _draw_entity(self, e: Entity, cx: int, cy: int) -> None:
        x = int(e.x - cx)
        y = int(e.y - cy)
        if x < -32 or x > INTERNAL_WIDTH + 16:
            return
        anim = int(e.anim * 6) % 2
        if e.kind == "goomba":
            if e.state == "dead":
                self.fb.blit(self.atlas.enemy("goomba_squish"), (x, y))
            else:
                self.fb.blit(self.atlas.enemy(f"goomba{anim + 1}"), (x, y))
        elif e.kind in ("koopa_g", "koopa_r"):
            color = "g" if e.kind == "koopa_g" else "r"
            if e.state in ("shell", "kicked"):
                self.fb.blit(self.atlas.enemy(f"shell_{color}"), (x, y))
            else:
                self.fb.blit(self.atlas.enemy(f"koopa_{color}{anim + 1}", flip=e.facing > 0), (x, y - 8))
        elif e.kind == "piranha":
            spr = "piranha_open" if int(e.anim * 4) % 2 else "piranha"
            self.fb.blit(self.atlas.enemy(spr), (x, y))
        elif e.kind == "hammerbro":
            self.fb.blit(self.atlas.enemy("hammerbro", flip=e.facing > 0), (x, y - 8))
        elif e.kind == "bullet":
            self.fb.blit(self.atlas.enemy("bullet", flip=e.facing > 0), (x, y))
        elif e.kind == "lakitu":
            self.fb.blit(self.atlas.enemy("lakitu"), (x, y))
        elif e.kind == "spiny":
            self.fb.blit(self.atlas.enemy("spiny"), (x, y))
        elif e.kind == "drybones":
            self.fb.blit(self.atlas.enemy("drybones", flip=e.facing > 0), (x, y - 8))
        elif e.kind == "thwomp":
            self.fb.blit(self.atlas.enemy("thwomp"), (x, y))
        elif e.kind == "boss":
            self.fb.blit(self.atlas.enemy("boss", flip=e.facing > 0), (x, y - 8))
        elif e.kind == "mushroom":
            m = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(m, PAL["R"], (0, 0, 16, 10))
            pygame.draw.ellipse(m, PAL["K"], (0, 0, 16, 10), 1)
            pygame.draw.circle(m, PAL["W"], (4, 4), 2)
            pygame.draw.circle(m, PAL["W"], (12, 4), 2)
            pygame.draw.rect(m, PAL["S"], (6, 9, 4, 7))
            self.fb.blit(m, (x, y))
        elif e.kind == "fireflower":
            f = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(f, PAL["F"], (8, 6), 5)
            pygame.draw.circle(f, PAL["Y"], (8, 6), 3)
            pygame.draw.line(f, PAL["G"], (8, 10), (8, 16), 2)
            self.fb.blit(f, (x, y))
        elif e.kind == "1up":
            m = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.ellipse(m, PAL["G"], (0, 0, 16, 10))
            pygame.draw.ellipse(m, PAL["K"], (0, 0, 16, 10), 1)
            t = self.font_small.render("1UP", True, PAL["W"])
            m.blit(t, (1, 3))
            self.fb.blit(m, (x, y))
        elif e.kind == "star":
            color = (PAL["Y"], PAL["F"], PAL["W"])[int(pygame.time.get_ticks() / 100) % 3]
            pygame.draw.polygon(self.fb, color, [
                (x + 8, y), (x + 10, y + 6), (x + 16, y + 6),
                (x + 11, y + 10), (x + 13, y + 16),
                (x + 8, y + 12), (x + 3, y + 16),
                (x + 5, y + 10), (x, y + 6), (x + 6, y + 6),
            ])
        elif e.kind == "fireball":
            color = (PAL["F"], PAL["O"])[int(pygame.time.get_ticks() / 60) % 2]
            pygame.draw.circle(self.fb, color, (x + 4, y + 4), 4)
            pygame.draw.circle(self.fb, PAL["Y"], (x + 4, y + 4), 2)

    def _draw_player(self, p: Player, cx: int, cy: int) -> None:
        # Flicker if invuln
        if p.invuln > 0 and int(pygame.time.get_ticks() / 80) % 2:
            return
        # State name
        if p.dead:
            name = "die" if p.power == 0 else "fall"
        elif not p.on_ground:
            if p.flying and p.power == 3:
                name = "fly"
            elif p.vy < 0:
                name = "jump"
            else:
                name = "fall"
        elif p.crouching:
            name = "crouch"
        elif p.skid:
            name = "skid"
        elif abs(p.vx) > 5:
            frame = int(p.anim * 8) % 3
            name = ["w1", "w2", "w3"][frame]
        else:
            name = "idle"

        spr = self.atlas.mario_sprite(p.power, name, flip=p.facing < 0)
        # Star mode tint
        if p.star_timer > 0:
            tinted = spr.copy()
            tint_color = [(252, 252, 252), (252, 56, 56), (252, 252, 0), (56, 252, 56)][int(pygame.time.get_ticks() / 70) % 4]
            tinted.fill(tint_color + (100,), special_flags=pygame.BLEND_RGBA_ADD)
            spr = tinted

        # Anchor bottom
        x = int(p.x - cx)
        y = int(p.y + p.h - spr.get_height() - cy)
        self.fb.blit(spr, (x, y))

    def _draw_hud(self, level: Level) -> None:
        # Top black bar
        pygame.draw.rect(self.fb, PAL["K"], (0, 0, INTERNAL_WIDTH, 16))
        score = self.font.render(f"MARIO {level.score:06d}", True, PAL["W"])
        coins = self.font.render(f"x{level.coins:02d}", True, PAL["Y"])
        world = self.font.render(f"WORLD {level.full_name}", True, PAL["W"])
        time = self.font.render(f"TIME {int(max(0, level.time_f)):03d}", True, PAL["W"])
        self.fb.blit(score, (2, 1))
        # coin icon
        pygame.draw.ellipse(self.fb, PAL["Y"], (90, 3, 8, 10))
        self.fb.blit(coins, (100, 1))
        self.fb.blit(world, (130, 1))
        self.fb.blit(time, (200, 1))
        # P-meter
        if level.player.power == 3:
            pygame.draw.rect(self.fb, PAL["W"], (50, 220, 100, 8), 1)
            pygame.draw.rect(self.fb, PAL["F"], (51, 221, int(98 * level.player.p_meter), 6))

    def draw_world_map(self, world_num: int, cursor_lvl: int, levels: list[dict]) -> pygame.Surface:
        theme = THEMES.get(get_world_theme(world_num), THEMES["grass"])
        self.fb.fill(theme["sky"])
        # Title
        title = self.font_big.render(f"WORLD {world_num}", True, PAL["W"])
        title_outline = self.font_big.render(f"WORLD {world_num}", True, PAL["K"])
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            self.fb.blit(title_outline, (8 + dx, 8 + dy))
        self.fb.blit(title, (8, 8))

        # World levels list
        world_levels = [l for l in levels if l["world"] == world_num]
        # Draw nodes in a path
        n = len(world_levels)
        for i, lv in enumerate(world_levels):
            col = i % 5
            row = i // 5
            nx = 30 + col * 44
            ny = 60 + row * 36
            # path line to next
            if i < n - 1:
                next_col = (i + 1) % 5
                next_row = (i + 1) // 5
                nxn = 30 + next_col * 44
                nyn = 60 + next_row * 36
                pygame.draw.line(self.fb, PAL["W"], (nx + 8, ny + 8), (nxn + 8, nyn + 8), 2)
            # node icon
            node_color = PAL["G"] if lv["kind"] == "normal" else (PAL["Z"] if lv["kind"] == "fortress" else PAL["X"])
            pygame.draw.rect(self.fb, node_color, (nx, ny, 16, 16))
            pygame.draw.rect(self.fb, PAL["K"], (nx, ny, 16, 16), 1)
            # cursor
            if i == cursor_lvl:
                pygame.draw.rect(self.fb, PAL["F"], (nx - 2, ny - 2, 20, 20), 2)
                # mario icon
                m = self.atlas.mario_sprite(0, "idle")
                self.fb.blit(m, (nx, ny - 12))
            # label
            lbl = self.font_small.render(lv["lvl"].split("-", 1)[-1][:3], True, PAL["W"])
            self.fb.blit(lbl, (nx + 1, ny + 18))

        # Footer
        if cursor_lvl < len(world_levels):
            sel = world_levels[cursor_lvl]
            sub = self.font.render(f"{sel['lvl']} ({sel['kind']})", True, PAL["W"])
            self.fb.blit(sub, (8, 210))
            sub2 = self.font_small.render("ENTER = start | LEFT/RIGHT = pick | M/ESC = back", True, PAL["W"])
            self.fb.blit(sub2, (8, 228))
        return self.fb


def get_world_theme(world_num: int) -> str:
    return {1: "grass", 2: "desert", 3: "water", 4: "giant",
            5: "sky", 6: "ice", 7: "pipe", 8: "dark"}.get(world_num, "grass")




# ============================================================================
# GAME STATE MACHINE
# ============================================================================

ST_TITLE = "title"
ST_MAP = "map"
ST_LEVEL = "level"
ST_GAMEOVER = "gameover"
ST_VICTORY = "victory"
ST_TRANS = "trans"  # level -> map transition


class Game:
    """Top-level state machine: title -> map -> level -> ... -> victory."""

    def __init__(self):
        self.state = ST_TITLE
        self.renderer = Renderer()
        self.atlas = Atlas.get()

        # World map state
        self.current_world = 1  # 1-8
        self.cursor_lvl = 0     # index into current world's levels
        self.world_unlocked = 1 # highest unlocked world
        self.lvl_unlocked_in_world = {w: 0 for w in range(1, 9)}  # cursor unlocked per world

        # Persistent stats
        self.lives = 4
        self.coins = 0
        self.score = 0
        self.world_complete = {w: False for w in range(1, 9)}

        # Level instance
        self.level: Level | None = None
        self.level_meta: dict | None = None

        # Transition timer
        self.trans_timer = 0.0
        self.trans_kind = ""   # "win" / "die" / "gameover"
        self.trans_message = ""

        # Title timer (for blink)
        self.title_timer = 0.0

        # Input edge detection
        self._keys_prev: dict[int, bool] = {}

    # ---- Input helpers ----
    def _key_pressed(self, keys, k: int) -> bool:
        now = bool(keys[k])
        was = self._keys_prev.get(k, False)
        self._keys_prev[k] = now
        return now and not was

    def _commit_key_state(self, keys):
        # Track edges for any keys we might watch
        for k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_LEFT, pygame.K_RIGHT,
                  pygame.K_UP, pygame.K_DOWN, pygame.K_a, pygame.K_d, pygame.K_w,
                  pygame.K_s, pygame.K_ESCAPE, pygame.K_m, pygame.K_v, pygame.K_f,
                  pygame.K_x, pygame.K_LSHIFT):
            self._keys_prev[k] = bool(keys[k])

    # ---- Level helpers ----
    def get_world_levels(self, world_num: int) -> list[dict]:
        return [lv for lv in LEVELS if lv["world"] == world_num]

    def start_level(self, meta: dict):
        self.level = Level(meta)
        self.level_meta = meta
        self.state = ST_LEVEL

    def finish_level(self, won: bool):
        """Called when a level ends — either completed or player died."""
        if won:
            self.score += 1000
            # Unlock next level in world
            world_lvls = self.get_world_levels(self.current_world)
            cur = self.cursor_lvl
            if cur + 1 < len(world_lvls):
                self.lvl_unlocked_in_world[self.current_world] = max(
                    self.lvl_unlocked_in_world[self.current_world], cur + 1)
                self.cursor_lvl = cur + 1
            else:
                # World cleared
                self.world_complete[self.current_world] = True
                if self.current_world < 8:
                    self.world_unlocked = max(self.world_unlocked, self.current_world + 1)
                    self.current_world += 1
                    self.cursor_lvl = 0
                else:
                    # Game complete!
                    self.state = ST_VICTORY
                    self.trans_timer = 0.0
                    return
            self.trans_kind = "win"
            self.trans_message = "COURSE CLEAR!"
        else:
            self.lives -= 1
            self.trans_kind = "die"
            self.trans_message = "OH NO!"
            if self.lives <= 0:
                self.state = ST_GAMEOVER
                self.trans_timer = 0.0
                return

        self.state = ST_TRANS
        self.trans_timer = 0.0
        # Reset level state for next try (will be re-created if same level)
        self.level = None

    def reset_full(self):
        """Reset on game over -> back to title."""
        self.lives = 4
        self.coins = 0
        self.score = 0
        self.current_world = 1
        self.cursor_lvl = 0
        self.world_unlocked = 1
        self.lvl_unlocked_in_world = {w: 0 for w in range(1, 9)}
        self.world_complete = {w: False for w in range(1, 9)}
        self.level = None
        self.state = ST_TITLE
        self.title_timer = 0.0

    # ---- Update ----
    def update(self, dt: float, keys):
        if self.state == ST_TITLE:
            self.title_timer += dt
            if self._key_pressed(keys, pygame.K_RETURN) or self._key_pressed(keys, pygame.K_SPACE):
                self.state = ST_MAP
                self.cursor_lvl = 0
                self._commit_key_state(keys)
                return

        elif self.state == ST_MAP:
            world_lvls = self.get_world_levels(self.current_world)
            n = len(world_lvls)
            if n > 0:
                max_unlocked = self.lvl_unlocked_in_world.get(self.current_world, 0)
                if self._key_pressed(keys, pygame.K_LEFT) or self._key_pressed(keys, pygame.K_a):
                    self.cursor_lvl = max(0, self.cursor_lvl - 1)
                if self._key_pressed(keys, pygame.K_RIGHT) or self._key_pressed(keys, pygame.K_d):
                    self.cursor_lvl = min(n - 1, min(max_unlocked, self.cursor_lvl + 1))
                # UP/DOWN: switch worlds (within unlocked range)
                if self._key_pressed(keys, pygame.K_UP) or self._key_pressed(keys, pygame.K_w):
                    if self.current_world > 1:
                        self.current_world -= 1
                        self.cursor_lvl = 0
                if self._key_pressed(keys, pygame.K_DOWN) or self._key_pressed(keys, pygame.K_s):
                    if self.current_world < self.world_unlocked:
                        self.current_world += 1
                        self.cursor_lvl = 0
                if self._key_pressed(keys, pygame.K_RETURN) or self._key_pressed(keys, pygame.K_SPACE):
                    if self.cursor_lvl < n:
                        self.start_level(world_lvls[self.cursor_lvl])

        elif self.state == ST_LEVEL:
            if self.level is None:
                self.state = ST_MAP
                self._commit_key_state(keys)
                return
            # Quick return to map
            if self._key_pressed(keys, pygame.K_m):
                self.level = None
                self.state = ST_MAP
                self._commit_key_state(keys)
                return
            self.level.update(dt, keys)
            # Sync coins/score
            if self.level.player.dead:
                self.finish_level(False)
            elif self.level.complete:
                # Add level coins to total
                self.coins += self.level.player.coins
                self.score += self.level.player.coins * 200
                self.finish_level(True)

        elif self.state == ST_TRANS:
            self.trans_timer += dt
            if self.trans_timer > 1.6:
                self.state = ST_MAP

        elif self.state == ST_GAMEOVER:
            self.trans_timer += dt
            if self.trans_timer > 3.0 or self._key_pressed(keys, pygame.K_RETURN):
                self.reset_full()

        elif self.state == ST_VICTORY:
            self.trans_timer += dt
            if self._key_pressed(keys, pygame.K_RETURN):
                self.reset_full()

        self._commit_key_state(keys)

    # ---- Draw ----
    def draw(self) -> pygame.Surface:
        if self.state == ST_TITLE:
            return self._draw_title()
        elif self.state == ST_MAP:
            world_lvls = self.get_world_levels(self.current_world)
            return self.renderer.draw_world_map(self.current_world, self.cursor_lvl, world_lvls)
        elif self.state == ST_LEVEL:
            if self.level is not None:
                fb = self.renderer.draw_level(self.level)
                # Overlay lives counter
                lf = self.renderer.font_small.render(f"x{self.lives}", True, PAL["W"])
                fb.blit(lf, (220, 2))
                return fb
            return self._blank()
        elif self.state == ST_TRANS:
            return self._draw_trans()
        elif self.state == ST_GAMEOVER:
            return self._draw_gameover()
        elif self.state == ST_VICTORY:
            return self._draw_victory()
        return self._blank()

    def _blank(self) -> pygame.Surface:
        s = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        s.fill(PAL["K"])
        return s

    def _draw_title(self) -> pygame.Surface:
        fb = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        # Sky gradient
        for y in range(INTERNAL_HEIGHT):
            t = y / INTERNAL_HEIGHT
            r = int(92 * (1 - t * 0.3))
            g = int(148 * (1 - t * 0.2))
            b = int(252 * (1 - t * 0.1))
            pygame.draw.line(fb, (r, g, b), (0, y), (INTERNAL_WIDTH, y))

        # Big title text (18pt to fit 256px width without clipping on left edge)
        title = "SUPER MARIO BROS. 3"
        title_f = pygame.font.SysFont("Courier", 18, bold=True)
        ts = title_f.render(title, True, PAL["R"])
        # Shadow
        sh = title_f.render(title, True, PAL["K"])
        fb.blit(sh, ((INTERNAL_WIDTH - ts.get_width()) // 2 + 2, 50 + 2))
        fb.blit(ts, ((INTERNAL_WIDTH - ts.get_width()) // 2, 50))

        # Subtitle
        sub = self.renderer.font.render("AC's id Software Mac Port", True, PAL["W"])
        fb.blit(sub, ((INTERNAL_WIDTH - sub.get_width()) // 2, 84))
        sub2 = self.renderer.font_small.render("- FILES = OFF -", True, PAL["Y"])
        fb.blit(sub2, ((INTERNAL_WIDTH - sub2.get_width()) // 2, 98))

        # Mario figure (big, centered)
        m = self.atlas.mario_sprite(1, "idle")
        m_scaled = pygame.transform.scale(m, (m.get_width() * 2, m.get_height() * 2))
        fb.blit(m_scaled, ((INTERNAL_WIDTH - m_scaled.get_width()) // 2, 120))

        # Press start (blink)
        if int(self.title_timer * 2) % 2 == 0:
            ps = self.renderer.font.render("PRESS ENTER TO START", True, PAL["W"])
            fb.blit(ps, ((INTERNAL_WIDTH - ps.get_width()) // 2, 195))

        cr = self.renderer.font_small.render("8 WORLDS - 90+ LEVELS - 60 FPS", True, PAL["W"])
        fb.blit(cr, ((INTERNAL_WIDTH - cr.get_width()) // 2, 220))

        return fb

    def _draw_trans(self) -> pygame.Surface:
        fb = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        fb.fill(PAL["K"])
        msg = self.renderer.font_big.render(self.trans_message, True, PAL["W"])
        fb.blit(msg, ((INTERNAL_WIDTH - msg.get_width()) // 2, 90))
        # World/level label
        if self.level_meta is not None:
            sub = self.renderer.font.render(self.level_meta["lvl"], True, PAL["Y"])
            fb.blit(sub, ((INTERNAL_WIDTH - sub.get_width()) // 2, 116))
        # Lives
        lives_txt = self.renderer.font.render(f"MARIO x {self.lives}", True, PAL["W"])
        fb.blit(lives_txt, ((INTERNAL_WIDTH - lives_txt.get_width()) // 2, 140))
        return fb

    def _draw_gameover(self) -> pygame.Surface:
        fb = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        fb.fill(PAL["K"])
        msg = self.renderer.font_big.render("GAME OVER", True, PAL["R"])
        fb.blit(msg, ((INTERNAL_WIDTH - msg.get_width()) // 2, 96))
        sc = self.renderer.font.render(f"SCORE  {self.score}", True, PAL["W"])
        fb.blit(sc, ((INTERNAL_WIDTH - sc.get_width()) // 2, 130))
        if int(self.trans_timer * 2) % 2 == 0:
            ps = self.renderer.font_small.render("PRESS ENTER", True, PAL["W"])
            fb.blit(ps, ((INTERNAL_WIDTH - ps.get_width()) // 2, 180))
        return fb

    def _draw_victory(self) -> pygame.Surface:
        fb = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        # Celebratory background
        for y in range(INTERNAL_HEIGHT):
            t = y / INTERNAL_HEIGHT
            fb.fill((int(252 * (1 - t * 0.2)),
                     int(204 * (1 - t * 0.3)),
                     int(56 * (1 - t * 0.5))), (0, y, INTERNAL_WIDTH, 1))
        msg = self.renderer.font_big.render("YOU SAVED", True, PAL["W"])
        msg2 = self.renderer.font_big.render("THE PRINCESS!", True, PAL["W"])
        fb.blit(msg, ((INTERNAL_WIDTH - msg.get_width()) // 2, 60))
        fb.blit(msg2, ((INTERNAL_WIDTH - msg2.get_width()) // 2, 80))

        # Big Mario celebration
        m = self.atlas.mario_sprite(2, "jump")
        m_scaled = pygame.transform.scale(m, (m.get_width() * 3, m.get_height() * 3))
        fb.blit(m_scaled, ((INTERNAL_WIDTH - m_scaled.get_width()) // 2, 110))

        sc = self.renderer.font.render(f"FINAL SCORE  {self.score}", True, PAL["W"])
        fb.blit(sc, ((INTERNAL_WIDTH - sc.get_width()) // 2, 200))
        cr = self.renderer.font_small.render("MEOW - THANKS FOR PLAYING", True, PAL["R"])
        fb.blit(cr, ((INTERNAL_WIDTH - cr.get_width()) // 2, 220))
        return fb


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    pygame.init()
    pygame.display.set_caption("AC's id Software SMB3 — FULL (FILES=OFF)")
    flags = pygame.SCALED | pygame.DOUBLEBUF
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    clock = pygame.time.Clock()

    game = Game()
    fullscreen = False
    limit_fps = True
    running = True
    show_debug = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.state == ST_LEVEL:
                        # Return to map mid-level
                        game.level = None
                        game.state = ST_MAP
                    elif game.state == ST_MAP:
                        # Return to title
                        game.state = ST_TITLE
                    elif game.state in (ST_GAMEOVER, ST_VICTORY):
                        game.reset_full()
                    else:
                        running = False
                elif event.key == pygame.K_v:
                    limit_fps = not limit_fps
                elif event.key == pygame.K_F11 or (event.key == pygame.K_f and (pygame.key.get_mods() & pygame.KMOD_ALT)):
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
                    else:
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
                elif event.key == pygame.K_F3:
                    show_debug = not show_debug

        # dt clamped
        dt = min(clock.tick(TARGET_FPS if limit_fps else 0) / 1000.0, 0.05)

        keys = pygame.key.get_pressed()

        try:
            game.update(dt, keys)
            fb = game.draw()
        except Exception as e:
            # Safe fallback — show error on screen rather than crash
            fb = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
            fb.fill((0, 0, 0))
            f = pygame.font.SysFont("Courier", 10, bold=True)
            err_lines = [
                "RUNTIME ERROR:",
                str(type(e).__name__),
                str(e)[:40],
                str(e)[40:80] if len(str(e)) > 40 else "",
                "",
                "PRESS ESC -> MAP",
            ]
            for i, line in enumerate(err_lines):
                surf = f.render(line, True, (255, 64, 64))
                fb.blit(surf, (8, 20 + i * 14))
            # Recover by booting back to map
            if game.state == ST_LEVEL:
                game.level = None
                game.state = ST_MAP

        # Optional FPS overlay
        if show_debug:
            f = pygame.font.SysFont("Courier", 10, bold=True)
            fps_s = f.render(f"FPS {int(clock.get_fps())}", True, PAL["Y"])
            fb.blit(fps_s, (INTERNAL_WIDTH - 50, INTERNAL_HEIGHT - 14))

        # Scale to window
        if fb.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
            scaled = pygame.transform.scale(fb, (SCREEN_WIDTH, SCREEN_HEIGHT))
        else:
            scaled = fb
        screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
