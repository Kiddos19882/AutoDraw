"""Independent CI Firefox 159 binary selector contracts; no browser started."""
from pathlib import Path
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from run_egret_stage_reference_firefox import find_firefox


class FrozenFirefoxSelectorContract(unittest.TestCase):
    def test_01_real_explicit_pinned_binary_wins_over_runner_default(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"firefox.exe"
            path.write_bytes(b"fixture")
            with patch.dict(os.environ,{"AUTODRAW_PINNED_FIREFOX":str(path)}):
                self.assertEqual(find_firefox(),path)

    def test_02_explicit_missing_pinned_binary_fails_closed(self):
        with TemporaryDirectory() as tmp:
            with patch.dict(os.environ,{
                "AUTODRAW_PINNED_FIREFOX":str(Path(tmp)/"missing.exe")
            }):
                with self.assertRaisesRegex(FileNotFoundError,
                        "Pinned Firefox binary missing"):
                    find_firefox()

    def test_03_explicit_empty_binary_fails_closed(self):
        with patch.dict(os.environ,{"AUTODRAW_PINNED_FIREFOX":""}):
            with self.assertRaises(FileNotFoundError):
                find_firefox()


if __name__=="__main__":
    unittest.main()
