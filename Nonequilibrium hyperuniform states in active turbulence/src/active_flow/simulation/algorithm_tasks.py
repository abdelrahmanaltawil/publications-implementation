# env imports
import functools
import numpy as np
from typing import Callable
import scipy.fftpack as scipy

# local imports
from helpers.time_stepping import stepping_scheme, controller, energy_calculation, velocity_calculation


def discretize(L: float, N: int) -> tuple[np.ndarray]:
    '''
    Placeholder
    '''
    
    # Spatial Domain
    axis = np.linspace(0, L, num=N, endpoint=False) 
    dx = axis[2] - axis[1]
    x_components, y_components = np.meshgrid(axis, axis)
    x_vectors = np.stack((x_components, y_components), axis=2)

    # Frequency Domain
    k_axis = 2*np.pi*scipy.fftfreq(N, L/N)
    dk = k_axis[2] - k_axis[1]
    k_x, k_y = np.meshgrid(k_axis, k_axis)
    k_vectors = np.stack((k_x, k_y), axis=2)

    return x_vectors, dx, k_vectors, dk


def deAliasing_rule(k_square: np.ndarray, N: int, dk: float) -> np.ndarray:
    '''
    Placeholder
    '''

    deAlias = k_square < (2/3*(N/2)*dk)**2

    return deAlias


def set_initial_conditions(N: int) -> np.ndarray:
    '''
    Placeholder
    '''

    # Initial conditions
    w = np.random.normal(0, 1, size=(N,N))
    initial_w_k = scipy.fft2(w)

    return initial_w_k


def model_problem(k_norm: np.ndarray, K_MIN: int, K_MAX: int, V_0: float, V_RATIO: float) -> None:
    ''' 
    Apply physical parameters related to the model
    '''

    # PVC model v0, v1, v2
    v_eff = np.zeros_like(k_norm)
    v_eff[k_norm < K_MIN] = V_0
    v_eff[(k_norm >= K_MIN) & (k_norm <= K_MAX)] = -V_RATIO*V_0
    v_eff[k_norm > K_MAX] = 10*V_0

    return v_eff


def prepare_stepping_scheme(STEPPING_SCHEME: str, v_eff: np.ndarray, k_vectors: np.ndarray, k_square: np.ndarray, deAlias: np.ndarray, COURANT: float, 
                            dx: float, dk: float, N: int) -> tuple[Callable]:
    '''
    Placeholder
    '''

    # operators
    k_inverse = np.zeros_like(k_square)
    np.place(k_inverse, k_square != 0, k_square[k_square != 0]**-1)
    k_scale_bound = np.linspace(0, np.max(np.sqrt(k_square)), N)


    # stepping scheme functions
    time_step = functools.partial(
        stepping_scheme,
        STEPPING_SCHEME= STEPPING_SCHEME, 
        v_eff= v_eff,
        k_x= k_vectors[:,:,0],
        k_y= k_vectors[:,:,1], 
        k_square= k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2, 
        k_inverse= k_inverse,  
        deAlias= deAlias
        )

    velocity = functools.partial(
        velocity_calculation, 
        k_x= k_vectors[:,:,0],
        k_y= k_vectors[:,:,1],
        k_inverse= k_inverse
        )

    cfl_controller = functools.partial(
        controller, 
        courant = COURANT,
        dx = dx
        )

    energy = functools.partial(
        energy_calculation, 
        k_norm= np.sqrt(k_square),
        dk= dk,
        N= N,
        factor= k_scale_bound[1] - k_scale_bound[0]
        )

    return time_step, velocity, cfl_controller, energy


def solve(w_k: np.ndarray, ITERATIONS: int, tau: float, time_step: Callable, velocity: Callable, cfl_controller: Callable, energy: Callable) -> tuple[list]:
    '''
    Placeholder
    '''

    monitor = []
    snapshots = []
    simulation_time=0
    for iteration in range(ITERATIONS+1):

        w_k = time_step(w_k, tau)
        u, v, u_k, v_k = velocity(w_k)

        max_u = np.max(np.sqrt(u**2 + v**2))
        if iteration > 2500:
            tau = cfl_controller(
                max_u= max_u
            )

        if iteration % 100 == 0:
            E_k_1 = energy(
                U_k= np.abs(u_k)**2 + np.abs(v_k)**2
                )

            monitor.append(
                (   
                    iteration,
                    simulation_time,
                    tau,
                    max_u, 
                    E_k_1
                )
            )
            print(
                "iteration = "+"{0:07d}".format(iteration) +"\t"+ 
                "tau = "+"{:.4f}".format(tau) +"\t"+ 
                "E(k=1) = "+"{:.20s}".format("{:0.20f}".format(E_k_1)) +"\t"+ 
                "U_max = "+"{:.20s}".format("{:0.20f}".format(max_u))
                )
    
        if iteration % 1000 == 0:
            snapshots.append(
                    (
                        iteration,
                        w_k
                    )
                )

        simulation_time+=tau

    return monitor, snapshots
    