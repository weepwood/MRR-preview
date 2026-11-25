import unittest
from unittest.mock import patch
import assemble

ITEMS = [assemble.identity('v1.1', 'a'*40), assemble.identity('v1.2', 'b'*40)]

class OnlineTests(unittest.TestCase):
    @patch('assemble.expected', return_value=ITEMS)
    @patch('assemble.fetch_json')
    def test_checks_root_and_both_versions(self, fetch, expected):
        fetch.side_effect = [{'versions': ITEMS}, *ITEMS]
        assemble.online()
        self.assertEqual([c.args[0] for c in fetch.call_args_list], ['versions.json', 'v1.1/preview-build.json', 'v1.2/preview-build.json'])

    @patch('assemble.expected', return_value=ITEMS)
    @patch('assemble.time.sleep')
    @patch('assemble.fetch_json')
    def test_stale_root_retries_without_accepting_old_versions(self, fetch, sleep, expected):
        fetch.side_effect = [{'versions': []}, {'versions': ITEMS}, *ITEMS]
        assemble.online()
        self.assertEqual(fetch.call_count, 4)
        sleep.assert_called_once_with(15)

    @patch('assemble.expected', return_value=ITEMS)
    @patch('assemble.time.monotonic', side_effect=[0, 601])
    @patch('assemble.fetch_json')
    def test_stale_version_fails(self, fetch, clock, expected):
        fetch.side_effect = [{'versions': ITEMS}, ITEMS[0], ITEMS[0]]
        with self.assertRaises(ValueError):
            assemble.online()

if __name__ == '__main__':
    unittest.main()
