# env imports
import yaml
import pathlib
import numpy as np
import neptune.new as neptune

# local imports
import active_flow.hyperuniformity_analysis.preprocessing as preprocessing
import active_flow.hyperuniformity_analysis.algorithm_tasks as task
import active_flow.hyperuniformity_analysis.postprocessing as postprocessing
import active_flow.hyperuniformity_analysis.helpers.register as re


def run(parameters: dict) -> str:
    '''
    Placeholder
    '''
    
    run = neptune.init_run(
            tags=["hyper uniformity analysis"],
        )
    run_id = run["sys/id"].fetch()
    re.init_register()

    reference_run = neptune.init_run(
        with_id=parameters["preprocessing"]["experiment_ID"],
        mode="read-only"
        )

    run["parameters"] = reference_run["parameters"].fetch()
    run["parameters/reference_extremes_experiment"] = parameters["preprocessing"]["experiment_ID"]
    parameters["postprocessing"]["snapshots_locations"] = list(map(int, reference_run["parameters/snapshots_locations"].fetch().replace('[', '').replace(']', '').replace('\n', '').split(",")))

    ## load arrays    
    reference_run["data/arrays"].download(destination=parameters["preprocessing"]["download_path"])
    reference_run.wait()
    preprocessing.unzip_delete_file(
        file_path= pathlib.Path(parameters["preprocessing"]["download_path"]+"/arrays.zip")
        )
    preprocessing.load_arrays(
        read_path= pathlib.Path(parameters["preprocessing"]["download_path"]+"/arrays"),
        snapshots_locations= parameters["postprocessing"]["snapshots_locations"]
        )
        
    reference_run.stop()


    # Algorithm
    for extrema_type in ["all_extrema", "minima", "maxima"]:
        task.structure_factor(
            kx= re.register["operators"]["k_vectors"][:,:,0], 
            ky= re.register["operators"]["k_vectors"][:,:,1],
            extrema_snapshots= re.register["snapshots"][extrema_type],
            )
        task.radial_profile(
            kx= re.register["operators"]["k_vectors"][:,:,0], 
            ky= re.register["operators"]["k_vectors"][:,:,1],
            structure_factor_snapshots= re.register["snapshots_structure_factor"]
            )

        postprocessing.save_arrays(
            operators= re.register["operators"], 
            radial_profile_snapshots= re.register["snapshots_radial_profile"],
            extrema_type= extrema_type,
            save_path= pathlib.Path(parameters["postprocessing"]["save_path"]+"/arrays")
            )
        run["data/arrays/"+extrema_type].upload_files(parameters["postprocessing"]["save_path"]+"/arrays/snapshots/radial_profile/"+extrema_type)
        run.wait()

        dk = abs(re.register["operators"]["k_vectors"][:,:,0][0,2] - re.register["operators"]["k_vectors"][:,:,0][0,1])

        # average_slop, average_y_intercept = task.linear_curve_fitting(
        #     k= np.arange(dk, np.max(re.register["operators"]["k_vectors"][:,:,0][0,:]), dk),
        #     radial_profile_snapshots= re.register["snapshots_radial_profile"],
        #     k_interval= parameters["algorithm"]["k_interval"],
        #     symbol= symbol
        #     )

        # Postprocessing
        figure = postprocessing.plot_structure_factor_snapshots(
            structure_factor= re.register["snapshots_structure_factor"],
            symbol= extrema_type
            )
        run["image/"+extrema_type+" structure_factor snapshots"].upload(figure)

        figure = postprocessing.plot_radial_profile_snapshots(
            k_modes= np.arange(dk, np.max(re.register["operators"]["k_vectors"][:,:,0][0,:]), dk),
            radial_profile_snapshots= re.register["snapshots_radial_profile"],
            symbol= extrema_type,
            )
        run["plot/"+extrema_type+" radial_profile snapshots"].upload(figure)

        # average_slop, average_y_intercept = task.linear_curve_fitting(
        #     k= np.arange(dk, np.max(re.register["operators"]["k_vectors"][:,:,0][0,:]), dk),
        #     radial_profile_snapshots= re.register["snapshots_radial_profile"],
        #     k_interval= parameters["algorithm"]["k_interval"],
        #     symbol= symbol,
        #     normalized= True
        #     )

        figure = postprocessing.plot_normalized_radial_profile_snapshots(
            k_modes= np.arange(dk, np.max(re.register["operators"]["k_vectors"][:,:,0][0,:]), dk),
            radial_profile_snapshots= re.register["snapshots_radial_profile"],
            symbol= extrema_type,
            )
        run["plot/"+extrema_type+" normalized_radial_profile snapshots"].upload(figure)

        figure = postprocessing.plot_power_law_snapshots(
            k_modes= np.arange(dk, np.max(re.register["operators"]["k_vectors"][:,:,0][0,:]), dk),
            radial_profile_snapshots= re.register["snapshots_radial_profile"],
            # extrapolation_line= [average_slop, average_y_intercept],
            symbol= extrema_type,
            )
        run["plot/"+extrema_type+" power_law snapshots"].upload(figure)

    run["data/arrays/averages"].upload_files(parameters["postprocessing"]["save_path"]+"/arrays/snapshots/radial_profile/averages")

    figure = postprocessing.plot_k_max_snapshots(
        k_modes= np.arange(dk, np.max(re.register["operators"]["k_vectors"][:,:,0][0,:]), dk),
        radial_profile_snapshots= re.register["snapshots_radial_profile"],
        symbol= "all_extrema"
        )
    run["plot/all_extrema k_max snapshots"].upload(figure)

    # figure = postprocessing.compare_fitting_intervals(
    #     k= np.arange(1, np.max(re.register["operators"]["k_vectors"][:,:,0][0])),
    #     radial_profile_snapshots= re.register["snapshots_radial_profile"],
    #     intervals= [[0,5], [0,10], [0,15], [0,20], [0,25]],
    #     symbol= "all_extrema"
    #     )
    # run["plot/all_extrema fitting_intervals residuals"].upload(figure)


    run.stop()

    return run_id


if __name__ == "__main__":


    with open(pathlib.Path("./parameters/hyperuniformity_analysis.yml"), "r") as file:
        parameters = yaml.safe_load(file)

    run(
        parameters= parameters
        )
