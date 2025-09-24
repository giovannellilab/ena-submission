#!/usr/bin/env python3

from typing import List
import os
import glob
import hashlib
import sys
import argparse
from datetime import datetime
import pandas as pd
import bs4 as bs
import subprocess


def main():
    args = parse_args()

    print(f"[INFO] Using 16S forward pattern {args.forward_pattern_16s}")
    print(f"[INFO] Using WGS forward pattern {args.forward_pattern_wgs}")
    forward_pattern_dict = {
        "16S": args.forward_pattern_16s,
        "WGS": args.forward_pattern_wgs
    }

    run_path = create_run(
        metadata_path=args.metadata_path,
        samples_dir=args.samples_dir,
        template_dir=args.template_dir,
        forward_pattern_dict=forward_pattern_dict,
        experiment_types=args.experiment_types
    )


def create_run(
    metadata_path: str,
    samples_dir: str,
    template_dir: str,
    forward_pattern_dict: dict,
    experiment_types: List[str]
) -> str:

    # Raise error if samples directory does not exist
    if not os.path.exists(samples_dir):
        raise FileNotFoundError(f"{samples_dir} does not exist!")

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]

    template_path = os.path.join(
        template_dir,
        f"run.xml"
    )
    
    run_xml = []

    for experiment_type in experiment_types:

        if experiment_type == '16S':
            exp_dir = '16_S'
        elif experiment_type == 'WGS':
            exp_dir = 'Metagenomes'
        
        forward_pattern = forward_pattern_dict[experiment_type]
        pattern_for = f"{samples_dir}/{exp_dir}/**/{forward_pattern}"

        exclude_dirs = ['weak_failed','unmerged_lanes','ANT23_raw_sequences']
        print(f'----- Experiment type: {experiment_type} ------')

        for filename_for in glob.glob(pattern_for, recursive=True):
            
            name = '_'.join(os.path.basename(filename_for).strip().split('_')[:3])
            if any(excluded in filename_for for excluded in exclude_dirs):
                continue

            # Avoid raw reads
            if "raw" in os.path.basename(filename_for):
                continue

            # Get reverse file from forward one
            # WARNING: may generate errors there are multiple "1" in the pattern
            forward_pattern = forward_pattern.replace("*", "")
            reverse_pattern = forward_pattern.replace("1", "2")
            filename_rev = filename_for.replace(
                forward_pattern,
                reverse_pattern
            )

            # Raise error when reverse file does not exist
            if not os.path.exists(filename_rev):
                raise ValueError(f"[!] Reverse file not found: {filename_rev}")
            else:
                print(filename_for)

            if experiment_type == "WGS":
                # Retrieve checksum (MD5.txt)
                checksum_path = os.path.join(
                    os.path.dirname(filename_for),
                    f"MD5.txt"
                )
                try:
                    if checksum_path:
                        
                        with open(checksum_path, mode="r") as reader:
                            lines = reader.readlines()
                            print(lines)
                            # WARNING: assuming for and rev are in the 1st and 2nd lines
                            hash_for = lines[0].split(" ")[0]
                            hash_rev = lines[1].split(" ")[0]
                    else:
                        raise FileNotFoundError

                except (FileNotFoundError):

                    hash_for = hashlib.md5(open(filename_for, mode="rb").read())\
                        .hexdigest()
                    hash_rev = hashlib.md5(open(filename_rev, mode="rb").read())\
                         .hexdigest()
                    checksum_file = os.path.join(
                        os.path.dirname(filename_for),
                        f'MD5.txt'
                        )
                    with open(checksum_file, mode='w') as writer:
                        writer.write(f"{hash_for} {os.path.basename(filename_for)}\n")
                        writer.write(f"{hash_rev} {os.path.basename(filename_rev)}\n")

            elif experiment_type == "16S":
                # Compute the checksum (MD5)
                hash_for = hashlib.md5(open(filename_for, mode="rb").read())\
                    .hexdigest()
                hash_rev = hashlib.md5(open(filename_rev, mode="rb").read())\
                    .hexdigest()

            else:
                raise NotImplementedError(
                    f"[ERROR] Experiment {experiment_type} is not supported!"
                )

            with open(template_path, mode="r") as handle:
                template_xml = handle.read()

            # WARNING: sample alias is assumed to be the first three fields
            sample_alias = os.path.basename(filename_for)
            sample_alias = "_".join(sample_alias.split("_")[:3])
            exp_alias = f"{project_name}-{sample_alias}-{experiment_type}"

            # Add only the filename instead of the whole path
            filename_for = os.path.basename(filename_for)
            filename_rev = os.path.basename(filename_rev)

            template_xml = template_xml\
                .replace("$$$EXPERIMENT_ALIAS$$$",  exp_alias)\
                .replace("$$$FORWARD_R1_FASTQ$$$",  filename_for)\
                .replace("$$$FORWARD_R1_MD5SUM$$$", hash_for)\
                .replace("$$$REVERSE_R2_FASTQ$$$",  filename_rev)\
                .replace("$$$REVERSE_R2_MD5SUM$$$", hash_rev)

            run_xml += [template_xml]

    run_xml = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<RUN_SET>" + "\n" + \
        "\n".join(run_xml) + "\n" + \
        "</RUN_SET>" + "\n"
    
    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_run.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(run_xml)

    print(f"[STEP1][+] Run XML saved to:         {output_path}")

    return output_path


def parse_args():
    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument("-i", "--metadata_path", 
                        help="Excel file containing the metadata for the sequences.",
                        type=str
                        )
    parser.add_argument("-s", "--samples_dir",
                        help="Directory containing the sequences to submit.",
                        type=str
                        )
    parser.add_argument("-t", "--template_dir",
                        help="Directory containing the templates for the submission.",
                        type=str
                        )
    parser.add_argument("-f", "--forward_pattern_16s",
                        help="Pattern followed in naming the forward sequence files (16S).",
                        type=str,
                        default="*1.fastq.gz")
    parser.add_argument("-w", "--forward_pattern_wgs",
                        help="Pattern followed in naming the forward sequence files (WGS).",
                        type=str,
                        default="*1.fq.gz"
                        )
    parser.add_argument("-e", "--experiment_types",
                        help="String defining either 16S, WGS or both.",
                        type=lambda t: [s.strip() for s in t.split(",")],
                        default=["16S", "WGS"]    
                        )
    parser.add_argument("-x", "--submission_type",
                        help="Submission type: 'y' or 'yes' for permanent; 'n' or 'no' for test. Leave empty for dry run.",
                        type=str,
                        default=None,
                        choices=['y', 'yes', 'n', 'no', None]  # Accept only known values
    )
    parser.add_argument("-u", "--user_password",
                        help="User and password for the submission (e.g. user1:password1234).",
                        type=str
    )
    parser.add_argument("-r", "--recipe",
                        help="XML File obtained from the s01 script.",
                        type=str    
                        )

    return parser.parse_args()


if __name__ == "__main__":
    main()
