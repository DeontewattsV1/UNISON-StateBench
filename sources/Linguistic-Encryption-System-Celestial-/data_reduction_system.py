"""
data_reduction_system.py
========================

This module implements a simple end‑to‑end data reduction pipeline. The goal of
the pipeline is to minimise the amount of data retained by selectively storing
only what is necessary, compressing unique data to shrink its footprint,
eliminating redundant files through deduplication, purging obsolete data via
lifecycle rules and optionally performing edge computation to summarise data
locally before it is sent to a central location.

It supports file-level deduplication, gzip compression, retention cleanup,
and optional CSV/text summarisation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import pandas as pd
except ImportError:
    pd = None


METADATA_FILENAME = "processed_files.json"


def compute_file_hash(path: Path, chunk_size: int = 65536) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def load_metadata(metadata_path: Path) -> Dict[str, Dict[str, str]]:
    if not metadata_path.exists():
        return {}
    with metadata_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_metadata(metadata_path: Path, metadata: Dict[str, Dict[str, str]]) -> None:
    tmp_path = metadata_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    tmp_path.replace(metadata_path)


def compress_file(src: Path, dst: Path) -> None:
    import gzip
    with src.open("rb") as f_in, gzip.open(dst, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def summarise_csv(src: Path) -> Dict[str, Dict[str, float]]:
    if pd is None:
        raise NotImplementedError("Pandas is required for CSV summarisation")
    df = pd.read_csv(src)
    summary: Dict[str, Dict[str, float]] = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if series.empty:
                continue
            summary[col] = {
                "count": float(series.count()),
                "mean": float(series.mean()),
                "min": float(series.min()),
                "max": float(series.max()),
            }
    return summary


def summarise_text(src: Path) -> Dict[str, int]:
    from collections import Counter
    word_counts: Counter[str] = Counter()
    with src.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            words = [w.strip(".,;:-!?\"'()[]{}<>/\\").lower() for w in line.split()]
            word_counts.update(word for word in words if word)
    return dict(word_counts)


def process_file(
    file_path: Path,
    output_dir: Path,
    summary_dir: Optional[Path],
    metadata: Dict[str, Dict[str, str]],
    retention_days: int,
    edge_threshold: int = 10_000_000,
) -> Tuple[bool, Optional[str]]:
    file_hash = compute_file_hash(file_path)
    if file_hash in metadata:
        return False, None

    if summary_dir is not None and file_path.stat().st_size >= edge_threshold:
        summary_data: Optional[Dict] = None
        if file_path.suffix.lower() == ".csv":
            try:
                summary_data = summarise_csv(file_path)
            except Exception as exc:
                print(f"Warning: failed to summarise CSV {file_path}: {exc}. Falling back to compression.")
        elif file_path.suffix.lower() in {".txt", ".log"}:
            summary_data = summarise_text(file_path)

        if summary_data is not None:
            summary_dir.mkdir(parents=True, exist_ok=True)
            summary_file = summary_dir / f"{file_path.stem}_{file_hash[:8]}.summary.json"
            with summary_file.open("w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2)
            metadata[file_hash] = {
                "original_path": str(file_path),
                "processed_time": datetime.utcnow().isoformat(),
                "summary_path": str(summary_file),
                "type": "summary",
            }
            return True, str(summary_file)

    output_dir.mkdir(parents=True, exist_ok=True)
    compressed_path = output_dir / f"{file_path.name}.gz"
    compress_file(file_path, compressed_path)
    metadata[file_hash] = {
        "original_path": str(file_path),
        "processed_time": datetime.utcnow().isoformat(),
        "compressed_path": str(compressed_path),
        "type": "compressed",
    }
    return True, str(compressed_path)


def purge_old_archives(output_dir: Path, metadata: Dict[str, Dict[str, str]], retention_days: int) -> None:
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    remove_keys = []
    for file_hash, info in list(metadata.items()):
        processed_time = datetime.fromisoformat(info["processed_time"])
        if processed_time < cutoff:
            path_key = "compressed_path" if info.get("type") == "compressed" else "summary_path"
            try:
                Path(info[path_key]).unlink(missing_ok=True)
            except Exception as exc:
                print(f"Warning: failed to delete {info[path_key]}: {exc}")
            remove_keys.append(file_hash)
    for key in remove_keys:
        del metadata[key]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deduplicate, compress and summarise incoming files")
    parser.add_argument("--source-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--summary-dir", type=str, default=None)
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--edge-threshold", type=int, default=10_000_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    summary_dir = Path(args.summary_dir) if args.summary_dir else None

    metadata_path = output_dir / METADATA_FILENAME
    metadata = load_metadata(metadata_path)

    processed_count = 0
    for file_path in sorted(source_dir.iterdir()):
        if file_path.is_dir() or file_path.name == METADATA_FILENAME:
            continue
        processed, dest = process_file(
            file_path=file_path,
            output_dir=output_dir,
            summary_dir=summary_dir,
            metadata=metadata,
            retention_days=args.retention_days,
            edge_threshold=args.edge_threshold,
        )
        if processed:
            processed_count += 1
            if dest:
                print(f"Processed {file_path} -> {dest}")
        else:
            print(f"Skipped duplicate: {file_path}")

    purge_old_archives(output_dir, metadata, args.retention_days)
    save_metadata(metadata_path, metadata)
    print(f"Processing complete. {processed_count} new files processed.")


if __name__ == "__main__":
    main()
