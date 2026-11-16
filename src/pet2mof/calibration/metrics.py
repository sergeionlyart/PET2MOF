"""Protocol V1-V4; experimental uncertainty unknown means conditional comparison."""
import numpy as np


def metrics(observed, predicted, u_obs, *, u_num=0., scale=None, experimental_known=False):
    q, pred, u = np.broadcast_arrays(np.asarray(observed, float), np.asarray(predicted, float), np.asarray(u_obs, float))
    if q.size == 0 or np.any(~np.isfinite([q, pred, u])) or np.any(u <= 0) or u_num < 0:
        raise ValueError('finite nonempty observations/predictions and positive uncertainties required')
    e = pred - q
    U = 1.96 * np.sqrt(u**2 + u_num**2)
    mae, bias = float(np.mean(abs(e))), float(np.mean(e))
    coverage = float(np.mean(abs(e) <= U))
    within = mae <= U.mean() and coverage >= .9 and abs(bias) <= U.mean()/2
    return dict(MAE=mae, RMSE=float(np.sqrt(np.mean(e**2))), Bias=bias,
                NMAE=None if scale is None else mae/scale, mean_U=float(U.mean()),
                fraction_within_U=coverage, within_conditional_tolerances=bool(within),
                status=('pass' if within else 'fail') if experimental_known else 'conditional_comparison',
                errors=e.tolist(), U=U.tolist(),
                relative_errors=[float(abs(v)/abs(o)) if abs(o) > bound else None for o,v,bound in zip(q.flat,e.flat,U.flat)])


def aicc(chi2, k, n_independent):
    """Known-error Gaussian objective, up to a common constant; NOT point-count AICc."""
    if n_independent <= k + 1:
        return None
    return float(chi2 + 2*k + 2*k*(k+1)/(n_independent-k-1))
