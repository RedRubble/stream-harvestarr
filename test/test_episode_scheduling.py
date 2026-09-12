import os
import sys
import unittest
from datetime import datetime

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
sys.path.insert(0, APP_DIR)

os.environ.setdefault('CONFIGPATH', os.path.join(APP_DIR, '..', 'config', 'config.yml'))
os.makedirs(os.path.join(APP_DIR, '..', 'logs'), exist_ok=True)
sys.argv = sys.argv[:1]

import stream_harvestarr  # noqa: E402


class TestEpisodeScheduling(unittest.TestCase):

    def client(self, episodes):
        client = object.__new__(stream_harvestarr.StreamHarvester)
        client.get_episodes_by_series_id = lambda series_id: episodes
        return client

    def series(self):
        return [{'id': 424, 'title': 'Taskmaster (AU)', 'monitored': True}]

    def test_undated_tba_is_not_requested(self):
        episodes = [{
            'id': 1, 'seriesId': 424, 'title': 'TBA', 'monitored': True,
            'hasFile': False,
        }]
        needed = self.client(episodes).getseriesepisodes(self.series())
        self.assertEqual(needed, [])

    def test_undated_to_be_announced_is_not_requested(self):
        episodes = [{
            'id': 1, 'seriesId': 424, 'title': 'To Be Announced',
            'monitored': True, 'hasFile': False,
        }]
        needed = self.client(episodes).getseriesepisodes(self.series())
        self.assertEqual(needed, [])

    def test_dated_tba_remains_eligible(self):
        episodes = [{
            'id': 1, 'seriesId': 424, 'title': 'TBA', 'monitored': True,
            'hasFile': False, 'airDateUtc': '2020-01-01T00:00:00Z',
        }]
        needed = self.client(episodes).getseriesepisodes(self.series())
        self.assertEqual([episode['id'] for episode in needed], [1])


if __name__ == '__main__':
    unittest.main()
