import glob

import os

import argparse

import subprocess

from pathlib import Path

import shutil

import sys

import re

import pandas as pd


# # DAMGER: 
# THIS SCRIPT RENAMES DIRECTORIES AND THEIR CONTENT
# BE SURE THAT FILE: map_samples.tsv CONTAINS CORRECT INFO


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
        print(f"Warning: Experiment subdirectory '{main_dir}' does not exist. Skipping...")
        return target_dir
    
    
    with open(tsv_file,'r') as file:

        mapping = {}
        for line in file:
            current, new = line.strip().split('\t')
            mapping[current] = new
        print(mapping)
    

    sample_dirs = glob.glob(os.path.join(main_dir, 'G*'))


    # sample_dirs = glob.glob(os.path.join(main_dir, '*'))  # Get all files and directories
    # regex_pattern =  r'^[A-Z]+\d{6}_([A-Z]+)$'

    # Filter the directories using regex
    #matching_dirs = [d for d in sample_dirs if os.path.isdir(d) and re.match(regex_pattern, os.path.basename(d))]


    used_keys = set()

    for old_sample_path in sample_dirs:
        old_sample_name = os.path.basename(old_sample_path)


        if old_sample_name in mapping:
            new_sample_name = mapping[old_sample_name]
            new_sample_path = os.path.join(main_dir, new_sample_name)

            shutil.move(old_sample_path, new_sample_path)
            print(f"Renamed directory: {old_sample_name} -> {new_sample_name}")

            used_keys.add(old_sample_name)  # Tracking used keys

            for old_file_path in glob.glob(os.path.join(new_sample_path, f"{old_sample_name}*")):

                old_file_name = os.path.basename(old_file_path)
                new_file_name = old_file_name.replace(old_sample_name, new_sample_name)
                new_file_path = os.path.join(new_sample_path, new_file_name)

                shutil.move(old_file_path, new_file_path)
                print(f"Renamed file: {old_file_name} -> {new_file_name}")


    unused_keys = set(mapping.keys()) - used_keys
    if unused_keys:
        print("Warning: The following mappings were not used (directories not found):")
        for unused_key in unused_keys:
            print(f"  - {unused_key}")
                      
    return target_dir



def save_to_csv(output_file:str,
                unique_names: list):
    # Convert set to DataFrame
    df = pd.DataFrame({'Sample_Alias': list(unique_names)})

    # Save DataFrame to CSV
    smaples_aliases = os.path.join(output_file,'sample_aliases.csv')
    df.to_csv(smaples_aliases, index=False)

    return smaples_aliases


# # major problem:
# #  Samples are UNIQUE, can be either obtaiend from S or F or BG,
# #  BUT they are considered as a UNIQUE UNIT of biological data
# # Could occur that a sample fails to have a 16S experiment BUT
# # To have WGS data

def retrieve_sample_alias(
        target_dir : str
                        ): 
    
    e16s_dirs = glob.glob(os.path.join(target_dir,'16_S','*'))
    # # get unique sample alias from 16S and WGS:
    e16s = []
    for sample in e16s_dirs:
        sample = os.path.basename(sample)
        samples_alias = "_".join(sample.split("_")[:3]) 
        e16s.append(samples_alias)
    set_16s = set(e16s)

    ewgs_dirs = glob.glob(os.path.join(target_dir,'Metagenomes','*'))
    ewgs = []
    for sample in ewgs_dirs:
        sample = os.path.basename(sample)
        samples_alias = "_".join(sample.split("_")[:3]) 
        ewgs.append(samples_alias)
    set_wgs = set(ewgs)
    #  create a set for each list

    # Do a union
    union = set_16s.union(set_wgs)
    # Do intersection
    intersection = set_16s.intersection(set_wgs)
    all_samp = list(union)
    print(len(list(union)))

    save_to_csv(output_file=args.file_path,
                unique_names = all_samp
                )
    
    return list(union), list(intersection)




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
    # parser.add_argument(
    #     "-e", "--experiment_type",
    #     help="String defining either 16S or WGS ",
    #     type = str
    # )
    args = parser.parse_args()

    # check_sanity(
    #     tsv_file = args.file_path,
    #     target_dir = args.sample_dir,
    # )

    # sample_dir = first_function(
    #     tsv_file = args.file_path,
    #     target_dir = args.sample_dir,
    #     experiment_type  = args.experiment_type
    #     )

    all,common = retrieve_sample_alias(
        target_dir = args.sample_dir
    )

    # walk_dir(
    #     target_dir=args.sample_dir
    # )