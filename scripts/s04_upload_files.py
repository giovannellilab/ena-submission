#!/usr/bin/env python3

import os
import argparse
import pandas as pd
import subprocess
import time
import yaml

def main():
    args = parse_args()

    config_file = args.config_path
    data = read_config(config_file)

    project = data.get("project_name")
    template_dir = data.get("template_dir")
    submission_type = data.get("submission_type")
    metadata_file = data.get("metadata_file")
    readmapping_table_wgs = data.get("readmapping_table_wgs")
    readmapping_table_amp = data.get("readmapping_table_amplicon")
    raw_data_dir_amp = data.get("raw_data_dir_amplicon")
    raw_data_dir_wgs = data.get("raw_data_dir_wgs")


    file_list = gather_files(
        experiment_type = args.experiment_type,
        nested = args.nested,
        readmapping_table_wgs=readmapping_table_wgs,
        readmapping_table_amplicon=readmapping_table_amp,
        raw_data_dir_amplicon=raw_data_dir_amp,
        raw_data_dir_wgs=raw_data_dir_wgs,
    )

    upload_files(
        file_list=file_list,
        username = args.username,
        interactive=args.interactive,
        dry_run=args.dry_run
    )


def read_config(config_file: str):

    with open(config_file, "r") as file:
        data = yaml.load(file, Loader=yaml.SafeLoader)
    return data


def gather_files(experiment_type: str, 
           samples_dir: str,
           mapping_samples:str,
           nested:bool
           )-> list:

    # Raise error if samples directory does not exist
    if samples_dir and not os.path.exists(samples_dir):
        raise FileNotFoundError(f"{samples_dir} does not exist!")
    
    if mapping_samples and not os.path.exists(mapping_samples):
        raise FileNotFoundError(f"{mapping_samples} does not exist!")

    exp_dir = os.path.abspath(samples_dir)
    table_mapping = pd.read_csv(mapping_samples, sep="\t")
    

    required_cols = ["r1","r2","sample"]
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

        r1 = os.path.join(str(base_path),i.forward)
        r2 = os.path.join(str(base_path),i.reverse)
 
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
        f"webin2.ebi.ac.uk",
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
                        help="Username for the submission.",
                        type=str
    )
    parser.add_argument("-i", "--interactive",
                        help="Whether to perform the upload in interactive mode.",
                        type=bool,
                        default=False
    )
    parser.add_argument("--dry_run", action='store_true',
                        help="Execute a dry_run with only printing the command")
    
    return parser.parse_args()


if __name__ == "__main__":
    main()
