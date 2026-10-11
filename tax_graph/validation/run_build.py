"""Record a full library rebuild using the current Python interpreter."""
import importlib.metadata
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent
command = [sys.executable, "official/tools/build.py", *sys.argv[1:]]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout = result.stdout.decode("utf-8", "replace")
stderr = result.stderr.decode("utf-8", "replace")
warnings = sorted({match.group(0) for line in stderr.splitlines()
                   for match in [re.search(r"\b\w*Warning:.*", line)] if match})
log = stdout + ("\n" + "\n".join(warnings) + "\n" if warnings else "")
if result.returncode:
    log += stderr
(DEST / "build.log").write_text(log, encoding="utf-8")
packages = ("PyMuPDF", "beautifulsoup4", "requests", "openpyxl", "numpy", "sentence-transformers")
versions = {}
for package in packages:
    try:
        versions[package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        versions[package] = None
(DEST / "build_environment.json").write_text(json.dumps({
    "python": sys.version.split()[0], "command": "python official/tools/build.py" +
    (" " + " ".join(sys.argv[1:]) if sys.argv[1:] else ""), "exit_code": result.returncode,
    "packages": versions, "warnings": warnings,
}, indent=2) + "\n", encoding="utf-8")
print(log, end="")
sys.exit(result.returncode)
