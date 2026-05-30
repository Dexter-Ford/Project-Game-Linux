"""Physics facade."""

from __future__ import annotations

from simulation.physics_py import GravitySimulator

PhysicsEngine = None
RUST_ENGINE_AVAILABLE = False

__all__ = ["GravitySimulator", "PhysicsEngine", "RUST_ENGINE_AVAILABLE"]
