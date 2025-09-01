def main():
    import hashlib
    import json
    import sys
    from pathlib import Path

    input_path = Path(sys.argv[1])
    is_wsd = False
    checksum = {}
    for bz2_path in input_path.glob("**/*.bz2"):
        if "_wsd" in bz2_path.name:
            is_wsd = True
        with bz2_path.open("rb", buffering=0) as f:
            checksum[bz2_path.name] = hashlib.file_digest(f, "sha256").hexdigest()

    out_name = "build/sha256_wsd.json" if is_wsd else "build/sha256.json"
    out_path = Path(out_name)
    if not out_path.parent.is_dir():
        out_path.parent.mkdir()
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(checksum, f, indent=2, sort_keys=True)
