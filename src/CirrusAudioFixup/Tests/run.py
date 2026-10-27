"""Run the explicitly selected, asset-free public port regressions."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[3]/'tools/test.py'),run_name='__main__')
