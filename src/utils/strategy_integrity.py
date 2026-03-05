# SOURCE_OF_TRUTH: INTEGRITY_VERIFICATION -- IMMUTABLE
"""
Cryptographic integrity verification for locked strategy file and source files.
Read-only verification — never modifies any files.
"""

import hashlib
import os
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
STRATEGY_FILE = os.path.join(PROJECT_ROOT, "STRATEGY_LOCKED_V1.4_CE_PE.md")

# Hardcoded expected hash — computed from the original locked strategy file
EXPECTED_HASH = "afc7b32f11ca2bf57c2f98730fba11a09b10694e6f2d079e4cb48dd95e1ccc89"


def _compute_file_hash(filepath: str) -> str:
    """Compute SHA256 hash of a file."""
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_strategy_hash() -> bool:
    """
    Verify that STRATEGY_LOCKED_V1.4_CE_PE.md has not been modified.
    Returns True if hash matches, False if mismatch or file missing.
    """
    computed = _compute_file_hash(STRATEGY_FILE)

    if computed == EXPECTED_HASH:
        logger.info("INTEGRITY: Strategy file hash VERIFIED — %s", computed[:16])
        return True

    print()
    print("+" + "=" * 62 + "+")
    print("|  CRITICAL: STRATEGY_LOCKED_V1.4_CE_PE.md HAS BEEN MODIFIED  |")
    print("|  HASH MISMATCH -- RECON INVALID -- DO NOT TRUST RESULTS     |")
    print("+" + "=" * 62 + "+")
    print(f"  Computed: {computed}")
    print(f"  Expected: {EXPECTED_HASH}")
    print()

    logger.error("INTEGRITY: Strategy file hash MISMATCH — computed=%s expected=%s",
                 computed, EXPECTED_HASH)
    return False


def verify_all_py_hashes() -> dict[str, str]:
    """
    Compute SHA256 hashes of all .py files in src/.
    Returns dict of relative_path -> hash.
    Prints a warning summary for visibility.
    """
    src_dir = os.path.join(PROJECT_ROOT, "src")
    hashes = {}

    for root, _dirs, files in os.walk(src_dir):
        for fname in sorted(files):
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, PROJECT_ROOT)
                hashes[rel] = _compute_file_hash(fpath)

    logger.info("INTEGRITY: Computed hashes for %d source files", len(hashes))
    for path, h in sorted(hashes.items()):
        logger.debug("  %s -> %s", path, h[:16])

    return hashes
