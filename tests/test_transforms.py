from __future__ import annotations

import numpy as np
import pytest

from aligner.transforms import (
    apply_integer_translations,
    compute_common_valid_crop_region,
    translate_image_without_wrap,
)


def test_translate_image_without_wrap_fills_new_pixels_with_zero() -> None:
    image = np.arange(12, dtype=np.uint16).reshape(3, 4)

    translated = translate_image_without_wrap(image, dx=2, dy=-1)

    expected = np.array(
        [
            [0, 0, 4, 5],
            [0, 0, 8, 9],
            [0, 0, 0, 0],
        ],
        dtype=np.uint16,
    )
    np.testing.assert_array_equal(translated, expected)


def test_apply_integer_translations_requires_one_position_per_slice() -> None:
    data = np.zeros((2, 3, 4), dtype=np.uint8)

    with pytest.raises(ValueError, match="position count"):
        apply_integer_translations(data, [(0.0, 0.0)])


def test_compute_common_valid_crop_region_rejects_empty_overlap() -> None:
    with pytest.raises(ValueError, match="no common valid crop"):
        compute_common_valid_crop_region([(0.0, 0.0), (4.0, 0.0)], width=4, height=4)
