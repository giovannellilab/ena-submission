
import re

import os

import argparse

import pandas as pd

import glob



def uploader(
        file_list: list ,
        interactive: bool = False

)-> None:

    #NOTA: ftp will ask for each file confirmation, to disable interactive mode, issue the prompt command or
    # OR use -i flag in ftp command
    #save credentials in netrc file 
    if interactive:
        mput_command =  "mput "+ " ".join(file_list) + "; bye"

    else:

        #mput_command = "set cmd:interactive no; mput " + " ".join(file_list) + "; bye"
        mput_command = "mput -c " + " ".join(file_list) + "; bye"

    ftp_connection = [
        "lftp",
        "webin2.ebi.ac.uk",
        "-e", mput_command
    ]
    
    # try:
    #     subprocess.run(ftp_connection, check=True, text=True)
    #     print(f"First commmand run")

    # except subprocess.CalledProcessError as e:
    #     print(f"Error:", {e.stderr})
    
    return None




def main(
        samples_dir: str,
        experiment_type: str,
        forward_pattern: str

)-> list:

    if not os.path.exists(samples_dir):
        print(f'Error {samples_dir} not correctly inputed')
        return 


    if experiment_type == 'WGS':
        sample_path = os.path.join(samples_dir,'Metagenomes')
    else:
        sample_path = os.path.join(samples_dir,experiment_type)

    all_files = []
    pattern_for = f"{sample_path}/**/{forward_pattern}"

    for filename_for in glob.glob(pattern_for, recursive=True):

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

        # Raise error when there is not exactly one reverse file
        if not os.path.exists(filename_rev):
            raise ValueError(f"[!] Reverse file not found: {filename_rev}")

        all_files.append(filename_for)
        all_files.append(filename_rev)

        size_for = os.path.getsize(filename_for) / (1024 * 1024)
        size_rev = os.path.getsize(filename_rev) / (1024 * 1024)

        print(f" - {filename_for} ---- ({size_for:.2f} MB)")
        print(f" - {filename_rev} ---- ({size_rev:.2f} MB)")


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
        "-f", "--forward_pattern",
        help="Pattern followed in naming the forward sequence files.",
        type=str,
        default="*_1.fq.gz"
    )

    args = parser.parse_args()


    files = main(
        samples_dir = args.sample_dir,
        experiment_type =args.experiment_type,
        forward_pattern=args.forward_pattern
    )

    uploader(
            file_list = files
    )
    