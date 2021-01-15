import numpy as np
from abc import ABCMeta
from sklearn.utils import check_array
from sklearn.utils.validation import check_is_fitted
from sklearn.base import BaseEstimator, TransformerMixin, RegressorMixin
from sklearn.metrics.pairwise import pairwise_kernels
from ..preprocessing.flexible_scaler import KernelFlexibleCenterer
from ..selection.FPS import SampleFPS


class _Sparsified(TransformerMixin, RegressorMixin, BaseEstimator, metaclass=ABCMeta):
    """
    Super-class defined sparcified methods

        :param kernel: the kernel used for this learning
        :param gamma: exponential factor of the rbf and sigmoid kernel
        :param degree: polynomial kernel degree
        :param coef0: free term of the polynomial and sigmoid kernel
        :param kernel_params: kernel parameter set
        :param n_active: the size of the small dataset used in learning
        :param center: if True, centering of kernel during the learning is carried out
        :param n_jobs: The number of jobs to use for the computation the kernel. This works by breaking down the pairwise matrix into n_jobs even slices and computing them in parallel.
        :param selector: defines the sampling method for the active subsets
        :param selector_args: define the parameters for selector function
    """

    def __init__(
        self,
        kernel="linear",
        gamma=None,
        degree=3,
        coef0=1,
        kernel_params=None,
        n_active=None,
        center=True,
        n_jobs=1,
        selector=SampleFPS,
        selector_args={},
    ):
        """
        Initializes superclass for sparse methods

        :param kernel: the kernel used for this learning
        :param gamma: exponential factor of the rbf and sigmoid kernel
        :param degree: polynomial kernel degree
        :param coef0: free term of the polynomial and sigmoid kernel
        :param kernel_params: kernel parameter set
        :param n_active: the size of the active dataset used in learning
        :param center: if True, centering of kernel during the learning is carried out
        :param n_jobs: The number of jobs to use for the computation the kernel. This works by breaking down the pairwise matrix into n_jobs even slices and computing them in parallel.
        :param selector: defines the sampling method for the active subsets
        :param selector_args: define the parameters for selector function
        """
        self.kernel = kernel
        self.gamma = gamma
        self.degree = degree
        self.coef0 = coef0
        self.kernel_params = kernel_params
        self.n_active = n_active
        self.center = center
        self.n_jobs = n_jobs
        self._selector = selector
        self._selector_args = selector_args

    def _get_kernel(self, X, Y=None):
        """
        Calculate kernel for the matrix X or (optionally) for matrix X and Y
        :param X: matrix, for which we calculate kernel
        :param Y: A second feature array only if X has shape [n_samples_a, n_features].

        :return: sklearn.metrics.pairwise.pairwise_kernels(X, Y)
        """
        if self.kernel == "precomputed":
            if X.shape[-1] != self.n_active:
                raise ValueError("The supplied kernel does not match n_active.")
            return X
        if callable(self.kernel):
            params = self.kernel_params or {}
        else:
            params = {"gamma": self.gamma, "degree": self.degree, "coef0": self.coef0}
        return pairwise_kernels(
            X, Y, metric=self.kernel, filter_params=True, n_jobs=self.n_jobs, **params
        )

    def _get_kernel_matrix(self, X, X_sparse=None):
        """
        Calculate the Kmm and Knm matrices, which corresponds to the kernel evaluated between the active set samples
        :param X: input matrices, for which we calculate Kmm and Knm
        :param Kmm: kernel evaluated between the active set samples
        :param Knm: kernel matrix between X and X_sparse
        """
        if X_sparse is None:
            selector = self._selector(X, **self._selector_args)

            i_active = selector.select(self.n_active)

            X_sparse = X[i_active]

            if self.kernel == "precomputed":
                X_sparse = X_sparse[:, i_active]

        self.X_sparse_ = X_sparse
        K_sparse_ = self._get_kernel(self.X_sparse_)

        K_cross_ = self._get_kernel(X, self.X_sparse_)
        if self.center:
            self.kfc = KernelFlexibleCenterer()
            self.kfc.fit(K_sparse_)
            K_sparse_ = self.kfc.transform(K_sparse_)
            K_cross_ = self.kfc.transform(K_cross_)
        return K_sparse_, K_cross_
