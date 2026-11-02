"""Host-side regression checks for DNG matrix direction and invalid profile rejection."""

import argparse
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np
from prepare import libraw_color_tags

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--gpr-source", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.gpr_source.resolve() / "tools"))
import raw_media as media


class ColorProfileTest(unittest.TestCase):
    def test_xyz_to_camera_direction_and_d65(self):
        matrix = np.array(
            [[1.0, 0.2, 0.3], [0.4, 1.1, 0.6], [0.7, 0.8, 1.4], [0, 0, 0]]
        )
        tags = {
            t["code"]: t
            for t in libraw_color_tags(SimpleNamespace(rgb_xyz_matrix=matrix), media)
        }
        np.testing.assert_allclose(
            media.values(tags[50721]),
            [1, 0.2, 0.3, 0.4, 1.1, 0.6, 0.7, 0.8, 1.4],
            rtol=0,
            atol=1e-10,
        )
        self.assertEqual(media.values(tags[50778]), (21,))
        self.assertEqual(tags[50721]["type"], 10)

    def test_invalid_profile_does_not_create_plausible_calibration(self):
        for matrix in (
            np.zeros((4, 3)),
            np.full((4, 3), np.nan),
            np.eye(3),
            np.ones((4, 3)),
        ):
            with self.subTest(matrix=matrix):
                with self.assertRaises(ValueError):
                    libraw_color_tags(SimpleNamespace(rgb_xyz_matrix=matrix), media)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
