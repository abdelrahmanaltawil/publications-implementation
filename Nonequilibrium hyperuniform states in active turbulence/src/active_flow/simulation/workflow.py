# env imports
import yaml
import pathlib
import numpy as np
import neptune.new as neptune

# local imports
import algorithm_tasks as task
import postprocessing


def run(parameters: dict) -> str:
    '''
    Placeholder
    '''
    
    discretization = parameters["algorithm"]["discretization"]
    physical = parameters["algorithm"]["physical"]


    run = neptune.init_run(
        source_files=["./src/simulation"],
        tags=["reference simulation"]
        )

    # Preprocessing
    run["parameters"] = parameters["algorithm"]

    # Algorithm
    x_vectors, dx, k_vectors, dk =task.discretize(
        L= discretization["domain_length"],
        N= discretization["collocation_points_per_axis"] 
        )
    run["parameters/spatial_discretization_factor"].log(dx)
    run["parameters/frequency_discretization_factor"].log(dk)

    deAlias = task.deAliasing_rule(
        k_square= k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2,
        N= discretization["collocation_points_per_axis"],
        dk= dk
        )
    initial_w_k = task.set_initial_conditions(
        N= discretization["collocation_points_per_axis"]
        )
    v_eff = task.model_problem(
        k_norm= np.sqrt(k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2),
        K_MIN= physical["k_min"],
        K_MAX= physical["k_max"], 
        V_0= physical["v_0"], 
        V_RATIO= physical["v_ratio"]
        )    
    time_step, velocity, cfl_controller, energy = task.prepare_stepping_scheme(
        STEPPING_SCHEME= discretization["time_stepping_scheme"], 
        v_eff= v_eff, 
        k_vectors= k_vectors,
        k_square= k_vectors[:,:,0]**2 + k_vectors[:,:,1]**2, 
        deAlias= deAlias,
        COURANT= discretization["courant"],
        dx= dx,
        dk= dk,
        N= discretization["collocation_points_per_axis"]
        )
    monitored, snapshots = task.solve(
        w_k= initial_w_k,
        ITERATIONS= discretization["iterations"],
        tau= discretization["tau"],
        time_step= time_step,
        velocity= velocity,
        cfl_controller= cfl_controller,
        energy= energy
        )


    # Postprocessing
    postprocessing.save_arrays(
        operators= [
            (x_vectors, "x_vectors"),
            (k_vectors, "k_vectors")
            ], 
        snapshots= snapshots,
        headers= parameters["postprocessing"]["save_quantities"],
        save_path= pathlib.Path(parameters["postprocessing"]["save_path"])
        )
    run["data/arrays"].upload_files(parameters["postprocessing"]["save_path"]+"/arrays")

    monitor_table = postprocessing.save_monitoring_table(
        monitored_data= monitored,
        headers= ["Iterations"]+parameters["preprocessing"]["monitor"],
        save_path= pathlib.Path(parameters["postprocessing"]["save_path"])
        )
    run["data/tables/monitoring"].upload(parameters["postprocessing"]["save_path"]+"/tables/monitoring.csv")
    
    run.wait()
    postprocessing.remove_data(
        data_path= pathlib.Path(parameters["postprocessing"]["save_path"])
        )

    figure = postprocessing.plot_convergence(
        monitored_data= monitor_table,  
    )
    run["plots/convergence"].upload(figure)
    
    run.stop()


if __name__ == "__main__":


    with open(pathlib.Path("./parameters/simulation.yml"), "r") as file:
        parameters = yaml.safe_load(file)
    

    # simulations_settings = [
    #     (np.pi, 128, 1000000, 1),
    #     (np.pi, 128, 1000000, 2),
    #     (np.pi, 128, 1000000, 5),
    #     (4*np.pi, 512, 1000000, 1),
    #     (4*np.pi, 512, 1000000, 2),
    #     (4*np.pi, 512, 1000000, 5)
    # ]
    
    # for L, N, ITERATIONS, V_RATIO in simulations_settings:
        
    #     parameters["algorithm"]["discretization"]["domain_length"] = L
    #     parameters["algorithm"]["discretization"]["collocation_points_per_axis"] = N
    #     parameters["algorithm"]["discretization"]["iterations"] = ITERATIONS
    #     parameters["algorithm"]["physical"]["v_ratio"] = V_RATIO


    run(
        parameters= parameters
        )