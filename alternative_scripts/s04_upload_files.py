#!/usr/bin/env python3

import os
import argparse
import pandas as pd
import subprocess
import time


def main():
    args = parse_args()

    file_list = gather_files(
        experiment_type = args.experiment_type,
        WGS_samples_dir = args.WGS_samples_dir,
        AMP_samples_dir = args.AMP_samples_dir,
        mapping_WGS = args.mapping_WGS,
        mapping_AMP = args.mapping_AMP
    )

    upload_files(
        file_list=file_list,
        username = args.username,
        interactive=args.interactive,
        dry_run=args.dry_run
    )


def gather_files(experiment_type: str, 
           WGS_samples_dir: str,
           AMP_samples_dir: str,
           mapping_WGS,
           mapping_AMP)-> list:

    # Raise error if samples directory does not exist
    if WGS_samples_dir and not os.path.exists(WGS_samples_dir):
        raise FileNotFoundError(f"{WGS_samples_dir} does not exist!")
    
    if AMP_samples_dir and not os.path.exists(AMP_samples_dir):
        raise FileNotFoundError(f"{AMP_samples_dir} does not exist!")

    if experiment_type == '16S':
        exp_dir = os.path.abspath(AMP_samples_dir)
        table_mapping = pd.read_csv(mapping_AMP, sep="\t")
    elif experiment_type == 'WGS':
        exp_dir = os.path.abspath(WGS_samples_dir)
        table_mapping = pd.read_csv(mapping_WGS, sep="\t")

    all_files = []
    for i in table_mapping.itertuples():
        r1 = os.path.join(str(exp_dir), i.forward)
        r2 = os.path.join(str(exp_dir), i.reverse)
 
        all_files.append(r1)
        all_files.append(r2)

        size_for = os.path.getsize(r1) / (1024 * 1024)
        size_rev = os.path.getsize(r2) / (1024 * 1024)

        print(f"- {r1} ---- ({size_for:.2f} MB)")
        print(f"- {r2} ---- ({size_rev:.2f} MB)")

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
    
    parser.add_argument("-e", "--experiment_type",
                        help="Either 16S or metagenomics.",
                        type=str,
                        choices=["WGS", "16S"]
    )
    parser.add_argument("-w", "--WGS_samples_dir",
                        help="Directory containing the sequences to submit.",
                        type=str
                        )
    parser.add_argument("-a", "--AMP_samples_dir",
                        help="Directory containing the 16S sequences to submit.",
                        type=str
                        )
    parser.add_argument("-m", "--mapping_WGS",
                        help="Table containing rawreads filename (forward and reverse) and sample_alias for WGS",
                        type=str,)
    parser.add_argument("-k", "--mapping_AMP",
                        help="Table containing rawreads filename (forward and reverse) and sample_alias for AMPLICON",
                        type=str,)
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
