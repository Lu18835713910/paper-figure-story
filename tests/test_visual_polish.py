"""Current v2 regression entry; v1 expectations retained in legacy_visual_polish_v1.py."""
from pathlib import Path
import runpy
if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("test_visual_polish_locked.py")), run_name="__main__")
