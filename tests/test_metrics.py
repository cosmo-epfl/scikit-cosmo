import unittest

import numpy as np
from scipy.stats import ortho_group
from sklearn.datasets import load_iris

from skcosmo.metrics import (
    global_reconstruction_error,
    global_reconstruction_distortion,
    local_reconstruction_error,
)


class ReconstructionMeasuresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        features = load_iris().data
        cls.features_small = features[:20, [0, 1]]
        cls.features_large = features[:20, [0, 1, 0, 1]]
        cls.eps = 1e-5
        cls.n_local_points = 15

        np.random.seed(0x5F3759DF)
        cls.features_rotated_small = cls.features_small.dot(
            ortho_group.rvs(cls.features_small.shape[1])
        )

    def test_global_reconstruction_error_identity(self):
        gfre_val = global_reconstruction_error(self.features_large, self.features_large)
        self.assertTrue(
            abs(gfre_val) < self.eps,
            f"global_reconstruction_error {gfre_val} surpasses threshold for zero {self.eps}",
        )

    def test_global_reconstruction_error_small_to_large(self):
        # tests that the GRE of a small set of features onto a larger set of features returns within a threshold of zero
        gfre_val = global_reconstruction_error(self.features_small, self.features_large)
        self.assertTrue(
            abs(gfre_val) < self.eps,
            f"global_reconstruction_error {gfre_val} surpasses threshold for zero {self.eps}",
        )

    def test_global_reconstruction_error_large_to_small(self):
        # tests that the GRE of a large set of features onto a smaller set of features returns within a threshold of zero
        gfre_val = global_reconstruction_error(self.features_large, self.features_small)
        self.assertTrue(
            abs(gfre_val) < self.eps,
            f"global_reconstruction_error {gfre_val} surpasses threshold for zero {self.eps}",
        )

    def test_global_reconstruction_distortion_identity(self):
        # tests that the GRD of a set of features onto itself returns within a threshold of zero
        gfrd_val = global_reconstruction_distortion(
            self.features_large, self.features_large
        )
        self.assertTrue(
            abs(gfrd_val) < self.eps,
            f"global_reconstruction_error {gfrd_val} surpasses threshold for zero {self.eps}",
        )

    def test_global_reconstruction_distortion_small_to_large(self):
        # tests that the GRD of a small set of features onto a larger set of features returns within a threshold of zero
        # should just run
        global_reconstruction_error(self.features_small, self.features_large)

    def test_global_reconstruction_distortion_large_to_small(self):
        # tests that the GRD of a large set of features onto a smaller set of features returns within a threshold of zero
        # should just run
        global_reconstruction_error(self.features_large, self.features_small)

    def test_global_reconstruction_distortion_small_to_rotated_small(self):
        # tests that the GRD of a small set of features onto a rotation of itself returns within a threshold of zero
        gfrd_val = global_reconstruction_distortion(
            self.features_small, self.features_rotated_small
        )
        self.assertTrue(
            abs(gfrd_val) < self.eps,
            f"global_reconstruction_error {gfrd_val} surpasses threshold for zero {self.eps}",
        )

    def test_local_reconstruction_error_identity(self):
        # tests that the local reconstruction error of a set of features onto itself returns within a threshold of zero

        lfre_val = local_reconstruction_error(
            self.features_large, self.features_large, self.n_local_points
        )
        self.assertTrue(
            abs(lfre_val) < self.eps,
            f"local_reconstruction_error {lfre_val} surpasses threshold for zero {self.eps}",
        )

    def test_local_reconstruction_error_small_to_large(self):
        # tests that the local reconstruction error of a small set of features onto a larger set of features returns within a threshold of zero

        lfre_val = local_reconstruction_error(
            self.features_small, self.features_large, self.n_local_points
        )
        self.assertTrue(
            abs(lfre_val) < self.eps,
            f"local_reconstruction_error {lfre_val} surpasses threshold for zero {self.eps}",
        )

    def test_local_reconstruction_error_large_to_small(self):
        # tests that the local reconstruction error of a larger set of features onto a smaller set of features returns within a threshold of zero

        lfre_val = local_reconstruction_error(
            self.features_large, self.features_small, self.n_local_points
        )
        self.assertTrue(
            abs(lfre_val) < self.eps,
            f"local_reconstruction_error {lfre_val} surpasses threshold for zero {self.eps}",
        )


if __name__ == "__main__":
    unittest.main()
