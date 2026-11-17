"""Verify the delivered files. Does not validate scientific inputs."""
from pathlib import Path
import hashlib
import sys

root = Path(__file__).resolve().parent
manifest = root / "SHA256SUMS.txt"
if not manifest.is_file():
    raise SystemExit("Missing SHA256SUMS.txt")
failed = []
checked = 0
for line in manifest.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    expected, name = line.split("  ", 1)
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        failed.append(name + ": missing or unsafe path")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    checked += 1
    if actual != expected:
        failed.append(name + ": checksum mismatch")
print(f"Checked {checked} files; failed {len(failed)}")
for message in failed:
    print(message)
sys.exit(1 if failed else 0)
