"""เทสต์ ip_detect: consensus, private/CGNAT"""

import unittest
from unittest import mock

from cloudflare_ddns import ip_detect


class GetPublicIpTest(unittest.TestCase):
    def setUp(self):
        self.patcher = mock.patch.object(ip_detect, "_http_get")
        self.http_get = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_first_provider_wins_without_consensus(self):
        self.http_get.side_effect = ["1.2.3.4", "9.9.9.9", "9.9.9.9", "9.9.9.9"]
        self.assertEqual(ip_detect.get_public_ip(4, consensus=None), "1.2.3.4")

    def test_consensus_returns_ip_when_2_agree(self):
        self.http_get.side_effect = ["1.2.3.4", "1.2.3.4", "9.9.9.9", "9.9.9.9"]
        self.assertEqual(ip_detect.get_public_ip(4, consensus=2), "1.2.3.4")

    def test_consensus_returns_none_when_disagree(self):
        self.http_get.side_effect = ["1.2.3.4", "9.9.9.9", "5.6.7.8", "1.2.3.4"]
        self.assertIsNone(ip_detect.get_public_ip(4, consensus=2))

    def test_consensus_ignores_invalid_answers(self):
        self.http_get.side_effect = ["not-an-ip", "1.2.3.4", "1.2.3.4", "9.9.9.9"]
        self.assertEqual(ip_detect.get_public_ip(4, consensus=2), "1.2.3.4")

    def test_consensus_skips_errors(self):
        self.http_get.side_effect = [
            mock.Mock(side_effect=OSError("boom")),
            "1.2.3.4",
            "1.2.3.4",
            "9.9.9.9",
        ]
        self.assertEqual(ip_detect.get_public_ip(4, consensus=2), "1.2.3.4")

    def test_consensus_none_when_only_one_answers(self):
        self.http_get.side_effect = [
            mock.Mock(side_effect=OSError("boom")),
            mock.Mock(side_effect=OSError("boom")),
            "1.2.3.4",
            mock.Mock(side_effect=OSError("boom")),
        ]
        self.assertIsNone(ip_detect.get_public_ip(4, consensus=2))

    def test_no_answer_returns_none(self):
        self.http_get.side_effect = mock.Mock(side_effect=OSError("boom"))
        self.assertIsNone(ip_detect.get_public_ip(4, consensus=2))


class PrivateIpTest(unittest.TestCase):
    def test_private(self):
        self.assertTrue(ip_detect.is_private_ip("192.168.1.10"))
        self.assertTrue(ip_detect.is_private_ip("10.0.0.5"))

    def test_cgnat(self):
        self.assertTrue(ip_detect.is_private_ip("100.64.0.1"))
        self.assertTrue(ip_detect.is_private_ip("100.100.100.100"))

    def test_public(self):
        self.assertFalse(ip_detect.is_private_ip("1.2.3.4"))
        self.assertFalse(ip_detect.is_private_ip("8.8.8.8"))


if __name__ == "__main__":
    unittest.main()