#!/usr/bin/env python3
"""
ena_bulk_download.py

Bulk-download (private) read files from ENA using a table of run accessions
and their FTP file paths, authenticating with your Webin credentials.

INPUT TABLE FORMAT
-------------------
A CSV or TSV file with at least these columns:

    run_accession   fastq_ftp

- run_accession : e.g. ERR9463971
- fastq_ftp     : one or more FTP paths for that run, separated by ';'
                  (this matches the format ENA itself uses in its
                  Run Report / filereport exports). Paths may or may not
                  include the 'ftp://' scheme and may or may not include
                  the host - the script normalises this.

Example row (tab-separated):
    ERR9463971    ftp.dcc-private.ebi.ac.uk/vol1/fastq/ERR946/001/ERR9463971/ERR9463971_1.fastq.gz;ftp.dcc-private.ebi.ac.uk/vol1/fastq/ERR946/001/ERR9463971/ERR9463971_2.fastq.gz

Where to get this table: log into the Webin Portal, open the Run Report,
and export it as CSV/TSV. It will contain the exact private FTP paths for
your own submitted (possibly unpublished) files.

USAGE
-----
    python3 ena_bulk_download.py \\
        --table runs.tsv \\
        --username Webin-XXXXX \\
        --password 'yourpassword' \\
        --outdir /path/to/output \\
        [--threads 4] [--retries 3] [--verify-md5] [--delimiter auto] [--dry-run]

Use --dry-run first on any new table: it checks your credentials once, then
lists every accession/filename/source-URL/destination-path it *would*
download, without touching the network for transfers or writing any files.

Credentials can also be supplied via environment variables instead of the
command line (recommended, avoids password showing in shell history / ps):

    export ENA_WEBIN_USER=Webin-XXXXX
    export ENA_WEBIN_PASS=yourpassword
    python3 ena_bulk_download.py --table runs.tsv --outdir ./data
"""

import argparse
import csv
import ftplib
import hashlib
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse


def parse_args():
    p = argparse.ArgumentParser(
        description="Bulk-download ENA (private) read files listed in a table."
    )
    p.add_argument(
        "-t", "--table", required=True,
        help="Path to CSV/TSV table with columns run_accession and fastq_ftp"
    )
    p.add_argument(
        "-u", "--username", default=os.environ.get("ENA_WEBIN_USER"),
        help="Webin account (e.g. Webin-XXXXX). Falls back to ENA_WEBIN_USER env var."
    )
    p.add_argument(
        "-p", "--password", default=os.environ.get("ENA_WEBIN_PASS"),
        help="Webin password. Falls back to ENA_WEBIN_PASS env var."
    )
    p.add_argument(
        "-o", "--outdir", required=True,
        help="Directory to save downloaded files into"
    )
    p.add_argument(
        "--accession-col", default="run_accession",
        help="Column name holding the run accession (default: run_accession)"
    )
    p.add_argument(
        "--path-col", default="fastq_ftp",
        help="Column name holding ';'-separated FTP paths (default: fastq_ftp)"
    )
    p.add_argument(
        "--delimiter", default="auto",
        help="Table delimiter: 'auto' (sniff), ',' or '\\t' (default: auto)"
    )
    p.add_argument(
        "--threads", type=int, default=4,
        help="Number of parallel downloads (default: 4)"
    )
    p.add_argument(
        "--retries", type=int, default=3,
        help="Retry attempts per file on failure (default: 3)"
    )
    p.add_argument(
        "--verify-md5", action="store_true",
        help="Fetch the .md5 sidecar file (if present) and verify checksum after download"
    )
    p.add_argument(
        "--log-file", default=None,
        help="Optional path to a log file (in addition to console output)"
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Don't download anything. Validate credentials once, then list what "
             "would be downloaded (accession, filename, source URL, destination path)."
    )
    return p.parse_args()


def setup_logging(log_file):
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def sniff_delimiter(table_path, requested):
    if requested != "auto":
        return "\t" if requested in ("\\t", "tab") else requested
    with open(table_path, "r", newline="") as f:
        sample = f.read(4096)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t").delimiter
    except csv.Error:
        return "\t" if "\t" in sample else ","


def normalise_ftp_url(raw_path):
    """Ensure the path has an ftp:// scheme and a host."""
    raw_path = raw_path.strip()
    if not raw_path:
        return None
    if raw_path.startswith("ftp://"):
        return raw_path
    return "ftp://" + raw_path


