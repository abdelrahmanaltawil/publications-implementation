import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path to import preprocessing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from preprocessing import extract_rainfall_events, clean_data


class TestExtractRainfallEvents(unittest.TestCase):

    def setUp(self):
        self.time_col = 'datetime'
        self.rain_col = 'value'
        self.ietd = 6

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=[self.time_col, self.rain_col])
        result = extract_rainfall_events(df, self.time_col, self.rain_col, self.ietd)
        self.assertTrue(result.empty)

    def test_single_continuous_event(self):
        # 3 hours of rain
        times = pd.to_datetime(['2023-01-01 10:00', '2023-01-01 11:00', '2023-01-01 12:00'])
        values = [1.0, 2.0, 1.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, self.ietd)
        
        self.assertEqual(len(result), 1)
        event = result.iloc[0]
        self.assertEqual(event['Duration (hrs)'], 3)
        self.assertEqual(event['Volume (mm)'], 4.0)
        self.assertEqual(event['Peak Precipitation (mm)'], 2.0)
        self.assertEqual(event['Start Time'], times[0])
        self.assertEqual(event['End Time'], times[2])

    def test_two_events_separated_by_gap(self):
        # Event 1: 10:00, 11:00 (End 11:00)
        # Gap: 12, 13, 14, 15, 16, 17 (6 dry hours -> 11:00 to 18:00 is 7 hours diff)
        # 18:00 is next rain. Diff = 7h. 7 > 6 is True. New event.
        times = pd.to_datetime([
            '2023-01-01 10:00', '2023-01-01 11:00', # Event 1
            '2023-01-01 18:00', '2023-01-01 19:00'  # Event 2
        ])
        values = [1.0, 1.0, 2.0, 2.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, self.ietd)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['Volume (mm)'], 2.0)
        self.assertEqual(result.iloc[1]['Volume (mm)'], 4.0)
        
        # Check Inter-Event Time
        # Start time of event 2 (18:00) - End time of event 1 (11:00) = 7 hours
        self.assertEqual(result.iloc[1]['Inter-Event Time (hrs)'], 7.0)

    def test_event_not_separated_if_gap_small(self):
        # Event 1: 10:00
        # Next rain: 16:00. Diff = 6h. 6 > 6 is False. Same event.
        times = pd.to_datetime(['2023-01-01 10:00', '2023-01-01 16:00'])
        values = [1.0, 1.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, self.ietd)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Duration (hrs)'], 7)

    def test_year_boundary_reset(self):
        # Event 1: 2022-12-31 20:00
        # Event 2: 2023-01-01 05:00
        # Diff = 9 hours. > 6. New event.
        times = pd.to_datetime(['2022-12-31 20:00', '2023-01-01 05:00']) 
        values = [1.0, 1.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, self.ietd)
        
        self.assertEqual(len(result), 2)
        # Inter-event time should be None because year changed
        self.assertTrue(pd.isna(result.iloc[1]['Inter-Event Time (hrs)']))

    # === NEW EDGE CASE TESTS ===

    def test_single_row_of_data(self):
        """Edge case: Only one hour of rainfall data."""
        times = pd.to_datetime(['2023-01-01 10:00'])
        values = [5.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, self.ietd)
        
        self.assertEqual(len(result), 1)
        event = result.iloc[0]
        self.assertEqual(event['Duration (hrs)'], 1)
        self.assertEqual(event['Volume (mm)'], 5.0)
        self.assertEqual(event['Peak Precipitation (mm)'], 5.0)
        self.assertEqual(event['Intensity (mm/hr)'], 5.0)
        # First event has no inter-event time
        self.assertTrue(pd.isna(event['Inter-Event Time (hrs)']))

    def test_very_long_continuous_event(self):
        """Edge case: Event spanning multiple days continuously."""
        times = pd.date_range('2023-01-01 00:00', periods=48, freq='h')
        values = [0.5] * 48  # 48 hours of light rain
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, self.ietd)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['Duration (hrs)'], 48)
        self.assertEqual(result.iloc[0]['Volume (mm)'], 24.0)

    def test_extreme_ietd_threshold_very_small(self):
        """Edge case: IETD=1 should separate events with 2+ hour gap."""
        times = pd.to_datetime(['2023-01-01 10:00', '2023-01-01 12:00'])  # 2h gap
        values = [1.0, 1.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, IETD_threshold=1)
        
        self.assertEqual(len(result), 2)  # Should be 2 events with IETD=1

    def test_extreme_ietd_threshold_very_large(self):
        """Edge case: IETD=24 should merge events with <24h gap."""
        times = pd.to_datetime([
            '2023-01-01 10:00', 
            '2023-01-02 08:00'  # 22 hour gap
        ])
        values = [1.0, 1.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, IETD_threshold=24)
        
        self.assertEqual(len(result), 1)  # Merged with IETD=24

    def test_intensity_calculation_correctness(self):
        """Verify intensity = volume / duration."""
        times = pd.to_datetime(['2023-01-01 10:00', '2023-01-01 11:00', '2023-01-01 12:00'])
        values = [3.0, 6.0, 3.0]  # Total = 12mm, duration = 3h
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, self.ietd)
        
        expected_intensity = 12.0 / 3.0  # 4.0 mm/hr
        self.assertAlmostEqual(result.iloc[0]['Intensity (mm/hr)'], expected_intensity, places=5)

    def test_many_small_events(self):
        """Edge case: Multiple small events with exact IETD gaps."""
        times = []
        values = []
        for i in range(5):
            start = pd.Timestamp('2023-01-01 00:00') + pd.Timedelta(hours=i * 8)
            times.append(start)
            values.append(1.0)
        
        df = pd.DataFrame({self.time_col: pd.to_datetime(times), self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, IETD_threshold=6)
        
        # 8h gaps > 6h IETD, so should have 5 separate events
        self.assertEqual(len(result), 5)


class TestCleanData(unittest.TestCase):
    """Tests for the clean_data function."""

    def setUp(self):
        self.time_col = 'datetime'
        self.rain_col = 'value'

    def test_empty_dataframe(self):
        """Edge case: Empty input DataFrame."""
        df = pd.DataFrame(columns=[self.time_col, self.rain_col])
        result = clean_data(df, self.time_col, self.rain_col)
        self.assertTrue(result.empty)

    def test_all_nan_values(self):
        """Edge case: All rainfall values are NaN."""
        times = pd.date_range('2023-06-01', periods=10, freq='h')
        values = [np.nan] * 10
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = clean_data(df, self.time_col, self.rain_col, winter_months=[])
        self.assertTrue(result.empty)

    def test_all_zero_values(self):
        """Edge case: All rainfall values are zero (dry period)."""
        times = pd.date_range('2023-06-01', periods=10, freq='h')
        values = [0.0] * 10
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = clean_data(df, self.time_col, self.rain_col, winter_months=[])
        self.assertTrue(result.empty)  # Zeros are filtered out

    def test_winter_month_filtering(self):
        """Test that winter months are correctly filtered."""
        times = pd.to_datetime([
            '2023-01-15 10:00',  # January - winter
            '2023-06-15 10:00',  # June - summer
            '2023-12-15 10:00',  # December - winter
        ])
        values = [1.0, 1.0, 1.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = clean_data(df, self.time_col, self.rain_col, winter_months=[1, 12])
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0][self.time_col].month, 6)

    def test_no_winter_filtering(self):
        """Test with no winter months (include all data)."""
        times = pd.to_datetime(['2023-01-15 10:00', '2023-06-15 10:00'])
        values = [1.0, 1.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = clean_data(df, self.time_col, self.rain_col, winter_months=[])
        
        self.assertEqual(len(result), 2)

    def test_outlier_removal_iqr(self):
        """Test IQR-based outlier removal."""
        times = pd.date_range('2023-06-01', periods=100, freq='h')
        # Create data with one extreme outlier
        values = [1.0] * 99 + [1000.0]  # 99 normal + 1 extreme
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = clean_data(df, self.time_col, self.rain_col, 
                          winter_months=[], remove_outliers=True)
        
        # Outlier should be removed
        self.assertEqual(len(result), 99)
        self.assertLessEqual(result[self.rain_col].max(), 1.0)

    def test_outlier_removal_disabled(self):
        """Test outlier removal when disabled."""
        times = pd.date_range('2023-06-01', periods=100, freq='h')
        values = [1.0] * 99 + [1000.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = clean_data(df, self.time_col, self.rain_col, 
                          winter_months=[], remove_outliers=False)
        
        # Outlier should be kept
        self.assertEqual(len(result), 100)
        self.assertEqual(result[self.rain_col].max(), 1000.0)

    def test_data_is_sorted_by_time(self):
        """Verify output is sorted by timestamp."""
        times = pd.to_datetime(['2023-06-01 12:00', '2023-06-01 10:00', '2023-06-01 11:00'])
        values = [1.0, 2.0, 3.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = clean_data(df, self.time_col, self.rain_col, winter_months=[])
        
        # Should be sorted chronologically
        times_result = result[self.time_col].tolist()
        self.assertEqual(times_result, sorted(times_result))

    def test_mixed_valid_invalid_values(self):
        """Edge case: Mix of valid, NaN, and zero values."""
        times = pd.date_range('2023-06-01', periods=5, freq='h')
        values = [1.0, np.nan, 0.0, 2.0, np.nan]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = clean_data(df, self.time_col, self.rain_col, winter_months=[])
        
        # Only 1.0 and 2.0 should remain
        self.assertEqual(len(result), 2)
        self.assertEqual(list(result[self.rain_col]), [1.0, 2.0])


if __name__ == '__main__':
    unittest.main()

