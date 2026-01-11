# env imports
import yaml
import pathlib
import sys

# Ensure project level imports
sys.path.append(str(pathlib.Path(__file__).parent.parent))
import numpy as np
import neptune.new as neptune

# local imports
import hyperuniformity_analysis.preprocessing as preprocessing
import hyperuniformity_analysis.algorithm_tasks as task
import hyperuniformity_analysis.postprocessing as postprocessing
import hyperuniformity_analysis.helpers.register as re


def run(parameters: dict) -> str:
    """
    Run the hyperuniformity analysis workflow.
    
    Computes the structure factor S(k) for vortex center distributions
    to determine if the pattern is hyperuniform. This is the final and
    most important analysis step in the pipeline.
    
    Pipeline:
    1. Download extrema positions from Neptune.ai reference run
    2. Compute structure factor S(kx, ky) for each extrema type
    3. Calculate radially-averaged profile S(|k|)
    4. Generate plots (S(k) heatmaps, radial profiles, power-law fits)
    5. Upload all results to Neptune
    
    Parameters
    ----------
    parameters : dict
        Configuration dictionary from hyperuniformity_analysis.yml containing:
        - preprocessing.experiment_ID: Neptune run ID from extrema search
        - preprocessing.download_path: Local temp directory
        - postprocessing.save_path: Output directory
    
    Returns
    -------
    str
        Neptune.ai run ID for this hyperuniformity analysis experiment.
    
    Notes
    -----
    - Analysis is performed for all extrema types: all_extrema, minima, maxima
    - Hyperuniformity is indicated by S(k) → 0 as k → 0
    - Radial profiles are normalized for comparison across conditions
    - Power-law plots reveal the hyperuniformity exponent α
    """
    
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

        figure = postprocessing.plot_normalized_radial_profile_snapshots(
            k_modes= np.arange(dk, np.max(re.register["operators"]["k_vectors"][:,:,0][0,:]), dk),
            radial_profile_snapshots= re.register["snapshots_radial_profile"],
            symbol= extrema_type,
            )
        run["plot/"+extrema_type+" normalized_radial_profile snapshots"].upload(figure)

        figure = postprocessing.plot_power_law_snapshots(
            k_modes= np.arange(dk, np.max(re.register["operators"]["k_vectors"][:,:,0][0,:]), dk),
            radial_profile_snapshots= re.register["snapshots_radial_profile"],
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


    run.stop()

    return run_id


if __name__ == "__main__":


    with open(pathlib.Path("./parameters/hyperuniformity_analysis.yml"), "r") as file:
        parameters = yaml.safe_load(file)

    run(
        parameters= parameters
        )
