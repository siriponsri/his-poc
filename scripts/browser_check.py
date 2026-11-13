"""Compatibility entry point: run the v0.2 React browser workflow suite."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/'apps/web/scripts/browser_check.py'),run_name='__main__')
