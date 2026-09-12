"""
Unit tests for the Sonarr manual-import request and exact-file selection.
"""
import os
import sys
import tempfile
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
sys.path.insert(0, APP_DIR)

os.environ.setdefault('CONFIGPATH', os.path.join(APP_DIR, '..', 'config', 'config.yml'))
os.makedirs(os.path.join(APP_DIR, '..', 'logs'), exist_ok=True)
sys.argv = sys.argv[:1]

import stream_harvestarr  # noqa: E402


class FakeResponse(object):

    status_code = 200

    def __init__(self, data=None):
        self.data = {} if data is None else data

    def json(self):
        return self.data

    def raise_for_status(self):
        return None


class TestManualImport(unittest.TestCase):

    def setUp(self):
        self.client = object.__new__(stream_harvestarr.StreamHarvester)
        self.client.base_url = 'http://sonarr:8989'
        self.client.sonarr_api_version = 'api/v3'
        self.client.download_directory = '/download'
        self.client.sent = {}

    def test_manual_import_scan_filters_folder_and_series(self):
        calls = {}

        def request_get(url, params=None):
            calls['url'] = url
            calls['params'] = params
            return FakeResponse([])

        self.client.request_get = request_get

        self.assertEqual(self.client.get_manual_import('/download', '314'), [])
        self.assertEqual(calls, {
            'url': 'http://sonarr:8989/api/v3/manualimport',
            'params': {
                'folder': '/download',
                'seriesId': 314,
                'filterExistingFiles': True,
            },
        })

    def test_import_uses_exact_path_episode_and_sonarr_metadata(self):
        candidate = {
            'path': '/download/episode.mkv',
            'quality': {'quality': {'name': 'WEBRip'}},
            'languages': [{'id': 1, 'name': 'English'}],
            'releaseGroup': 'Example',
        }
        self.client.get_manual_import = lambda folder, series_id: [candidate]

        def request_put(url, params=None, jsondata=None):
            self.client.sent = {
                'url': url,
                'params': params,
                'data': jsondata,
            }
            return FakeResponse()

        self.client.request_put = request_put
        series = {'id': 314}
        episode = {'id': 2718, 'seasonNumber': 2}

        self.assertTrue(self.client.import_downloaded_file(
            series, episode, '/download/episode.mkv'))
        self.assertEqual(self.client.sent['url'],
                         'http://sonarr:8989/api/v3/manualimport')
        self.assertEqual(self.client.sent['data'], [{
            'path': '/download/episode.mkv',
            'seriesId': 314,
            'seasonNumber': 2,
            'episodeIds': [2718],
            'quality': {'quality': {'name': 'WEBRip'}},
            'languages': [{'id': 1, 'name': 'English'}],
            'releaseGroup': 'Example',
        }])

    def test_import_rejects_file_not_returned_by_sonarr(self):
        self.client.get_manual_import = lambda folder, series_id: []
        self.assertFalse(self.client.import_downloaded_file(
            {'id': 314}, {'id': 2718, 'seasonNumber': 2},
            '/download/missing.mkv'))

    def test_find_downloaded_file_ignores_partial_and_subtitle_files(self):
        series = {'id': 314, 'title': 'Series', 'path': '/tv/Series'}
        episode = {
            'id': 2718, 'title': 'Episode', 'seasonNumber': 2,
            'episodeNumber': 3,
        }
        self.client.build_download_template = lambda ser, eps, season, episode_number: (
            '/download/Series - S02E03 - Episode [series-314-episode-2718].%(ext)s')
        with tempfile.TemporaryDirectory() as directory:
            self.client.download_directory = directory
            expected = os.path.join(
                directory, 'Series - S02E03 - Episode [series-314-episode-2718].mkv')
            open(expected, 'w').close()
            open(expected + '.part', 'w').close()
            open(expected[:-4] + '.srt', 'w').close()
            self.client.build_download_template = lambda ser, eps, season, episode_number: (
                os.path.join(directory,
                             'Series - S02E03 - Episode [series-314-episode-2718].%(ext)s'))

            self.assertEqual(
                self.client.find_downloaded_file(series, episode, '02', '03'),
                expected)


if __name__ == '__main__':
    unittest.main()
