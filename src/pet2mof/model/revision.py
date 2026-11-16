"""Versioned observation operators; all model states remain per dry composite."""
import numpy as np

VERSIONS = ('v1', 'v1.1-mof', 'v1.1-connectivity')


def observation(q_composite, w, model_version='v1'):
    if model_version not in VERSIONS:
        raise ValueError('unknown model_version')
    if np.any(np.asarray(w) >= 1) or np.any(np.asarray(w) < 0):
        raise ValueError('observation basis requires 0 <= w < 1')
    return q_composite if model_version == 'v1' else q_composite/(1-np.asarray(w))


def connectivity(w, kappa, power):
    """Phenomenological shared pore-mouth connectivity, not measured porosity."""
    r = np.asarray(w)/(1-np.asarray(w))
    return np.exp(-(kappa*r)**power)


def dry_prediction(p, w, hostq, n_N, x, model_version='v1', baseline=False):
    if model_version not in VERSIONS:
        raise ValueError('unknown model_version')
    p, w = np.asarray(p), np.asarray(w)
    if baseline:
        eta, kd = x
        q = (1-w)*hostq + w*n_N*eta*kd*p/(1+kd*p)
    else:
        A0, lam, kd, kappa = x[:4]
        scale = ((1-w)*connectivity(w, kappa, x[4]) if model_version == 'v1.1-connectivity'
                 else 1-w-kappa*w)
        q = scale*hostq + w*n_N*.5*A0*np.exp(-lam*w/(1-w))*kd*p/(1+kd*p)
    return observation(q, w, model_version)
