import argparse
import os
import time
import zipfile
from pathlib import Path

import httpx

from generator import generate_documents


def make_archive(source_dir: Path, archive_path: Path) -> Path:
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".html", ".htm", ".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
                zf.write(path, path.relative_to(source_dir))
    return archive_path


def run(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Generating sample documents in {output_dir} ...")
    generate_documents(str(output_dir), count=args.count, fraud_count=args.fraud_count)

    archive = Path(args.archive)
    if not archive.is_absolute():
        archive = Path.cwd() / archive
    archive.parent.mkdir(parents=True, exist_ok=True)

    print(f"[2/4] Zipping generated documents to {archive} ...")
    make_archive(output_dir, archive)

    t0 = time.perf_counter()
    with httpx.Client(timeout=args.timeout) as client:
        print("[3/4] Uploading archive via /api/documents/batch-upload ...")
        with open(archive, "rb") as f:
            files = {"archive": (archive.name, f, "application/zip")}
            resp = client.post(f"{base_url}/api/documents/batch-upload", files=files)
            resp.raise_for_status()
            upload_results = resp.json()

        if args.match:
            print("[4/4] Triggering matching via /api/triplets/match ...")
            m = client.post(f"{base_url}/api/triplets/match")
            m.raise_for_status()
            match_payload = m.json()
        else:
            match_payload = {"message": "Skipped matching", "triplet_ids": []}

        stats = client.get(f"{base_url}/api/stats")
        stats.raise_for_status()
        stats_payload = stats.json()

    elapsed = time.perf_counter() - t0

    ok = [r for r in upload_results if str(r.get("status", "")).upper() != "ERROR"]
    fail = [r for r in upload_results if str(r.get("status", "")).upper() == "ERROR"]

    print("\n=== Demo Setup Summary ===")
    print(f"Processed files: {len(ok)}")
    print(f"Failed files:    {len(fail)}")
    print(f"Matched triplets created: {len(match_payload.get('triplet_ids', []))}")
    print(f"Open fraud alerts: {stats_payload.get('fraud', {}).get('open_alerts', 0)}")
    print(f"Elapsed: {elapsed:.2f}s")

    if fail:
        print("\nFailures:")
        for f in fail[:10]:
            print(f"- {f.get('message')}")

    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate and bulk-upload sample documents for FreightIQ demos")
    p.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    p.add_argument("--output-dir", default="generated", help="Where generated files should be written")
    p.add_argument("--archive", default="generated_upload.zip", help="ZIP archive output path")
    p.add_argument("--count", type=int, default=50, help="Number of triplets to generate")
    p.add_argument("--fraud-count", type=int, default=5, help="Number of anomalous triplets to generate")
    p.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout (seconds)")
    p.add_argument("--match", action="store_true", help="Trigger matching after upload")
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
