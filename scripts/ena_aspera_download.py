#!/usr/bin/env python3
"""
ena_aspera_download.py

Bulk-downloads ENA read files via Aspera (ascli), in parallel.

Accepts TWO possible kinds of input table, and figures out which one you
gave it automatically:

  1. A table that already has run_accession + fastq_ftp columns
     (e.g. straight from the ENA Portal API, or already converted).

  2. A raw Webin Reports Service file report, with id + fileName columns
     (id = run accession, fileName = your original submitted filename).
     In this case, the fastq_ftp path is built for you automatically,
     using ENA's "submitted files" convention:
         vol1/run/<first 6 chars of accession>/<accession>/<fileName>

Either way, only two things matter for the download step: which run each
file belongs to, and its path on the server. Everything else in your file
is ignored.

Prerequisites (must already be done once, outside this script):
  1. aspera-cli installed (`gem install aspera-cli`) and
     `ascli config transferd install` run successfully.
  2. A configured ascli preset, e.g. for public data:
       ascli conf preset update era --url=ssh://fasp.sra.ebi.ac.uk:33001 \\
         --username=era-fasp \\
         --ssh-keys=@ruby:Fasp::Installation.instance.bypass_keys.first \\
         --ts=@json:'{"target_rate_kbps":300000}'

Usage:
    python3 ena_aspera_download.py --table runs.tsv --preset era --outdir ./downloads --threads 4
    python3 ena_aspera_download.py --table runs.tsv --preset era --outdir ./downloads --dry-run
"""

import argparse
import csv
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Known host prefixes to strip from fastq_ftp entries, so the remaining
# path is relative to whatever host the ascli preset already points at.
KNOWN_HOSTS = [
    "ftp.sra.ebi.ac.uk/",
    "ftp.dcc-private.ebi.ac.uk/",
    "fasp.sra.ebi.ac.uk:",
    "ftp.ebi.ac.uk/",
]


def strip_host(path):
    """Remove a known host prefix from a path, if present."""
    path = path.strip()
    for host in KNOWN_HOSTS:
        if path.startswith(host):
            return path[len(host):]
    return path


def prefix6(accession):
    """First 6 characters of a run accession, e.g. ERR14788552 -> ERR147."""
    return accession[:6]


def build_submitted_path(accession, filename, host):
    """Build a full fastq_ftp-style path using ENA's 'submitted files'
    convention: vol1/run/<prefix6>/<accession>/<filename>, no subfolder.
    Use this when filenames do NOT start with the run accession."""
    return f"{host}/vol1/run/{prefix6(accession)}/{accession}/{filename}"


def sniff_delimiter(path):
    """Guess whether a file is comma, tab, or semicolon separated."""
    with open(path, "r", newline="") as f:
        sample = f.read(4096)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
    except csv.Error:
        if "\t" in sample:
            return "\t"
        return ","


def find_column(fieldnames, candidates):
    """Return the actual column name matching one of the candidates
    (case-insensitive), or None if none is found."""
    lower_map = {}
    for name in fieldnames:
        lower_map[name.lower()] = name
    for candidate in candidates:
        if candidate in lower_map:
            return lower_map[candidate]
    return None


