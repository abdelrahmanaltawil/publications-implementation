# env imports 
import numpy as np

# local imports
import active_flow.simulation.algorithm_tasks as tasks


def test_discretize() -> None:
    '''
    Placeholder
    '''
    
    L = np.pi
    N = 128

    x_vectors, dx, k_vectors, dk = tasks.discretize(
        L= L,
        N= N
    )

    # check dimensionality
    assert x_vectors[:,:,0].shape == x_vectors[:,:,1].shape == (N,N)
    assert k_vectors[:,:,0].shape == k_vectors[:,:,1].shape == (N,N)

    # discretization factors
    assert dx == L/N
    assert dk == (2*np.pi)/L


def test_deAliasing_rule() -> None:
    '''
    Placeholder
    '''

    L = np.pi
    N = 128

    x_vectors, dx, k_vectors, dk = tasks.discretize(
        L= L,
        N= N
    )
    deAlias = tasks.deAliasing_rule(
        k_square= k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2, 
        N= 128,
        dk= 2
    ) 

    # check dimensionality
    assert deAlias.shape == (N,N)

    # check type
    assert deAlias.dtype == np.bool_
    


def test_set_initial_conditions() -> None:
    '''
    Placeholder
    '''

    N = 128
    initial_w_k = tasks.set_initial_conditions(
        N= N
    )
    
    # check dimensionality
    assert initial_w_k.shape == (N, N)

    # check type
    assert initial_w_k.dtype == np.complex128


def test_model_problem() -> None:
    ''' 
    Placeholder
    '''

    assert 1 == 1 


def test_prepare_stepping_scheme() -> None:
    '''
    Placeholder
    '''

    pass