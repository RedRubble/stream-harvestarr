import os
import sys
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
sys.path.insert(0, APP_DIR)

os.environ.setdefault('CONFIGPATH', os.path.join(APP_DIR, '..', 'config', 'config.yml'))
os.makedirs(os.path.join(APP_DIR, '..', 'logs'), exist_ok=True)

import utils  # noqa: E402


class TestYtdlProgressLogging(unittest.TestCase):

    def test_percentage_progress_is_suppressed(self):
        message = '[download]   7.0% of ~   1.97GiB at 34.93MiB/s ETA 00:55 (frag 33/471)'
        self.assertTrue(utils._is_download_progress(message))

    def test_non_progress_download_message_is_retained(self):
        self.assertFalse(utils._is_download_progress(
            '[download] "Episode 12" did not match the episode'))

    def test_progress_without_space_after_percent_is_suppressed(self):
        self.assertTrue(utils._is_download_progress('[download] 7.0%'))


if __name__ == '__main__':
    unittest.main()
