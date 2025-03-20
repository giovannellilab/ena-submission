import glob

import os

import argparse

import subprocess

from pathlib import Path

import shutil

import sys


# # DAMGER: 
# THIS SCRIPT RENAMES DIRECTORIES AND THEIR CONTENT
# BE SURE THAT FILE: map_samples.tsv CONTAINS CORRECT INFO


def check_sanity(
    tsv_file : str,
    target_dir : str,
    experiment_type : str  

):

    if not os.path.exists(tsv_file):
        print(f"❌ Error: TSV file '{tsv_file}' not found.")
        sys.exit(1)

    # Ensure the main target directory exists
    if not os.path.exists(target_dir):
        print(f"❌ Error: Target directory '{target_dir}' not found.")
        sys.exit(1)


def first_function(
    tsv_file : str,
    target_dir : str,
    experiment_type : str
)->str:

    if experiment_type == '16S':
        experiment_type = '16_S'
    elif experiment_type == 'WGS':
        experiment_type = 'Metagenomes'


    main_dir = os.path.join(target_dir,experiment_type)
    if not os.path.exists(main_dir):
        print(f"⚠️ Warning: Experiment subdirectory '{main_dir}' does not exist. Skipping...")
        return target_dir
    

    with open(tsv_file,'r') as file:

        mapping = {}
        for line in file:
            current, new = line.strip().split('\t')
            mapping[current] = new


    sample_dirs = glob.glob(os.path.join(main_dir, "G*"))

    for old_sample_path in sample_dirs:
        old_sample_name = os.path.basename(old_sample_path)


        if old_sample_name in mapping:
            new_sample_name = mapping[old_sample_name]
            new_sample_path = os.path.join(main_dir, new_sample_name)

            shutil.move(old_sample_path, new_sample_path)
            print(f"Renamed directory: {old_sample_name} -> {new_sample_name}")


            for old_file_path in glob.glob(os.path.join(new_sample_path, f"{old_sample_name}*")):

                old_file_name = os.path.basename(old_file_path)
                new_file_name = old_file_name.replace(old_sample_name, new_sample_name)
                new_file_path = os.path.join(new_sample_path, new_file_name)

                shutil.move(old_file_path, new_file_path)
                print(f"Renamed file: {old_file_name} -> {new_file_name}")
                      
    return target_dir



def walk_dir( 
    target_dir : str
)->str:
    

    parent_dir = Path(target_dir)
    for path in parent_dir.rglob("*"):  # Iterate through all files and directories
        if path.is_dir():
            print(f"Directory: {path}")
        else:
            print(f"File: {path}")


if __name__ == '__main__':


    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument(
        "-f", "--file_path",
        help="TSV file containing old and new sample names.",
        type=str
    )
    parser.add_argument(
        "-s", "--sample_dir",
        help="Directory containing samples for the submission.",
        type=str
    )
    parser.add_argument(
        "-e", "--experiment_type",
        help="String defining either 16S or WGS ",
        type = str
    )
    args = parser.parse_args()

    sample_dir = first_function(
        tsv_file = args.file_path,
        target_dir = args.sample_dir,
        experiment_type  = args.experiment_type
        )


    # walk_dir(
    #     target_dir=args.sample_dir
    # )