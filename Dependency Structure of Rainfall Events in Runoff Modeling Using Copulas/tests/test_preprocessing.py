import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path to import preprocessing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from preprocessing import extract_rainfall_events

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
        # Event 1: 2022-12-31 23:00
        # Event 2: 2023-01-01 02:00
        # Diff = 3 hours. 3 < 6, so should be same event?
        # Wait, if diff < 6, it merges.
        # Let's make gap large so it splits, but crosses year.
        
        times = pd.to_datetime(['2022-12-31 20:00', '2023-01-01 05:00']) 
        # Diff = 9 hours. > 6. New event.
        values = [1.0, 1.0]
        df = pd.DataFrame({self.time_col: times, self.rain_col: values})
        
        result = extract_rainfall_events(df.copy(), self.time_col, self.rain_col, self.ietd)
        
        self.assertEqual(len(result), 2)
        # Inter-event time should be None because year changed
        self.assertTrue(pd.isna(result.iloc[1]['Inter-Event Time (hrs)']))

if __name__ == '__main__':
    unittest.main()
