import os
from pathlib import Path
import sys
import pytest

# Ensure repository root is on sys.path
repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
os.environ["PYTHONPATH"] = repo_root

if __name__ == "__main__":
    test_files = [
        "tests/test_graph_routing.py",
        "tests/test_danger_zones.py",
        "tests/test_vision_pipeline.py",
        "tests/test_multi_agent_system.py",
        "tests/test_announcements.py",
        "tests/test_e2e_resq.py",
        "tests/test_operational_workflows.py",
        "tests/test_intelligence_core.py",
    ]
    pytest_args = [
        "-v",
        "-s",
        "-p", "no:typeguard",
        "-p", "no:flask",
        "-p", "no:faker",
    ] + test_files

    print(f"Running pytest with args: {pytest_args}")
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)
