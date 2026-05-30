# Math module location

Orbital math (`Vec2`, Kepler solvers) lives in the sibling package **`maths/`** (with an “s”).

Python’s standard library already uses the top-level name `math`. A project folder with the same name breaks NumPy and other imports, so this directory is a placeholder that matches the design layout.

Use:

```python
from maths.vector import Vec2
from maths.kepler import solve_kepler, hohmann_transfer
```
