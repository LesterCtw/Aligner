from __future__ import annotations

import numpy as np

from aligner.image_view import array_to_display_uint8


def test_uint16_image_display_scaling_uses_full_display_range() -> None:
    image = np.array([[100, 200], [300, 400]], dtype=np.uint16)

    display = array_to_display_uint8(image)

    assert display.dtype == np.uint8
    assert display[0, 0] == 0
    assert display[-1, -1] == 255
    assert display.flags.c_contiguous


def test_flat_image_display_scaling_returns_black_image() -> None:
    image = np.full((2, 3), 1000, dtype=np.uint16)

    display = array_to_display_uint8(image)

    np.testing.assert_array_equal(display, np.zeros((2, 3), dtype=np.uint8))
