# env imports
import yaml
import pathlib
import neptune.new as neptune


# local imports
import active_flow.extrema_search.preprocessing as preprocessing
import active_flow.extrema_search.algorithm_tasks as task
import active_flow.extrema_search.postprocessing as postprocessing
import active_flow.extrema_search.helpers.register as re


def run(parameters: dict) -> str:
    '''
    Placeholder
    '''

    run = neptune.init_run(
            tags=["extrema search"],
        )
    run_id = run["sys/id"].fetch()
    re.init_register()

    reference_run = neptune.init_run(
        with_id=parameters["preprocessing"]["experiment_ID"],
        mode="read-only"
    )

    run["parameters"] = reference_run["parameters"].fetch()
    run["parameters/reference_snapshots_experiment"] = parameters["preprocessing"]["experiment_ID"]
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
    postprocessing.remove_data(
        data_path= pathlib.Path(pathlib.Path(parameters["preprocessing"]["download_path"]))
    )
        
    reference_run.stop()


    # Algorithm
    w_snapshots = task.compute_vorticity(
        snapshots = re.register["snapshots"]
    )
    task.create_grid(
        x= re.register["operators"]["x_vectors"][:,:,0],
        y= re.register["operators"]["x_vectors"][:,:,1],
        w= w_snapshots
        )
    extrema_snapshots = task.find_extrema(
        grids= re.register["grids"],
        threshold= None
        )


    # Postprocessing
    postprocessing.save_arrays(
        operators= re.register["operators"], 
        extrema_snapshots= extrema_snapshots,
        save_path= pathlib.Path(parameters["postprocessing"]["save_path"]+"/arrays")
    )
    run["data/arrays"].upload_files(parameters["postprocessing"]["save_path"]+"/arrays")
    run.wait()
    postprocessing.remove_data(
        data_path= pathlib.Path(parameters["postprocessing"]["save_path"])
    )

    figure = postprocessing.plot_extrema_count_snapshots(
        extrema_snapshots= extrema_snapshots
    )
    run["image/all extrema count"].upload(figure)

    figure = postprocessing.plot_point_cloud_snapshots(
        x_vector = re.register["operators"]["x_vectors"],
        extrema_snapshots = extrema_snapshots, 
        symbol= "All Extrema"
        )
    run["image/all extrema snapshots"].upload(figure)

    figure = postprocessing.plot_point_cloud_snapshots(
        x_vector = re.register["operators"]["x_vectors"],
        extrema_snapshots = extrema_snapshots, 
        symbol= "Minima"
        )
    run["image/minima snapshots"].upload(figure)

    figure = postprocessing.plot_point_cloud_snapshots(
        x_vector = re.register["operators"]["x_vectors"],
        extrema_snapshots = extrema_snapshots, 
        symbol= "Maxima"
        )
    run["image/maxima snapshots"].upload(figure)

    interactive_figure = postprocessing.interactive_point_cloud_plot(
        x_vector = re.register["operators"]["x_vectors"],
        extrema_snapshots = extrema_snapshots,
        w_snapshots= w_snapshots,
    )
    run["interactive plots/point cloud"].upload(interactive_figure)

    interactive_figure = postprocessing.interactive_surface_plot(
        x_vector= re.register["operators"]["x_vectors"],
        w_snapshots= w_snapshots
        )
    run["interactive plots/surface"].upload(interactive_figure)


    run.stop()

    return run_id


if __name__ == "__main__":


    with open(pathlib.Path("./parameters/extrema_search.yml"), "r") as file:
        parameters = yaml.safe_load(file)

    run(
        parameters= parameters
        )
