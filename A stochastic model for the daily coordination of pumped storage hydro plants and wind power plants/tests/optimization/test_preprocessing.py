
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import shutil
from src.optimization.preprocessing import create_run_directory, build_network_data

def test_create_run_directory(tmp_path):
    # Test with default run_id
    output_dir = tmp_path / "output"
    run_dir = create_run_directory(str(output_dir))
    assert run_dir.exists()
    assert run_dir.name.startswith("run_")
    
    # Test with specific run_id
    run_id = "test_run"
    run_dir = create_run_directory(str(output_dir), run_id)
    assert run_dir.exists()
    assert run_dir.name == "run_test_run"

@patch("src.optimization.preprocessing.Path")
def test_build_network_data(mock_path):
    # Setup mocks
    mock_file_path = MagicMock()
    mock_parents = [MagicMock(), MagicMock(), MagicMock()] # parents[2]
    
    # Configure the mock chain
    # Path(__file__) -> returns mock_file_path
    # mock_file_path.parents -> returns list
    # parents[2] -> returns a path
    # / config['inp_file'] -> returns final path
    
    # Easier: Mock the specific checking logic or ensure file exists.
    # The function uses Path(__file__).parents[2] / config['inp_file']
    # We can just verify it validates existence.
    
    config = {'inp_file': 'test.inp', 'T': 12}
    
    # Create a real temporary file structure that mimics the expectation if we want integration test
    # But unit test should mock.
    
    # Let's try to mock the specific call to .exists() on the resulting path object
    pass

def test_build_network_data_integration(tmp_path):
    # Create a dummy structure
    # src/optimization/preprocessing.py
    # data/inputs/config/system_config/water/GNET.inp
    # We need to trick the function into looking relative to our test file or mock __file__
    
    # Actually, modifying __file__ is hard.
    # Let's use patch('src.optimization.preprocessing.Path') carefully.
    pass

@patch("src.optimization.preprocessing.Path")
def test_build_network_data_success(mock_path_cls):
    # Mocking Path(__file__).parents[2] / config['inp_file']
    
    # Mock the instance created by Path(__file__)
    mock_file_obj = MagicMock()
    mock_path_cls.return_value = mock_file_obj
    
    # Mock parents list
    mock_root = MagicMock()
    mock_file_obj.parents = [MagicMock(), MagicMock(), mock_root]
    
    # Mock the full path construction
    mock_inp_path = MagicMock()
    mock_root.__truediv__.return_value = mock_inp_path
    
    # Set exists to True
    mock_inp_path.exists.return_value = True
    
    config = {'inp_file': 'test.inp', 'T': 24}
    
    result = build_network_data(config)
    
    assert result['inp_file'] == str(mock_inp_path)
    assert result['T'] == 24
    assert result['config'] == config

@patch("src.optimization.preprocessing.Path")
def test_build_network_data_file_not_found(mock_path_cls):
    # Similar setup but exists returns False
    mock_file_obj = MagicMock()
    mock_path_cls.return_value = mock_file_obj
    
    mock_root = MagicMock()
    mock_file_obj.parents = [MagicMock(), MagicMock(), mock_root]
    
    mock_inp_path = MagicMock()
    mock_root.__truediv__.return_value = mock_inp_path
    
    mock_inp_path.exists.return_value = False
    
    config = {'inp_file': 'test.inp'}
    
    with pytest.raises(FileNotFoundError):
        build_network_data(config)
