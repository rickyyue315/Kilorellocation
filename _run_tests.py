"""Run all tests and capture output properly."""
import sys
import os
import subprocess

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Run tests without capturing (avoid PowerShell pipe issues)
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-x", "-q", "--tb=short", "-s",
     "--tb=short", "-p", "no:warnings"],
    capture_output=False,
    text=True
)

print(f"\n\nExit code: {result.returncode}")