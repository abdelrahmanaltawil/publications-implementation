import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import pathlib
import tempfile
import os
import sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from postprocessing import get_git_revision_hash, save_data


class TestGetGitRevisionHash(unittest.TestCase):
    """Tests for the get_git_revision_hash function."""

    def test_returns_string(self):
        """Verify function returns a string."""
        result = get_git_revision_hash()
        self.assertIsInstance(result, str)

    def test_returns_valid_hash_or_unknown(self):
        """Hash should be 40 chars or 'unknown'."""
        result = get_git_revision_hash()
        # Either a valid 40-char hash or 'unknown'
        self.assertTrue(
            len(result) == 40 or result == "unknown",
            f"Expected 40-char hash or 'unknown', got: {result}"
        )

    @patch('subprocess.check_output')
    def test_handles_git_not_available(self, mock_subprocess):
        """Edge case: Git not installed or not in a repo."""
        mock_subprocess.side_effect = FileNotFoundError("git not found")
        result = get_git_revision_hash()
        self.assertEqual(result, "unknown")

    @patch('subprocess.check_output')
    def test_handles_not_a_git_repo(self, mock_subprocess):
        """Edge case: Directory is not a git repository."""
        mock_subprocess.side_effect = Exception("fatal: not a git repository")
        result = get_git_revision_hash()
        self.assertEqual(result, "unknown")


class TestSaveData(unittest.TestCase):
    """Tests for the save_data function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_path = pathlib.Path(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_single_dataframe(self):
        """Test saving a single DataFrame."""
        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        datasets = {"test_data.csv": df}
        
        save_data(datasets, self.save_path)
        
        saved_file = self.save_path / "test_data.csv"
        self.assertTrue(saved_file.exists())
        loaded = pd.read_csv(saved_file)
        pd.testing.assert_frame_equal(loaded, df)

    def test_save_to_nested_directory(self):
        """Test saving to nested directory structure."""
        df = pd.DataFrame({'x': [1, 2]})
        datasets = {"subdir1/subdir2/data.csv": df}
        
        save_data(datasets, self.save_path)
        
        saved_file = self.save_path / "subdir1/subdir2/data.csv"
        self.assertTrue(saved_file.exists())

    def test_empty_datasets_dict(self):
        """Edge case: Empty datasets dictionary."""
        datasets = {}
        
        # Should not raise an error
        save_data(datasets, self.save_path)
        
        # No files should be created
        files = list(self.save_path.iterdir())
        self.assertEqual(len(files), 0)

    def test_none_value_in_datasets(self):
        """Edge case: None value in datasets dict."""
        datasets = {
            "valid.csv": pd.DataFrame({'a': [1]}),
            "none_value.csv": None
        }
        
        save_data(datasets, self.save_path)
        
        # Only valid.csv should be created
        self.assertTrue((self.save_path / "valid.csv").exists())
        self.assertFalse((self.save_path / "none_value.csv").exists())

    def test_empty_dataframe(self):
        """Edge case: Empty DataFrame in datasets."""
        df = pd.DataFrame(columns=['a', 'b'])
        datasets = {"empty.csv": df}
        
        # Should log warning but not create file
        save_data(datasets, self.save_path)
        
        # Empty DataFrame should not be saved
        self.assertFalse((self.save_path / "empty.csv").exists())

    def test_multiple_datasets(self):
        """Test saving multiple DataFrames at once."""
        datasets = {
            "data1.csv": pd.DataFrame({'a': [1]}),
            "data2.csv": pd.DataFrame({'b': [2]}),
            "subdir/data3.csv": pd.DataFrame({'c': [3]})
        }
        
        save_data(datasets, self.save_path)
        
        self.assertTrue((self.save_path / "data1.csv").exists())
        self.assertTrue((self.save_path / "data2.csv").exists())
        self.assertTrue((self.save_path / "subdir/data3.csv").exists())

    def test_dataframe_with_special_characters(self):
        """Test DataFrame with column names containing special chars."""
        df = pd.DataFrame({
            'Volume (mm)': [1.0, 2.0],
            'Duration (hrs)': [3.0, 4.0],
            'Intensity (mm/hr)': [0.5, 1.0]
        })
        datasets = {"special_cols.csv": df}
        
        save_data(datasets, self.save_path)
        
        loaded = pd.read_csv(self.save_path / "special_cols.csv")
        self.assertIn('Volume (mm)', loaded.columns)
        self.assertIn('Duration (hrs)', loaded.columns)

    def test_large_dataframe(self):
        """Edge case: Large DataFrame with many rows."""
        df = pd.DataFrame({
            'id': range(10000),
            'value': range(10000)
        })
        datasets = {"large.csv": df}
        
        save_data(datasets, self.save_path)
        
        loaded = pd.read_csv(self.save_path / "large.csv")
        self.assertEqual(len(loaded), 10000)

    def test_dataframe_with_datetime_column(self):
        """Test DataFrame with datetime column."""
        df = pd.DataFrame({
            'time': pd.date_range('2023-01-01', periods=5, freq='h'),
            'value': [1.0, 2.0, 3.0, 4.0, 5.0]
        })
        datasets = {"datetime_data.csv": df}
        
        save_data(datasets, self.save_path)
        
        loaded = pd.read_csv(self.save_path / "datetime_data.csv")
        self.assertEqual(len(loaded), 5)


if __name__ == '__main__':
    unittest.main()
