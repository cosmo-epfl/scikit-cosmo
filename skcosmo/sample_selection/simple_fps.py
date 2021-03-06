import numpy as np
import numbers

from sklearn.utils.validation import NotFittedError
from ._greedy import GreedySelector


class FPS(GreedySelector):
    """Transformer that performs Greedy Feature Selection using Farthest Point Sampling.


    Parameters
    ----------

    n_samples_to_select : int or float, default=None
        The number of samples to select. If `None`, half of the samples are
        selected. If integer, the parameter is the absolute number of samples
        to select. If float between 0 and 1, it is the fraction of samples to
        select.

    initialize: int or 'random', default=0
        Index of the first sample to be selected. If 'random', picks a random
        value when fit starts.

    progress_bar: boolean, default=False
                  option to use `tqdm <https://tqdm.github.io/>`_
                  progress bar to monitor selections

    tolerance: float, defaults to 1E-12
                threshold below which distances will be considered 0

    Attributes
    ----------
    haussdorf_ : ndarray of shape (n_samples,)
                 the minimum distance from each sample to the set of selected
                 samples. once a sample is selected, the distance is not updated;
                 the final list will reflect the distances when selected.
    n_samples_to_select : int
        The number of samples that were selected.

    norms_ : ndarray of shape (n_samples,)
        The self-covariances of each of the samples

    X_selected_ : ndarray (n_samples_to_select, n_features)
                  The samples selected

    y_selected_ : ndarray (n_samples_to_select, n_properties)
                  The corresponding target values for the samples selected

    eligible_ : ndarray of shape (n_samples,), dtype=bool
                A mask of samples eligible for selection

    n_selected_ : int
                The number of samples that have been selected thus far

    report_progress : callable
                A wrapper to report the progress of the selector using a `tqdm` style
                progress bar

    score_threshold : float (optional)
                A score below which to stop selecting samples

    selected_idx_ : ndarray of integers
                    indices of the selected samples, with respect to the
                    original fitted matrix

    support_ : ndarray of shape (n_samples,), dtype=bool
        The mask of selected samples.

    """

    def __init__(
        self,
        n_samples_to_select=None,
        initialize=0,
        tolerance=1e-12,
        progress_bar=False,
    ):

        scoring = self.score
        self.initialize = initialize

        super().__init__(
            scoring=scoring,
            n_samples_to_select=n_samples_to_select,
            progress_bar=progress_bar,
            score_thresh_to_select=tolerance,
        )

    def _calculate_distances(self, X, last_selected):
        return self.norms_ + self.norms_[last_selected] - 2 * X[last_selected] @ X.T

    def _set_norms(self, X, y):
        self.norms_ = (X ** 2).sum(axis=1)

    def _init_greedy_search(self, X, y, n_to_select):
        """
        Initializes the search. Prepares an array to store the selected
        samples, selects the initial sample (unless provided), and
        computes the starting haussdorf distances.
        """

        super()._init_greedy_search(X, y, n_to_select)
        self._set_norms(X, y)

        if self.initialize == "random":
            initialize = np.random.randint(X.shape[0])
        elif isinstance(self.initialize, numbers.Integral):
            initialize = self.initialize
        else:
            raise ValueError("Invalid value of the initialize parameter")

        self.selected_idx_[0] = initialize
        self.haussdorf_ = np.full(X.shape[0], np.inf)
        self.haussdorf_at_select_ = np.full(X.shape[0], np.inf)
        self._update_post_selection(X, y, self.selected_idx_[0])

    def score(self, X, y=None):
        """
        Returns the Haussdorf distances of all samples to previous selections

        Parameters
        ----------
        X : ignored
        y : ignored

        Returns
        -------
        haussdorf : Haussdorf distances
        """
        return self.haussdorf_

    def _update_post_selection(self, X, y, last_selected):
        """
        Saves the most recently selected sample, increments the sample counter,
        and, recomputes haussdorf distances.
        """

        self.haussdorf_at_select_[last_selected] = self.haussdorf_[last_selected]
        self.haussdorf_[last_selected] = 0

        # distances of all points to the new point
        new_dist = self._calculate_distances(X, last_selected)

        # update in-place the Haussdorf distance list
        np.minimum(self.haussdorf_, new_dist, self.haussdorf_)

        super()._update_post_selection(X, y, last_selected)

    def get_select_distance(self):
        """ Returns the Haussdorf distances of selecte samples at their time of selection"""
        if hasattr(self, "haussdorf_at_select_"):
            return self.haussdorf_at_select_[self.selected_idx_]
        else:
            raise NotFittedError()
