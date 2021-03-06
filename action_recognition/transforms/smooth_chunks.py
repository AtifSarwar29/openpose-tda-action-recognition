import scipy.signal
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class SmoothChunks(BaseEstimator, TransformerMixin):
    """Smoothes the path of every keypoint, helps remove some jitter from OpenPose.

    Uses scipy.signal.savgol_filter with a window length of
    frames_per_chunk / 4 (+ 1 if not odd), and a polyorder of 3.

    """

    def fit(self, X, y=None, **fit_params):
        """Returns self unchanged, as there are no parameters to fit.

        Parameters
        ----------
        X : ignored
        y : ignored
        fit_params : ignored

        Returns
        -------
        self : unchanged

        """
        return self

    def transform(self, chunks):
        """Smooths the paths of keypoints.

        Parameters
        ----------
        chunks : array-like, shape = [n_chunks, frames_per_chunk, n_keypoints, 3]

        Returns
        -------
        chunks : array-like, shape = [n_chunks, frames_per_chunk, n_keypoints, 3]

        """
        smooth = np.array([self._smooth_chunk(chunk) for chunk in chunks])
        return smooth

    def _smooth_chunk(self, chunk):
        chunk = np.copy(chunk)
        window_length = int(chunk.shape[0] / 4)
        # Window length has to be odd!
        if window_length % 2 == 0:
            window_length += 1

        # Polyorder has to be less than window_length
        if window_length < 5:
            window_length = 5

        for i in range(chunk.shape[1]):
            for j in range(2):
                chunk[:, i, j] = scipy.signal.savgol_filter(chunk[:, i, j], window_length, 3)
        return chunk
