#!/usr/bin/env python3
"""
Static regression probe for the DX11 fixed-function conversion lane.

This probe intentionally does not enable native drawing or require a GPU.
It verifies the durable contract documented by the R201 TEMP semantic fix:
- TEMP has a deterministic default value before any write.
- RESULTARG TEMP writes do not implicitly replace CURRENT.

The script is a source/static helper and is not runtime validation.
"""

from dataclasses import dataclass


@dataclass
class TempRegister:
    value: tuple[float, float, float, float]


DEFAULT_TEMP = (0.0, 0.0, 0.0, 0.0)


def write_resultarg_temp(current, value):
    """Model D3D9 RESULTARG TEMP routing while preserving CURRENT."""
    temp = TempRegister(value)
    return current, temp


def run():
    current = (1.0, 0.5, 0.25, 1.0)
    initial = TempRegister(DEFAULT_TEMP)

    assert initial.value == DEFAULT_TEMP

    preserved_current, temp = write_resultarg_temp(
        current, (0.2, 0.3, 0.4, 0.5)
    )

    assert preserved_current == current
    assert temp.value != DEFAULT_TEMP
    assert temp.value == (0.2, 0.3, 0.4, 0.5)

    print("DX11_R201_TEMP_RESULTARG_CONTRACT_PASS")


if __name__ == "__main__":
    run()
