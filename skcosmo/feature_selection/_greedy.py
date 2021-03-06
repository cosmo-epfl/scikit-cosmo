"""
Sequential feature selection
"""
import numbers
import warnings

import numpy as np

from sklearn.feature_selection._base import SelectorMixin
from sklearn.base import BaseEstimator, MetaEstimatorMixin
from sklearn.utils.validation import check_is_fitted, check_array
from skcosmo.utils import get_progress_bar


class GreedySelector(SelectorMixin, MetaEstimatorMixin, BaseEstimator):
    """Transformer that performs Greedy Feature Selection.

    This Greedy Selector adds (forward selection) features to form a
    feature subset in a greedy fashion. At each stage, the model scores each
    feature (without an estimator) and chooses the feature with the maximum score.

    Parameters
    ----------

    n_features_to_select : int or float, default=None
        The number of features to select. If `None`, half of the features are
        selected. If integer, the parameter is the absolute number of features
        to select. If float between 0 and 1, it is the fraction of features to
        select.

    score_thresh_to_select : float, default=None
        Threshold for the score. If `None` selection will continue until the
        number or fraction given by n_features_to_select is chosen. Otherwise
        will stop when the score falls below the threshold.

    scoring : str, callable, list/tuple or dict, default=None
        A single str (see :ref:`scoring_parameter`) or a callable
        (see :ref:`scoring`) to evaluate the features. It is assumed that the
        next feature to select is that which maximizes the score.

        NOTE that when using custom scorers, each scorer should return a single
        value. Metric functions returning a list/array of values can be wrapped
        into multiple scorers that return one value each.

    full : boolean
        In the case that all non-redundant features are exhausted, choose
        randomly from the remaining features.

    progress_bar: boolean, default=False
                  option to use `tqdm <https://tqdm.github.io/>`_
                  progress bar to monitor selections

    Attributes
    ----------

    n_features_to_select : int
        The number of features that were selected.

    X_selected_ : ndarray (n_samples, n_features_to_select)
                  The features selected

    eligible_ : ndarray of shape (n_features,), dtype=bool
        A mask of features eligible for selection

    n_selected_ : int
        The number of features that have been selected thus far

    report_progress : callable
        A wrapper to report the progress of the selector using a `tqdm` style
        progress bar

    score_threshold : float (optional)
        A score below which to stop selecting points

    selected_idx_ : ndarray of integers
                    indices of the selected features, with respect to the
                    original fitted matrix

    support_ : ndarray of shape (n_features,), dtype=bool
        The mask of selected features.

    """

    def __init__(
        self,
        scoring,
        n_features_to_select=None,
        score_thresh_to_select=None,
        progress_bar=False,
        full=False,
    ):

        self.n_features_to_select = n_features_to_select
        self.n_selected_ = 0
        self.scoring = scoring

        if full and score_thresh_to_select is not None:
            raise ValueError(
                "You cannot specify both `score_thresh_to_select` and `full=True`."
            )

        self.score_threshold = score_thresh_to_select
        self.full = full

        if progress_bar:
            self.report_progress = get_progress_bar()
        else:
            self.report_progress = lambda x: x

    def fit(self, X, y=None, warm_start=False):
        """Learn the features to select.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Training vectors.
        y : array-like of shape (n_samples,)
            Target values.
        warm_start : bool
            Whether the fit should continue after having already
            run, after increasing n_features_to_select.
            Assumes it is called with the same X and y

        Returns
        -------
        self : object
        """
        tags = self._get_tags()

        if y is not None:
            X, y = self._validate_data(
                X,
                y,
                accept_sparse="csc",
                ensure_min_features=2,
                force_all_finite=not tags.get("allow_nan", True),
                multi_output=True,
            )
        else:
            X = check_array(
                X,
                accept_sparse="csc",
                ensure_min_features=2,
                force_all_finite=not tags.get("allow_nan", True),
            )

        n_features = X.shape[1]

        error_msg = (
            "n_features_to_select must be either None, an "
            "integer in [1, n_features - 1] "
            "representing the absolute "
            "number of features, or a float in (0, 1] "
            "representing a percentage of features to "
            f"select. Got {self.n_features_to_select} features and "
            f"an input with {n_features} features."
        )

        if self.n_features_to_select is None:
            n_iterations = n_features // 2
        elif isinstance(self.n_features_to_select, numbers.Integral):
            if not 0 < self.n_features_to_select < n_features:
                raise ValueError(error_msg)
            n_iterations = self.n_features_to_select
        elif isinstance(self.n_features_to_select, numbers.Real):
            if not 0 < self.n_features_to_select <= 1:
                raise ValueError(error_msg)
            n_iterations = int(n_features * self.n_features_to_select)
        else:
            raise ValueError(error_msg)

        if warm_start:
            if self.n_selected_ == 0:
                raise ValueError(
                    "Cannot fit with warm_start=True without having been previously initialized"
                )
            self._continue_greedy_search(X, y, n_iterations)
        else:
            self.n_selected_ = 0
            self._init_greedy_search(X, y, n_iterations)

        n_iterations -= self.n_selected_

        for n in self.report_progress(range(n_iterations)):

            new_feature_idx = self._get_best_new_feature(self.scoring, X, y)
            if new_feature_idx is not None:
                self._update_post_selection(X, y, new_feature_idx)
            else:
                warnings.warn(
                    f"Score threshold of {self.score_threshold} reached."
                    f"Terminating search at {self.n_selected_} / {self.n_features_to_select}."
                )
                self.X_selected_ = self.X_selected_[:, :n]
                self.selected_idx_ = self.selected_idx_[:n]
                self._postprocess(X, y)
                return self

        self._postprocess(X, y)
        return self

    def _init_greedy_search(self, X, y, n_to_select):
        """ Initializes the search. Prepares an array to store the selected features. """

        self.eligible_ = np.ones(X.shape[-1], dtype=bool)
        self.X_selected_ = np.zeros((X.shape[0], n_to_select), float)
        self.selected_idx_ = np.zeros((n_to_select), int)

    def _continue_greedy_search(self, X, y, n_to_select):
        """ Continues the search. Prepares an array to store the selected features. """

        n_pad = n_to_select - self.n_selected_
        self.X_selected_ = np.pad(
            self.X_selected_,
            [(0, 0), (0, n_pad)],
            "constant",
            constant_values=0.0,
        )
        old_idx = self.selected_idx_.copy()
        self.selected_idx_ = np.zeros((n_to_select), int)
        self.selected_idx_[: self.n_selected_] = old_idx

    def _get_best_new_feature(self, scorer, X, y):

        scores = scorer(X, y)
        scores = scores[self.eligible_]

        if self.score_threshold is not None and max(scores) < self.score_threshold:
            return None
        else:
            return np.where(self.eligible_)[0][np.argmax(scores)]

    def _update_post_selection(self, X, y, last_selected):
        """
        Saves the most recently selected feature and increments the feature counter
        """

        self.X_selected_[:, self.n_selected_] = X[:, last_selected]
        self.selected_idx_[self.n_selected_] = last_selected
        self.n_selected_ += 1
        self.eligible_[last_selected] = False

    def _get_support_mask(self):
        check_is_fitted(self, ["support_"])
        return self.support_

    def _postprocess(self, X, y):
        """ Post-process X and / or y when selection is finished """
        self.support_ = ~self.eligible_

    def _more_tags(self):
        return {
            "requires_y": False,
        }
