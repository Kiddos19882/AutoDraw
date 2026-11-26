"""Compatibility entry point: A28 now uses the shared AutoDraw FILL-001 UI."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source/preparation"))
from engine001_a28_live import *  # compatibility for the E2 contracts

if __name__ == "__main__":
    import runpy
    sys.path.insert(0, str(ROOT))
    runpy.run_path(str(ROOT / "integrated_app.py"), run_name="__main__")
