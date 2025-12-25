# env imports
import numpy as np
import scipy.fftpack as scipy

# local imports


def stepping_scheme(w_k: np.ndarray, tau: float, STEPPING_SCHEME: str, v_eff: np.ndarray, k_x:np.ndarray, k_y: np.ndarray, 
                    k_square: np.ndarray, k_inverse: np.ndarray, deAlias: np.ndarray) -> np.ndarray:
    """
    Advance the vorticity field one time step using specified integration scheme.
    
    Implements several time-stepping schemes for the PVC equations, handling
    both the linear (diffusion) and nonlinear (advection) terms.
    
    Parameters
    ----------
    w_k : np.ndarray
        Vorticity in Fourier space, shape (N, N).
    tau : float
        Time step Δt.
    STEPPING_SCHEME : str
        Integration method: "Euler Semi-Implicit", "RK3", or "IMEX Runge-Kutta".
    v_eff : np.ndarray
        Effective viscosity at each wavenumber.
    k_x : np.ndarray
        x-component of wavenumber grid.
    k_y : np.ndarray
        y-component of wavenumber grid.
    k_square : np.ndarray
        |k|² at each grid point.
    k_inverse : np.ndarray
        1/|k|² for computing stream function (0 at origin).
    deAlias : np.ndarray
        Boolean mask for dealiasing (2/3 rule).
    
    Returns
    -------
    np.ndarray
        Updated vorticity ω̂(k) after one time step.
    
    Notes
    -----
    - A(ω) = ν_eff × k² × ω̂ is the linear diffusion term
    - C(ω) = FFT(u·∂ω/∂x + v·∂ω/∂y) is the nonlinear advection term
    - IMEX schemes treat diffusion implicitly for stability
    """

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
    """
    Compute adaptive time step based on CFL condition.
    
    The Courant-Friedrichs-Lewy (CFL) condition ensures stability
    by limiting how far information can travel in one time step.
    
    Parameters
    ----------
    courant : float
        Target CFL number (typically < 1 for stability).
    dx : float
        Spatial grid spacing.
    max_u : np.ndarray
        Maximum velocity magnitude in the domain.
    
    Returns
    -------
    float
        Computed time step τ = CFL × Δx / U_max.
    """

    tau = courant*np.min(dx/max_u)
    
    return tau


def energy_calculation(k_norm: np.ndarray, dk: float, N: int, factor: float, U_k: np.ndarray) -> np.ndarray:
    """
    Compute the energy at wavenumber k=1.
    
    Calculates E(k=1) by integrating velocity spectrum over an annular
    shell around |k|=1. Used to monitor convergence to steady state.
    
    Parameters
    ----------
    k_norm : np.ndarray
        Wavenumber magnitude |k| at each grid point.
    dk : float
        Wavenumber spacing.
    N : int
        Grid resolution.
    factor : float
        Normalization factor for spectral binning.
    U_k : np.ndarray
        Velocity power spectrum |û|² + |v̂|².
    
    Returns
    -------
    float
        Energy E(k=1) in the first wavenumber shell.
    """

    circle = (k_norm >= dk-(dk/2)) & (k_norm < dk+(dk/2))
    E_k_1 = 0.5*np.sum(U_k[circle])/(factor*N**4)

    return E_k_1


def velocity_calculation(w_k: np.ndarray, k_x: np.ndarray, k_y: np.ndarray, k_inverse: np.ndarray) -> tuple[np.ndarray]:
    """
    Compute velocity field from vorticity via stream function.
    
    Uses the relations: ψ = ω/|k|², u = ∂ψ/∂y, v = -∂ψ/∂x
    in Fourier space: û = ik_y × ψ̂, v̂ = -ik_x × ψ̂
    
    Parameters
    ----------
    w_k : np.ndarray
        Vorticity in Fourier space.
    k_x : np.ndarray
        x-component of wavenumber grid.
    k_y : np.ndarray
        y-component of wavenumber grid.
    k_inverse : np.ndarray
        1/|k|² (0 at origin to avoid division by zero).
    
    Returns
    -------
    u : np.ndarray
        x-velocity in physical space.
    v : np.ndarray
        y-velocity in physical space.
    u_k : np.ndarray
        x-velocity in Fourier space.
    v_k : np.ndarray
        y-velocity in Fourier space.
    """
    
    psi_k = w_k*k_inverse
    u_k = 1j*k_y*psi_k
    v_k = -1j*k_x*psi_k

    u = np.real(scipy.ifft2(u_k))
    v = np.real(scipy.ifft2(v_k))

    return u, v, u_k, v_k