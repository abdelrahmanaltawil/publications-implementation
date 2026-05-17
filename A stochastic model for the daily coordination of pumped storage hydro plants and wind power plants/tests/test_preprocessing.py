import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.preprocessing import create_run_directory, build_network_data


def test_create_run_directory(tmp_path):
    run_dir = create_run_directory(str(tmp_path / "output"))
    assert run_dir.exists()
    assert run_dir.name.startswith("run_")
    assert (run_dir / "metadata").exists()


def test_build_network_data_water_only(tmp_path):
    inp = tmp_path / "network.inp"
    inp.write_text("[TITLE]\nTest\n")

    config = {
        "run_water": True,
        "run_energy": False,
        "run_nexus": False,
        "water": {"network": str(inp)},
        "T": 24,
    }
    data = build_network_data(config, project_root=Path("/"))

    assert "water" in data
    assert data["water"]["inp_file"] == str(inp)


def test_build_network_data_missing_water_file(tmp_path):
    config = {
        "run_water": True,
        "run_energy": False,
        "run_nexus": False,
        "water": {"network": "nonexistent/network.inp"},
        "T": 24,
    }
    with pytest.raises(FileNotFoundError):
        build_network_data(config, project_root=tmp_path)


def test_build_network_data_energy_only(tmp_path):
    dss = tmp_path / "master.dss"
    dss.write_text("! OpenDSS master\n")

    config = {
        "run_water": False,
        "run_energy": True,
        "run_nexus": False,
        "energy": {
            "network": str(dss),
            "nominal_voltage": 11.0,
            "voltage_tolerance": 0.10,
            "n_current_segments": 5,
            "technologies": {},
            "cost": {},
        },
        "T": 24,
    }
    data = build_network_data(config, project_root=Path("/"))

    assert "energy" in data
    assert "water" not in data
    assert data["energy"]["dss_file"] == str(dss)
