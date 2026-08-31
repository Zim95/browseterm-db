'''Pure unit tests for format_snapshot_version - no DB needed.'''
from unittest import TestCase

from browseterm_db.common.snapshot_version import format_snapshot_version


class TestFormatSnapshotVersion(TestCase):
    def test_examples_from_the_plan(self) -> None:
        self.assertEqual(format_snapshot_version(1), "0.0.0.0.1")
        self.assertEqual(format_snapshot_version(9), "0.0.0.0.9")
        self.assertEqual(format_snapshot_version(10), "0.0.0.1.0")
        self.assertEqual(format_snapshot_version(99), "0.0.0.9.9")
        self.assertEqual(format_snapshot_version(100), "0.0.1.0.0")
        self.assertEqual(format_snapshot_version(99999), "9.9.9.9.9")

    def test_zero(self) -> None:
        self.assertEqual(format_snapshot_version(0), "0.0.0.0.0")

    def test_negative_raises(self) -> None:
        with self.assertRaises(ValueError):
            format_snapshot_version(-1)

    def test_overflow_raises(self) -> None:
        with self.assertRaises(ValueError):
            format_snapshot_version(100000)
