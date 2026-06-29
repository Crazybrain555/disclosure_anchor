import unittest

from disclosure_anchor.api.routers.health import get_health


class HealthTests(unittest.TestCase):
    def test_health_payload(self) -> None:
        payload = get_health()
        self.assertEqual(payload.status, "ok")
        self.assertEqual(payload.service, "disclosure_anchor")
        self.assertTrue(payload.version)


if __name__ == "__main__":
    unittest.main()
