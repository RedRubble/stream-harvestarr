import logging
import os
import sys
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
sys.path.insert(0, APP_DIR)

os.environ.setdefault('CONFIGPATH', os.path.join(APP_DIR, '..', 'config', 'config.yml'))
os.makedirs(os.path.join(APP_DIR, '..', 'logs'), exist_ok=True)
sys.argv = sys.argv[:1]

import stream_harvestarr  # noqa: E402


def series(**overrides):
    ser = {'title': 'Have You Been Paying Attention?'}
    ser.update(overrides)
    return ser


def episode(**overrides):
    eps = {
        'title': 'Episode 10',
        'seasonNumber': 5,
        'episodeNumber': 10,
        'airDateUtc': '2026-03-07T09:30:00Z',
    }
    eps.update(overrides)
    return eps


class TestUrlUnchangedWhenNoPlaceholders(unittest.TestCase):

    def test_plain_url_is_returned_as_is(self):
        url = 'https://www.youtube.com/channel/UC123'
        self.assertEqual(
            stream_harvestarr.render_url_template(url, series(), episode()),
            url,
        )

    def test_url_containing_no_braces_ignores_missing_data(self):
        # A url with nothing to substitute must never be rejected, even
        # when the episode is missing every field a template could need.
        url = 'https://example.com/show/'
        eps = episode(airDateUtc=None, seasonNumber=None, episodeNumber=None)
        self.assertEqual(
            stream_harvestarr.render_url_template(url, series(), eps), url)


class TestReleaseDateVariables(unittest.TestCase):

    def test_release_year_is_substituted(self):
        url = 'https://10.com.au/episodes/{release-year}/'
        rendered = stream_harvestarr.render_url_template(url, series(), episode())
        self.assertEqual(rendered, 'https://10.com.au/episodes/2026/')

    def test_release_month_and_day_can_be_zero_padded_via_format_spec(self):
        url = '{release-year}-{release-month:02}-{release-day:02}'
        rendered = stream_harvestarr.render_url_template(
            url, series(), episode(airDateUtc='2026-01-05T00:00:00Z'))
        self.assertEqual(rendered, '2026-01-05')

    def test_release_month_and_day_are_unpadded_by_default(self):
        url = '{release-year}-{release-month}-{release-day}'
        rendered = stream_harvestarr.render_url_template(
            url, series(), episode(airDateUtc='2026-01-05T00:00:00Z'))
        self.assertEqual(rendered, '2026-1-5')

    def test_release_date_is_iso_formatted(self):
        url = 'https://example.com/{release-date}/'
        rendered = stream_harvestarr.render_url_template(url, series(), episode())
        self.assertEqual(rendered, 'https://example.com/2026-03-07/')

    def test_missing_air_date_skips_the_episode(self):
        url = 'https://10.com.au/episodes/{release-year}/'
        with self.assertLogs('stream_harvestarr', level='WARNING'):
            rendered = stream_harvestarr.render_url_template(
                url, series(), episode(airDateUtc=None))
        self.assertIsNone(rendered)

    def test_unparsable_air_date_skips_the_episode(self):
        url = 'https://10.com.au/episodes/{release-year}/'
        with self.assertLogs('stream_harvestarr', level='WARNING'):
            rendered = stream_harvestarr.render_url_template(
                url, series(), episode(airDateUtc='not-a-date'))
        self.assertIsNone(rendered)


class TestSeasonEpisodeVariables(unittest.TestCase):

    def test_season_and_episode_are_substituted(self):
        url = 'https://example.com/s{season}/e{episode}/'
        rendered = stream_harvestarr.render_url_template(url, series(), episode())
        self.assertEqual(rendered, 'https://example.com/s5/e10/')

    def test_zero_padding_via_format_spec(self):
        url = 'https://example.com/s{season:02}e{episode:02}'
        rendered = stream_harvestarr.render_url_template(
            url, series(), episode(seasonNumber=5, episodeNumber=3))
        self.assertEqual(rendered, 'https://example.com/s05e03')

    def test_absolute_episode_is_substituted_when_present(self):
        url = 'https://example.com/episode-{absolute-episode}/'
        rendered = stream_harvestarr.render_url_template(
            url, series(), episode(absoluteEpisodeNumber=46))
        self.assertEqual(rendered, 'https://example.com/episode-46/')

    def test_absolute_episode_missing_skips_the_episode(self):
        # Most non-anime Sonarr series never populate absoluteEpisodeNumber.
        url = 'https://example.com/episode-{absolute-episode}/'
        with self.assertLogs('stream_harvestarr', level='WARNING'):
            rendered = stream_harvestarr.render_url_template(url, series(), episode())
        self.assertIsNone(rendered)


class TestTitleAndYearVariables(unittest.TestCase):

    def test_series_title_is_url_quoted(self):
        url = 'https://example.com/{series-title}/'
        rendered = stream_harvestarr.render_url_template(
            url, series(title='Have You Been Paying Attention?'), episode())
        self.assertEqual(rendered, 'https://example.com/Have%20You%20Been%20Paying%20Attention%3F/')

    def test_episode_title_is_url_quoted(self):
        url = 'https://example.com/watch/{episode-title}'
        rendered = stream_harvestarr.render_url_template(
            url, series(), episode(title="Ricky's Big Day"))
        self.assertEqual(rendered, "https://example.com/watch/Ricky%27s%20Big%20Day")

    def test_series_year_is_substituted(self):
        url = 'https://example.com/{series-year}/show/'
        rendered = stream_harvestarr.render_url_template(
            url, series(year=2018), episode())
        self.assertEqual(rendered, 'https://example.com/2018/show/')

    def test_series_year_missing_skips_the_episode(self):
        url = 'https://example.com/{series-year}/show/'
        with self.assertLogs('stream_harvestarr', level='WARNING'):
            rendered = stream_harvestarr.render_url_template(url, series(), episode())
        self.assertIsNone(rendered)


class TestUnsupportedVariables(unittest.TestCase):

    def test_unknown_variable_name_skips_and_logs_an_error(self):
        url = 'https://example.com/{made-up-field}/'
        with self.assertLogs('stream_harvestarr', level='ERROR') as cm:
            rendered = stream_harvestarr.render_url_template(url, series(), episode())
        self.assertIsNone(rendered)
        self.assertIn('made-up-field', cm.output[0])
        self.assertIn('Supported variables', cm.output[0])

    def test_typo_of_a_real_variable_is_reported_not_guessed(self):
        url = 'https://example.com/{relase-year}/'
        with self.assertLogs('stream_harvestarr', level='ERROR'):
            rendered = stream_harvestarr.render_url_template(url, series(), episode())
        self.assertIsNone(rendered)

    def test_malformed_template_is_rejected_not_raised(self):
        url = 'https://example.com/{season'
        with self.assertLogs('stream_harvestarr', level='ERROR'):
            rendered = stream_harvestarr.render_url_template(url, series(), episode())
        self.assertIsNone(rendered)


class TestMultipleVariablesTogether(unittest.TestCase):

    def test_combined_template_renders_all_fields(self):
        url = 'https://example.com/{series-title}/{release-year}/s{season:02}e{episode:02}'
        rendered = stream_harvestarr.render_url_template(
            url, series(title='CHUMP'), episode(seasonNumber=2, episodeNumber=7))
        self.assertEqual(rendered, 'https://example.com/CHUMP/2026/s02e07')


if __name__ == '__main__':
    unittest.main()