def read_jobs(table_path, host):
    """Read the input table and return a list of (accession, relative_path)
    download jobs - one entry per individual file.

    Detects which of three table shapes was given, and handles each:
      1. run_accession + fastq_ftp (already built, possibly ';'-joined)
      2. run_accession + fileName  (one filename column, e.g. Webin report)
      3. run_accession + forward_file + reverse_file (two separate columns
         for paired-end reads, e.g. a submission sample sheet)
    """
    delimiter = sniff_delimiter(table_path)

    with open(table_path, "r", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = reader.fieldnames or []

        acc_col = find_column(fieldnames, ["run_accession", "id", "accession", "run", "run_id"])
        ftp_col = find_column(fieldnames, ["fastq_ftp", "aspera_path", "submitted_ftp"])
        filename_col = find_column(fieldnames, ["filename", "file_name"])
        forward_col = find_column(fieldnames, ["forward_file", "file_1", "fastq_1", "read1"])
        reverse_col = find_column(fieldnames, ["reverse_file", "file_2", "fastq_2", "read2"])

        if acc_col is None:
            raise ValueError(f"Could not find a run accession column in {table_path}. Found columns: {fieldnames}")

        have_ftp = ftp_col is not None
        have_filename = filename_col is not None
        have_forward_reverse = forward_col is not None or reverse_col is not None

        if not have_ftp and not have_filename and not have_forward_reverse:
            raise ValueError(
                f"Could not find fastq_ftp, fileName, or forward_file/reverse_file columns in {table_path}. "
                f"Found columns: {fieldnames}"
            )

        rows = list(reader)

    jobs = []
    for row in rows:
        accession = (row.get(acc_col) or "").strip()
        if not accession:
            continue

        if have_ftp and (row.get(ftp_col) or "").strip():
            # Table already has fastq_ftp - may contain multiple files
            # joined with ';'
            raw_value = row.get(ftp_col).strip()
            for one_path in raw_value.split(";"):
                one_path = one_path.strip()
                if one_path:
                    jobs.append((accession, strip_host(one_path)))

        elif have_filename and (row.get(filename_col) or "").strip():
            filename = row.get(filename_col).strip()
            full_path = build_submitted_path(accession, filename, host)
            jobs.append((accession, strip_host(full_path)))

        elif have_forward_reverse:
            forward_name = (row.get(forward_col) or "").strip() if forward_col else ""
            reverse_name = (row.get(reverse_col) or "").strip() if reverse_col else ""
            if forward_name:
                full_path = build_submitted_path(accession, forward_name, host)
                jobs.append((accession, strip_host(full_path)))
            if reverse_name:
                full_path = build_submitted_path(accession, reverse_name, host)
                jobs.append((accession, strip_host(full_path)))

    if not jobs:
        raise ValueError(f"No downloadable files found in {table_path}")

    return jobs


def download_one(job, preset, outdir, retries, rate_kbps, log_level):
    """Download a single file via ascli, with retries."""
    accession, relative_path = job
    filename = os.path.basename(relative_path)
    dest_dir = Path(outdir) / accession
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    if dest_path.exists() and dest_path.stat().st_size > 0:
        logging.info("[%s] %s already exists, skipping", accession, filename)
        return (accession, filename, "SKIPPED")

    command = [
        "ascli", f"-P{preset}", "server", "download", relative_path,
        f"--to-folder={dest_dir}",
        f"--log-level={log_level}",
    ]
    if rate_kbps:
        command.append(f'--ts=@json:{{"target_rate_kbps":{rate_kbps}}}')

    last_error = None
    for attempt in range(1, retries + 1):
        logging.info("[%s] Downloading %s (attempt %d/%d)", accession, filename, attempt, retries)
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                logging.info("[%s] Done: %s", accession, filename)
                return (accession, filename, "OK")
            last_error = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else f"exit code {result.returncode}"
            logging.warning("[%s] Attempt %d failed for %s: %s", accession, attempt, filename, last_error)
        except FileNotFoundError:
            logging.error("ascli not found on PATH - is aspera-cli installed and activated?")
            return (accession, filename, "FAILED: ascli not found")

        if attempt < retries:
            time.sleep(2 * attempt)

    logging.error("[%s] Giving up on %s after %d attempts: %s", accession, filename, retries, last_error)
    return (accession, filename, f"FAILED: {last_error}")


def run_dry_run(jobs, outdir):
    for accession, relative_path in jobs:
        filename = os.path.basename(relative_path)
        logging.info("[DRY RUN] %s -> %s/%s/%s", accession, outdir, accession, filename)
    logging.info("[DRY RUN] No files downloaded.")


def run_downloads(jobs, preset, outdir, threads, retries, rate_kbps, log_level):
    Path(outdir).mkdir(parents=True, exist_ok=True)

    futures = []
    with ThreadPoolExecutor(max_workers=threads) as pool:
        for job in jobs:
            future = pool.submit(download_one, job, preset, outdir, retries, rate_kbps, log_level)
            futures.append(future)

        results = []
        for future in as_completed(futures):
            results.append(future.result())

    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-l", "--table", required=True, help="Input table: run_accession+fastq_ftp, or id+fileName")
    parser.add_argument("--preset", required=True, help="ascli preset name, e.g. 'era' (passed as -P<preset>)")
    parser.add_argument("-o", "--outdir", required=True, help="Output directory (one subfolder per accession)")
    parser.add_argument("-t", "--threads", type=int, default=4, help="Parallel downloads (default: 4)")
    parser.add_argument("-r", "--retries", type=int, default=3, help="Retries per file (default: 3)")
    parser.add_argument("--host", default="ftp.sra.ebi.ac.uk",
                         help="Host to use when building paths from id+fileName (default: ftp.sra.ebi.ac.uk)")
    parser.add_argument("--rate-kbps", type=int, default=None, help="Optional per-transfer rate cap in kbps")
    parser.add_argument("--log-level", default="info", choices=["error", "warn", "info", "debug"],
                         help="ascli's own log verbosity (default: info)")
    parser.add_argument("--dry-run", action="store_true", help="List planned downloads without transferring")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    jobs = read_jobs(args.table, args.host)
    logging.info("Found %d file(s) to download across accessions.", len(jobs))

    if args.dry_run:
        run_dry_run(jobs, args.outdir)
        return

    results = run_downloads(jobs, args.preset, args.outdir, args.threads, args.retries, args.rate_kbps, args.log_level)

    ok_results = []
    failed_results = []
    for r in results:
        if r[2] in ("OK", "SKIPPED"):
            ok_results.append(r)
        else:
            failed_results.append(r)

    logging.info("Done. %d succeeded/skipped, %d failed.", len(ok_results), len(failed_results))
    if failed_results:
        logging.info("Failed files:")
        for accession, filename, status in failed_results:
            logging.info("  %s / %s -> %s", accession, filename, status)
        sys.exit(2)


if __name__ == "__main__":
    main()
