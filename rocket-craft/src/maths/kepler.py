"""Keplerian orbital mechanics."""

from __future__ import annotations

from typing import Dict, Union

import numpy as np

from .vector import Vec2

OrbitInfo = Dict[str, Union[float, bool]]


def solve_kepler(M: float, e: float, tolerance: float = 1e-6, max_iter: int = 50) -> float:
    """
    Solve Kepler's equation M = E - e*sin(E) for eccentric anomaly E.

    Parameters
    ----------
    M : mean anomaly (radians)
    e : eccentricity (0 <= e < 1)
    """
    M = float(M) % (2.0 * np.pi)
    e = float(e)

    if e < 1e-12:
        return M

    # Initial guess (Danby)
    if e < 0.8:
        E = M
    else:
        E = float(np.pi)

    for _ in range(max_iter):
        f = E - e * float(np.sin(E)) - M
        fp = 1.0 - e * float(np.cos(E))
        dE = -f / fp
        E += dE
        if abs(dE) < tolerance:
            return E

    return E


def orbital_position(
    a: float,
    e: float,
    i: float,
    omega: float,
    Omega: float,
    t: float,
    mu: float,
) -> Vec2:
    """
    Position in orbit at time t (seconds since periapsis).

    For 2D side-view we use i=0 and project to the orbital plane (x, y).
    Angles i, omega, Omega are in radians.
    """
    n = float(np.sqrt(mu / (a**3)))  # mean motion
    M = n * t
    E = solve_kepler(M, e)

    # True anomaly
    sin_E = float(np.sin(E))
    cos_E = float(np.cos(E))
    sqrt_term = float(np.sqrt(max(0.0, 1.0 - e * e)))
    nu = float(np.arctan2(sqrt_term * sin_E, cos_E - e))

    r = a * (1.0 - e * cos_E)

    # Perifocal coordinates
    x_p = r * float(np.cos(nu))
    y_p = r * float(np.sin(nu))

    # Rotate by argument of periapsis (2D simplification)
    cos_w = float(np.cos(omega))
    sin_w = float(np.sin(omega))
    x = x_p * cos_w - y_p * sin_w
    y = x_p * sin_w + y_p * cos_w

    return Vec2(x, y)


def hohmann_transfer(r1: float, r2: float, mu: float) -> tuple[float, float, float]:
    """
    Hohmann transfer between circular orbits at radii r1 and r2.

    Returns (delta_v1, delta_v2, transfer_time) in m/s and seconds.
    """
    r1, r2, mu = float(r1), float(r2), float(mu)
    if r1 <= 0 or r2 <= 0:
        raise ValueError("Orbit radii must be positive")

    r_inner, r_outer = (r1, r2) if r1 < r2 else (r2, r1)

    v1 = float(np.sqrt(mu / r_inner))
    a_transfer = (r_inner + r_outer) / 2.0
    v_peri = float(np.sqrt(mu * (2.0 / r_inner - 1.0 / a_transfer)))
    v_apo = float(np.sqrt(mu * (2.0 / r_outer - 1.0 / a_transfer)))
    v2 = float(np.sqrt(mu / r_outer))

    dv1 = abs(v_peri - v1)
    dv2 = abs(v2 - v_apo)
    transfer_time = float(np.pi * np.sqrt(a_transfer**3 / mu))

    if r1 > r2:
        return dv2, dv1, transfer_time
    return dv1, dv2, transfer_time


def orbital_elements_from_state(
    position: Vec2,
    velocity: Vec2,
    mu: float,
    planet_radius: float = 0.0,
) -> OrbitInfo:
    """Return practical orbit readouts from a 2D state vector."""
    r = position.length()
    v = velocity.length()
    if r < 1.0 or mu <= 0:
        return {"valid": False, "bound": False}

    energy = 0.5 * v * v - mu / r
    h = position.x * velocity.y - position.y * velocity.x
    rv = position.x * velocity.x + position.y * velocity.y

    ex = (v * v - mu / r) * position.x / mu - rv * velocity.x / mu
    ey = (v * v - mu / r) * position.y / mu - rv * velocity.y / mu
    e = float(np.hypot(ex, ey))

    info: OrbitInfo = {
        "valid": True,
        "bound": False,
        "eccentricity": e,
        "specific_energy": float(energy),
        "angular_momentum": float(h),
    }

    if abs(h) > 1e-9 and e > 1e-9:
        periapsis = (h * h / mu) / (1.0 + e)
        info["periapsis"] = float(periapsis)
        info["periapsis_altitude"] = float(periapsis - planet_radius)

    if energy < 0.0 and e < 1.0:
        a = -mu / (2.0 * energy)
        apoapsis = a * (1.0 + e)
        periapsis = a * (1.0 - e)
        period = 2.0 * float(np.pi) * float(np.sqrt(a**3 / mu))
        info.update(
            {
                "bound": True,
                "semi_major_axis": float(a),
                "apoapsis": float(apoapsis),
                "periapsis": float(periapsis),
                "apoapsis_altitude": float(apoapsis - planet_radius),
                "periapsis_altitude": float(periapsis - planet_radius),
                "period": float(period),
            }
        )

    return info


def predict_orbit_points(
    position: Vec2,
    velocity: Vec2,
    mu: float,
    num_points: int = 128,
    period_fraction: float = 1.0,
) -> list[Vec2]:
    """
    Sample points along the current conic orbit from state vectors (2D).
    Returns empty list if trajectory is escape (e >= 1) or degenerate.
    """
    r = position.length()
    v = velocity.length()
    if r < 1.0 or mu <= 0:
        return []

    # Specific orbital energy and angular momentum (2D scalar h)
    energy = 0.5 * v * v - mu / r
    h = position.x * velocity.y - position.y * velocity.x

    if abs(energy) < 1e-6:
        return []  # parabolic — skip for now

    if energy >= 0:
        return []  # hyperbolic escape

    a = -mu / (2.0 * energy)
    e = float(np.sqrt(max(0.0, 1.0 + 2.0 * energy * h * h / (mu * mu))))

    # Argument of periapsis from eccentricity vector direction
    ex = (v * v - mu / r) * position.x / mu - (position.x * velocity.x + position.y * velocity.y) * velocity.x / mu
    ey = (v * v - mu / r) * position.y / mu - (position.x * velocity.x + position.y * velocity.y) * velocity.y / mu
    omega = float(np.arctan2(ey, ex))

    n = float(np.sqrt(mu / (a**3)))
    period = 2.0 * float(np.pi) / n
    dt = period * period_fraction / num_points

    points: list[Vec2] = []
    for k in range(num_points):
        t = k * dt
        p = orbital_position(a, e, 0.0, omega, 0.0, t, mu)
        points.append(p)
    return points
