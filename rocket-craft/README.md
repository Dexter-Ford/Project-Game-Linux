# RocketCraft

A 2D rocket simulation game inspired by Kerbal Space Program, with simple RollerCoaster Tycoon–style graphics (pixel-friendly primitives for now). Side-view flight from launch through atmosphere to orbit, using **patched conics** physics (no full N-body engine).

## Tech stack

- Python 3.9+
- [Pygame](https://www.pygame.org/) — rendering and input
- [NumPy](https://numpy.org/) — math utilities
- [Numba](https://numba.pydata.org/) — optional acceleration (not required for the prototype)

## Features (current / planned)

| Status | Feature |
|--------|---------|
| ✅ | Patched-conics gravity, atmosphere drag, SOI hooks |
| ✅ | Build rocket from parts, throttle, rotate, launch |
| ✅ | Kepler orbit preview, Hohmann Δv helpers |
| ✅ | One-time intro cutscene, character creation, town, hangar, Thai dialogue, save/load |
| ✅ | Casual NPC conversations with session memory and milestone reactions |
| ✅ | Scrollable dialogue box, Unicode character names, five-slot load screen |
| ✅ | Larger town layout with separated districts, minimap, and full map overlay |
| ✅ | Player home with decor styles, NPC homes, and a mailbox with unread mail alerts |
| ✅ | Procedural SFX and MIDI zone music with silent fallback |
| ✅ | Story-driven daily events from JSON with Thai NPC dialogue and English UI choices |
| ✅ | Stardew-like time: 6 AM start, 2 AM day rollover, 10 real minutes per in-game day |
| ✅ | NPC morale, reputation, research points, and time-of-day NPC schedules |
| 🔜 | Multi-body SOI transfers, deeper economy, contracts |

## Setup

```bash
cd rocket-craft
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Optional: Rust physics extension

Requires [Rust](https://rustup.rs/) and [maturin](https://www.maturin.rs/):

```bash
pip install -r requirements-dev.txt
maturin develop --release
```

Verify:

```bash
python -c "from simulation.physics import RUST_ENGINE_AVAILABLE; print('rust:', RUST_ENGINE_AVAILABLE)"
```

If the extension is not built, the game uses the pure-Python physics in `simulation/physics_py.py` automatically.

## Run

From the **`rocket-craft`** directory (works the same in **Cursor**, **Codex**, or a normal terminal):

```bash
cd rocket-craft
source .venv/bin/activate   # after Setup
python src/main.py
```

You can also run this from any working directory, which is safest for Cursor/Codex:

```bash
python run_game.py
```

`main.py` and `run_game.py` add `src/` to `sys.path` automatically.

**Audio:** procedural thrust/click SFX plus MIDI for title and town zones (`assets/audio/*.mid`, auto-generated if missing). If the mixer fails to init, the game still runs without sound.

## Controls

| Input | Action |
|-------|--------|
| **Mouse** | Title buttons, town buildings, NPC dialogue, hangar parts |
| **E** | Talk, use mailbox, decorate, or sleep/save at home |
| **Mouse wheel** | Scroll long dialogue text |
| **M** | Toggle the full town map |
| **Enter** | Confirm character / add selected hangar part |
| **Backspace** | Remove last hangar part |
| **L** | Launch from hangar |
| **W/S** | Raise/lower launch throttle |
| **Space** | Toggle launch throttle |
| **A/D** | Pitch during launch |
| **P** | Pause launch |
| **R** | Reset launch |
| **Esc** | Back/close current screen |

## Project layout

```
rocket-craft/
├── engine/           # Rust crate (PyO3), optional acceleration
├── src/
│   ├── simulation/   # physics facade + rocket, planets
│   ├── screens/      # title, character, town, hangar, launch
│   ├── core/         # session, save/load, fonts, state machine
│   ├── maths/        # Vec2, Kepler, transfers (`maths` avoids stdlib `math`)
│   ├── graphics/     # sky, vegetation, buildings, NPC sprites, camera, HUD
│   ├── audio/        # procedural SFX + MIDI music
│   ├── data/         # Thai dialogue and story-event JSON
│   ├── main.py
│   └── config.py
├── assets/           # sprites (placeholder)
├── pyproject.toml    # maturin build config
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Physics notes

- World coordinates are in **meters** from the planet center.
- Gravity: \( F = GMm / r^2 \) toward the active SOI body.
- Drag: \( F = \frac{1}{2} \rho v^2 C_d A \).
- Thrust along rocket angle (0° = radially away from the active planet center).

## License

Prototype / educational use — add your license as needed.
