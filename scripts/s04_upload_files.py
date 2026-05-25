#!/usr/bin/env python3

import os
import argparse
import pandas as pd
import subprocess
import time
from ruamel.yaml import YAML
from ena_utils import read_config, get_config_variable, write_config


def main():
    args = parse_args()

    config_file = args.config_path
    data = read_config(config_file)

    readmapping_table_wgs = get_config_variable(data,"readmapping_table_wgs")
    readmapping_table_amp = get_config_variable(data,"readmapping_table_amp")
    raw_data_dir_amp = get_config_variable(data,"raw_data_dir_amp")
    raw_data_dir_wgs = get_config_variable(data,"raw_data_dir_wgs")


    file_list = gather_files(
        experiment_type=args.experiment_type,
        nested=args.nested,
        readmapping_table_wgs=readmapping_table_wgs,
        readmapping_table_amp=readmapping_table_amp,
        raw_data_dir_amp=raw_data_dir_amp,
        raw_data_dir_wgs=raw_data_dir_wgs,
    )

    upload_files(
        file_list=file_list,
        username = args.username,
        interactive=args.interactive,
        dry_run=args.dry_run
    )


def read_config(config_file: str):
    yaml = YAML(typ="safe")

    try:
        with open(config_file, "r") as file:
            data = yaml.load(file) or {}
    except FileNotFoundError:
        # If the file doesn't exist yet, start with a fresh dictionary
        data = {}

    with open(config_file, "r") as file:
        data = yaml.load(file)
    return data


def gather_files(
        experiment_type: str, 
        readmapping_table_wgs: str,
        readmapping_table_amp: str,
        raw_data_dir_amp: str,
        raw_data_dir_wgs: str,
        nested: bool
           )-> list:
    
    if experiment_type == "WGS":

        if not readmapping_table_wgs:
            raise ValueError("For WGS experiment, 'readmapping_table_wgs' must be provided in the config.")
        if not raw_data_dir_wgs:
            raise ValueError("For WGS experiment, 'raw_data_dir_wgs' must be provided in the config.")
        else:
            if not os.path.exists(raw_data_dir_wgs):
                raise FileNotFoundError(f"{raw_data_dir_wgs} does not exist!")
            else:
                samples_dir = raw_data_dir_wgs
                mapping_samples = readmapping_table_wgs
            
    elif experiment_type == "16S":

        if not readmapping_table_amp:
            raise ValueError("For 16S experiment, 'readmapping_table_amplicon' must be provided in the config.")
        if not raw_data_dir_amp:
            raise ValueError("For 16S experiment, 'raw_data_dir_amplicon' must be provided in the config.")
        else:
            if not os.path.exists(raw_data_dir_amp):
                raise FileNotFoundError(f"{raw_data_dir_amp} does not exist!")
            else:
                samples_dir = raw_data_dir_amp
                mapping_samples = readmapping_table_amp
    else:
        raise ValueError("Invalid experiment type. Must be either 'WGS' or '16S'.")
    

    exp_dir = os.path.abspath(samples_dir)
    table_mapping = pd.read_csv(mapping_samples, sep="\t")

    required_cols = ["r1","r2","sample_alias"]
    has_sample_id = "sample_id" in table_mapping.columns

    assert all(col in table_mapping.columns for col in required_cols), \
    f"Logic Error: One or more columns from {required_cols} are missing."

    if nested and not has_sample_id:
        raise ValueError("nested_folders=True requires an additional 'sample_id' column.")
    
    if not nested:
        print('\n[INFO] Assuming read files are in the same directory\n')
    
    else:
        print('\n[INFO] Sequence files are nested, proceeding to retrieve...\n')


    all_files = []
    for i in table_mapping.itertuples():

        base_path = os.path.join(exp_dir, str(i.sample_id)) if nested else exp_dir

        r1 = os.path.join(str(base_path),i.r1)
        r2 = os.path.join(str(base_path),i.r2)
 
        # 5. Immediate File Verification
        for f_path in [r1, r2]:
            if not os.path.exists(f_path):
                raise FileNotFoundError(f"Sequence file not found: {f_path}")
            
            all_files.append(f_path)
            size_file = os.path.getsize(f_path) / (1024 * 1024)

            print(f"- {f_path} ---- ({size_file:.2f} MB)")

    return all_files


def upload_files(file_list: list, username: str,  interactive: bool, dry_run)-> None:
    # NOTE: ftp will ask for each file confirmation, to disable interactive
    # mode, issue the prompt command or use -i flag in ftp command. Save
    # credentials in netrc file
    if interactive:
        mput_command =  "mput "+ " ".join(file_list) + "; bye"

    else:
        mput_command = "mput -c " + " ".join(file_list) + "; bye"

    ftp_connection = [
        "lftp",
        f"{username}@webin2.ebi.ac.uk",
        "-e", mput_command
    ]
    
    start_time = time.time() 

    try:
        print('Uploading ...')
        if dry_run:
            print(ftp_connection)
        else:
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


def parse_args():
    parser = argparse.ArgumentParser("Uploading raw sequences")
    parser.add_argument("-s", "--config_path", 
                        help="config yaml file containing direcotries for the whole workflow.",
                        type=str
                        )
    parser.add_argument("-e", "--experiment_type",
                        help="Either 16S or metagenomics.",
                        type=str,
                        choices=["WGS", "16S"]
    )
    parser.add_argument("-n", "--nested",
                        help="If sequences files are nested within each corrispective sample dir names",
                        action='store_true'
                        )
   
    parser.add_argument("-u", "--username",
                        help="User for the submission (e.g. user1).",
                        type=str
    )
    parser.add_argument("-i", "--interactive",
                        help="Whether to perform the upload in interactive mode.",
                        type=bool,
                        default=False
    )
    parser.add_argument("-z", "--dry_run", action='store_true',
                        help="Execute a dry_run with only printing the command.")
    
    return parser.parse_args()


if __name__ == "__main__":
    main()
