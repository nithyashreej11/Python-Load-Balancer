
import unittest
from load_balancer import RoundRobinScheduler, BACKENDS


class TestRoundRobinScheduler(unittest.TestCase):

    def setUp(self):
        self.scheduler = RoundRobinScheduler(BACKENDS)

    def test_round_robin_rotation(self):
        selected = [
            self.scheduler.next_backend()[0]
            for _ in range(6)
        ]

        expected = [
            "Server-1",
            "Server-2",
            "Server-3",
            "Server-1",
            "Server-2",
            "Server-3"
        ]

        self.assertEqual(selected, expected)

    def test_skip_down_backend(self):
        self.scheduler.set_status("Server-2", False)

        selected = [
            self.scheduler.next_backend()[0]
            for _ in range(4)
        ]

        self.assertNotIn("Server-2", selected)

    def test_all_backends_down(self):
        for name, host, port in BACKENDS:
            self.scheduler.set_status(name, False)

        self.assertIsNone(self.scheduler.next_backend())

    def test_backend_recovery(self):
        self.scheduler.set_status("Server-2", False)
        self.scheduler.set_status("Server-2", True)

        self.assertTrue(self.scheduler.get_status("Server-2"))

    def test_excluded_backend(self):
        selected = self.scheduler.next_backend(
            excluded={"Server-1", "Server-2"}
        )

        self.assertEqual(selected[0], "Server-3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
