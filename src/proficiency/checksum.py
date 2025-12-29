def main():
    import hashlib
    import json
    import subprocess
    import sys
    from pathlib import Path

    tag = sys.argv[1]
    is_wsd = False
    checksum = {}
    if Path(tag).is_dir():
        for bz2_path in Path(tag).glob("**/*.bz2"):
            if "_wsd" in bz2_path.name:
                is_wsd = True
            with bz2_path.open("rb", buffering=0) as f:
                checksum[bz2_path.name] = hashlib.file_digest(f, "sha256").hexdigest()
    else:
        p = subprocess.run(
            ["gh", "release", "view", tag, "--json", "assets"],
            check=True,
            text=True,
            capture_output=True,
        )
        data = json.loads(p.stdout)
        for asset in data["assets"]:
            if asset["name"].endswith(".bz2"):
                checksum[asset["name"]] = asset["digest"].removeprefix("sha256:")

    out_name = "build/sha256_wsd.json" if is_wsd else "build/sha256.json"
    out_path = Path(out_name)
    if not out_path.parent.is_dir():
        out_path.parent.mkdir()
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(checksum, f, indent=2, sort_keys=True)