def read_table(table_path, accession_col, path_col, delimiter):
    jobs = []
    with open(table_path, "r", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if accession_col not in reader.fieldnames or path_col not in reader.fieldnames:
            logging.error(
                "Table must contain columns '%s' and '%s'. Found columns: %s",
                accession_col, path_col, reader.fieldnames
            )
            sys.exit(1)
        for row in reader:
            acc = row[accession_col].strip()
            raw_paths = row[path_col].strip()
            if not acc or not raw_paths:
                continue
            urls = [normalise_ftp_url(p) for p in raw_paths.split(";") if p.strip()]
            for url in urls:
                jobs.append((acc, url))
    return jobs


def check_credentials(host, username, password):
    """Attempt a single login (no file transfer) to confirm credentials/host
    reachability before doing anything else. Returns (ok, error_message)."""
    try:
        ftp = ftplib.FTP(host, timeout=30)
        ftp.login(username, password)
        ftp.quit()
        return True, None
    except Exception as e:
        return False, str(e)


def md5_of_file(path, chunk_size=1024 * 1024):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_remote_md5(url, username, password):
    """Try to fetch the .md5 sidecar file that usually sits next to ENA files."""
    md5_url = url + ".md5"
    parsed = urlparse(md5_url)
    try:
        ftp = ftplib.FTP(parsed.hostname, timeout=30)
        ftp.login(username, password)
        buf = bytearray()
        ftp.retrbinary("RETR " + parsed.path, buf.extend)
        ftp.quit()
        content = buf.decode(errors="ignore").strip()
        return content.split()[0] if content else None
    except Exception:
        return None  # sidecar not available or not needed - not fatal


def download_one(job, username, password, outdir, retries, verify_md5, dry_run=False):
    acc, url = job
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    dest_dir = Path(outdir) / acc
    dest_path = dest_dir / filename

    if dry_run:
        # No network calls, no directory creation - just report the plan.
        note = " (already exists locally)" if dest_path.exists() else ""
        logging.info("[DRY RUN] %s: %s -> %s%s", acc, url, dest_path, note)
        return (acc, filename, "DRY_RUN")

    dest_dir.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and dest_path.stat().st_size > 0:
        logging.info("[%s] %s already exists, skipping download (delete it to re-fetch)", acc, filename)
    else:
        attempt = 0
        succeeded = False
        while attempt < retries:
            attempt += 1
            try:
                logging.info("[%s] Downloading %s (attempt %d/%d)", acc, filename, attempt, retries)
                ftp = ftplib.FTP(parsed.hostname, timeout=60)
                ftp.login(username, password)
                with open(dest_path, "wb") as f:
                    ftp.retrbinary("RETR " + parsed.path, f.write)
                ftp.quit()
                logging.info("[%s] Finished %s", acc, filename)
                succeeded = True
                break
            except Exception as e:
                logging.warning("[%s] Attempt %d failed for %s: %s", acc, attempt, filename, e)
                if dest_path.exists():
                    dest_path.unlink(missing_ok=True)
                time.sleep(2 * attempt)  # simple backoff
        if not succeeded:
            logging.error("[%s] Giving up on %s after %d attempts", acc, filename, retries)
            return (acc, filename, "FAILED")

    if verify_md5:
        remote_md5 = fetch_remote_md5(url, username, password)
        if remote_md5:
            local_md5 = md5_of_file(dest_path)
            if local_md5 == remote_md5:
                logging.info("[%s] MD5 OK for %s", acc, filename)
            else:
                logging.error(
                    "[%s] MD5 MISMATCH for %s (local=%s remote=%s)",
                    acc, filename, local_md5, remote_md5
                )
                return (acc, filename, "MD5_MISMATCH")
        else:
            logging.info("[%s] No remote .md5 found for %s, skipping verification", acc, filename)

    return (acc, filename, "OK")


def main():
    args = parse_args()
    setup_logging(args.log_file)

    if not args.username or not args.password:
        logging.error(
            "Missing credentials. Provide --username/--password or set "
            "ENA_WEBIN_USER / ENA_WEBIN_PASS environment variables."
        )
        sys.exit(1)

    table_path = Path(args.table)
    if not table_path.exists():
        logging.error("Table file not found: %s", table_path)
        sys.exit(1)

    delimiter = sniff_delimiter(table_path, args.delimiter)
    jobs = read_table(table_path, args.accession_col, args.path_col, delimiter)

    if not jobs:
        logging.error("No downloadable file entries found in table.")
        sys.exit(1)

    logging.info("Found %d file(s) to download across accessions.", len(jobs))

    if args.dry_run:
        # Validate credentials once against the host used by the first job,
        # so a bad password is caught immediately instead of per-file later.
        host = urlparse(jobs[0][1]).hostname
        ok, err = check_credentials(host, args.username, args.password)
        if ok:
            logging.info("[DRY RUN] Credentials OK for %s@%s", args.username, host)
        else:
            logging.warning("[DRY RUN] Could not verify credentials against %s: %s", host, err)
        logging.info("[DRY RUN] No files will be downloaded. Listing planned actions:")
    else:
        Path(args.outdir).mkdir(parents=True, exist_ok=True)

    results = []
    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {
            pool.submit(
                download_one, job, args.username, args.password,
                args.outdir, args.retries, args.verify_md5, args.dry_run
            ): job
            for job in jobs
        }
        for future in as_completed(futures):
            results.append(future.result())

    if args.dry_run:
        logging.info("[DRY RUN] %d file(s) would be downloaded. No changes made.", len(results))
        return

    ok = [r for r in results if r[2] == "OK"]
    failed = [r for r in results if r[2] != "OK"]

    logging.info("Done. %d succeeded, %d failed/mismatched.", len(ok), len(failed))
    if failed:
        logging.info("Failed/mismatched files:")
        for acc, filename, status in failed:
            logging.info("  %s / %s -> %s", acc, filename, status)
        sys.exit(2)


if __name__ == "__main__":
    main()
