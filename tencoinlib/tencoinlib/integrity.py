# tencoinlib/integrity.py

import hashlib
from pathlib import Path


def _collect_files(root: Path) -> list[Path]:
    return sorted(
        (
            p for p in root.rglob("*.py")
            if "__pycache__" not in p.parts
        ),
        key=lambda p: str(p.relative_to(root))
    )


def compute_library_hash() -> str:
    """Compute a deterministic SHA256 hash of all tencoinlib .py source files."""
    root = Path(__file__).parent
    sha256 = hashlib.sha256()
    for path in _collect_files(root):
        sha256.update(path.read_bytes())
    return sha256.hexdigest()


def get_file_manifest() -> list[tuple[str, str]]:
    """Return (relative_path, sha256_hex) for each file included in the hash."""
    root = Path(__file__).parent
    return [
        (str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in _collect_files(root)
    ]