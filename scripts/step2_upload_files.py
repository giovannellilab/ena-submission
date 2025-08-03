# ENA submission: STEP 2

# This script performs the following steps programmatically:

# 1. Sample files upload

# ---------------------------------------------------------------------------- #

# IMPORTANT! Some considerations must be taken into account:
# 1) The file pattern for forward reads must contain just one "1"

# ---------------------------------------------------------------------------- #

import os

import re

import argparse

import pandas as pd

import glob

import subprocess

import time

import sys

def check_sanity(
    tsv_file : str,
    target_dir : str,
):
    
    template_dir = os.path.dirname(tsv_file)

    available_files = [f for f in os.listdir(template_dir) 
                       if os.path.isfile(os.path.join(template_dir, f))
                        ]
    
    if not os.path.exists(tsv_file):
        print(f"Error: TSV file '{tsv_file}' not found.")

        if available_files:
            print("Did you mean one of these files?")
            for file in sorted(available_files):
                print(f"  - {file}")
        else:
            print("No files found in the target directory.")

        sys.exit(1)

    if not os.path.exists(target_dir):
        print(f"Error: Target directory '{target_dir}' not found.")
        sys.exit(1)



def exclude_samples(
   metadata_path: str,
   file: str
)-> list:
    
    exclude_list = []

    if not file:
        print('No metadata')
        return exclude_list
    
    else:
        exclusion_file = os.path.join(
            os.path.dirname(metadata_path),
            file
            )
    
        if not os.path.exists(exclusion_file):
            print(f'Error {exclusion_file} does not exist \n \
                no sample will be excluded')
            return exclude_list
        else:

            with open(exclusion_file,'r') as reader:
                for line in reader:
                    line = line.strip('\n')
                    exclude_list.append(line)
    
    return exclude_list


def upload_files(
    file_list: list ,
    interactive: bool = False
)-> None:

    # NOTE: ftp will ask for each file confirmation, to disable interactive
    # mode, issue the prompt command or use -i flag in ftp command. Save
    # credentials in netrc file
    if interactive:
        mput_command =  "mput "+ " ".join(file_list) + "; bye"

    else:
        mput_command = "mput -c " + " ".join(file_list) + "; bye"

    ftp_connection = [
        "lftp",
        "webin2.ebi.ac.uk",
        "-e", mput_command
    ]
    
    start_time = time.time() 

    try:
        print('Uploading ...')
        subprocess.run(ftp_connection, check=True, text=True)
        print(f"First commmand run")

    except subprocess.CalledProcessError as e:
        print(f"Error:", {e.stderr})

    end_time = time.time()  # Record end time
    elapsed_time = end_time - start_time  # Compute duration

    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = elapsed_time % 60

    print(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    print(f"End Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
    print(f"Total Duration: {hours}h {minutes}m {seconds:.2f}s")
    
    return None


def main(
    samples_dir: str,
    metadata_path: str,
    experiment_type: str,
    forward_pattern_dict: dict
)-> list:

    if not os.path.exists(samples_dir):
        print(f'Error {samples_dir} not correctly inputed')
        return 

    if experiment_type == 'WGS':
        sample_path = os.path.join(samples_dir,'Metagenomes')
    elif experiment_type == '16S':
        sample_path = os.path.join(samples_dir,'16_S')

    forward_pattern = forward_pattern_dict[experiment_type]

    all_files = []
    pattern_for = f"{sample_path}/**/{forward_pattern}"


    # # # provding a list of directories to be excluded
    # # # from a text file
    
    exclude_dirs = exclude_samples(
        metadata_path=metadata_path,
        file=args.exclude_dirs
        )
    exclude_dirs = ['unmerged_lanes']
    excluded = []
    for i,filename_for in enumerate(glob.glob(pattern_for, recursive=True)):
        
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
        # excluding specifc samples and files
        if any(excluded in filename_for for excluded in exclude_dirs):
            excluded.append(filename_for)
            excluded.append(filename_rev)
            continue 

        # Raise error when there is not exactly one reverse file
        if not os.path.exists(filename_rev):
            raise ValueError(f"[!] Reverse file not found: {filename_rev}")

        all_files.append(filename_for)
        all_files.append(filename_rev)

        size_for = os.path.getsize(filename_for) / (1024 * 1024)
        size_rev = os.path.getsize(filename_rev) / (1024 * 1024)


        print(f"- {filename_for} ---- ({size_for:.2f} MB)")
        print(f"- {filename_rev} ---- ({size_rev:.2f} MB)")

    if excluded:
        print(f'\n ----Excluded files----')
        print('\n'.join(f'{ex} -- excluded' for ex in excluded))
        print('\n')

    return all_files


if __name__ == "__main__":

    parser = argparse.ArgumentParser("Uploading raw sequences")
    parser.add_argument(
        "-i", "--metadata_path",
        help="Excel file containing the metadata for the sequences.",
        type=str
    )
    parser.add_argument(
        "-t", "--template_dir",
        help="Directory containing the templates for the submission.",
        type=str
    )
    parser.add_argument(
        "-e", "--experiment_type",
        help="Either 16S or metagenomics.",
        type=str
    )
    parser.add_argument(
        "-u", "--user_password",
        help="User and password for the submission (e.g. user1:password1234).",
        type=str
    )
    parser.add_argument(
        "-s", "--sample_dir",
        help = "Directory containing sample subdirectories for the submisssion",
        type=str
    )
    parser.add_argument(
        "-f", "--forward_pattern_16s",
        help="Pattern followed in naming the forward sequence files (16S).",
        type=str,
        default="*1.fastq.gz"
    )
    parser.add_argument(
        "-w", "--forward_pattern_wgs",
        help="Pattern followed in naming the forward sequence files (WGS).",
        type=str,
        default="*1.fq.gz"
    )
    parser.add_argument(
        "-a", "--interactive",
        help="Whether to perform the upload in interactive mode.",
        type=bool,
        default=False
    )
    parser.add_argument(
        "-z", "--exclude_dirs",
        help="Whether to exclude specific files.",
        type=str,
    )
    args = parser.parse_args()

    print(f"[INFO] Using 16S forward pattern {args.forward_pattern_16s}")
    print(f"[INFO] Using WGS forward pattern {args.forward_pattern_wgs}")
    forward_pattern_dict = {
        "16S": args.forward_pattern_16s,
        "WGS": args.forward_pattern_wgs
    }
    file_list = main(
        samples_dir=args.sample_dir,
        metadata_path=args.metadata_path,
        experiment_type=args.experiment_type,
        forward_pattern_dict=forward_pattern_dict
    )
    upload_files(
        file_list=file_list,
        interactive=args.interactive
    )
