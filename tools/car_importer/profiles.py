"""Exact source-verified profiles. No guessed slot paths are eligible for installation."""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Profile:
    slug: str
    display_name: str
    source_filename: str
    source_sha256: str
    dimensions: Tuple[float, float, float]
    center: Tuple[float, float, float]
    ground_y: float
    flip_front: bool = True


# Source SHA and bounds verified against the user's original F50 file and .blend.
PROFILES = {
    "f50": Profile(
        slug="f50",
        display_name="Ferrari F50 (verified baseline)",
        source_filename="obj_plcar_f50_pmt.sz",
        source_sha256="10daa1312b6cff0267b38b4c440c6007c68b470a225ca15f0c324876fd80aeab",
        dimensions=(2.0124359131, 1.2793918252, 4.4366760254),
        center=(0.0, 0.4712431133, -0.0185089111),
        ground_y=-0.1684527993,
    )
}


def get_profile(slug: str) -> Profile:
    try:
        return PROFILES[slug.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported/unverified vehicle slot: {slug}") from exc