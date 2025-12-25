# env imports
import numpy as np
import scipy.fftpack as scipy

# local imports


def stepping_scheme(w_k: np.ndarray, tau: float, STEPPING_SCHEME: str, v_eff: np.ndarray, k_x:np.ndarray, k_y: np.ndarray, 
                    k_square: np.ndarray, k_inverse: np.ndarray, deAlias: np.ndarray) -> np.ndarray:
    '''
    Placeholder
    '''

    ## callable "for ease of notation"
    mu_IM = lambda a: (1 + tau*a*v_eff*k_square)**-1

    # linear -> A: `v_eff * k^2 * w_k` & non-linear -> C: `u*wx + v*wy` functions
    A = lambda w_k: v_eff*k_square*w_k*deAlias
    C = lambda w_k: scipy.fft2(   np.real(scipy.ifft2(1j*k_y*(w_k*k_inverse)))  * np.real(scipy.ifft2(1j*k_x*w_k))
                                + np.real(scipy.ifft2(-1j*k_x*(w_k*k_inverse))) * np.real(scipy.ifft2(1j*k_y*w_k)) )*deAlias 


    if STEPPING_SCHEME == "Euler Semi-Implicit":
        NN_k = C(w_k)
        w_k = (w_k - tau*NN_k)*mu_IM(1)

    elif STEPPING_SCHEME == "RK3":
        w_k1 = w_k + tau*(-C(w_k) - A(w_k))
        w_k2 = 3/4.*w_k + 1/4.*w_k1 + 1/4*tau*(-C(w_k1) - A(w_k1))
        w_k = 1/3.*w_k + 2/3.*w_k2 + 2/3*tau*(-C(w_k2) - A(w_k2))

    elif STEPPING_SCHEME == "IMEX Runge-Kutta":
        C0 = C(w_k)
        w_k1 = (w_k + tau*(-1/2*C0))*mu_IM(1/2)

        C1 = C(w_k1)
        A1 = A(w_k1)
        w_k2 = (w_k + tau*(-11/18*C0 - 1/18*C1 - 1/6*A1))*mu_IM(1/2)
        
        C2 = C(w_k2)
        A2 = A(w_k2)
        w_k3 = (w_k + tau*(-5/6*C0 + 5/6*C1 - 1/2*C2 + 1/2*A1 - 1/2*A2))*mu_IM(1/2)
        
        C3 = C(w_k3)
        A3 = A(w_k3)
        w_k  = (w_k + tau*(-1/4*C0 - 7/4*C1 - 3/4*C2 + 7/4*C3 - 3/2*A1 + 3/2*A2 - 1/2*A3))*mu_IM(1/2) 

    return w_k*deAlias


def controller(courant: float, dx: float, max_u: np.ndarray) -> float:
    '''
    Placeholder
    '''

    tau = courant*np.min(dx/max_u)
    
    return tau


def energy_calculation(k_norm: np.ndarray, dk: float, N: int, factor: float, U_k: np.ndarray) -> np.ndarray:
    '''
    Placeholder
    '''

    circle = (k_norm >= dk-(dk/2)) & (k_norm < dk+(dk/2))
    E_k_1 = 0.5*np.sum(U_k[circle])/(factor*N**4)

    return E_k_1


def velocity_calculation(w_k: np.ndarray, k_x: np.ndarray, k_y: np.ndarray, k_inverse: np.ndarray) -> tuple[np.ndarray]:
    '''
    Placeholder
    '''
    
    psi_k = w_k*k_inverse
    u_k = 1j*k_y*psi_k
    v_k = -1j*k_x*psi_k

    u = np.real(scipy.ifft2(u_k))
    v = np.real(scipy.ifft2(v_k))

    return u, v, u_k, v_k