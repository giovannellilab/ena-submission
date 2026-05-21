#!/usr/bin/env python3

import argparse
import os
import csv
import subprocess
import bs4 as bs
import sys 
import pandas as pd
import yaml

def main():
    args = parse_args()
    
    config_file = args.config_path
    data = read_config(config_file)


    project_name = data.get("project_name")
    template_dir = data.get("template_dir")
    submission_type = data.get("submission_type")
    metadata_file = data.get("metadata_file")
    readmapping_table_wgs = data.get("readmapping_table_wgs")
    readmapping_table_amp = data.get("readmapping_table_amplicon")
    raw_data_dir_amp = data.get("raw_data_dir_amplicon")
    raw_data_dir_wgs = data.get("raw_data_dir_wgs")


    registrationType = None if args.registration_type == "null" else args.registration_type

    final_receipt_path = register_objects(
        metadata_path=metadata_file,
        project_name=project_name,
        template_dir=template_dir,
        user_password=args.user_password,
        submission_mode=submission_type,
        registration_type=registrationType,
        experiment_type=args.experiment_type

    )

    print(f"[STEP5][+][+][+] Experiments and runs info saved to {final_receipt_path}")


def read_config(config_file: str):

    with open(config_file, "r") as file:
        data = yaml.load(file, Loader=yaml.SafeLoader)
    return data


def register_objects(
    metadata_path: str,
    template_dir: str,
    user_password: str,
    submission_mode: str,
    registration_type: str,
    experiment_type: str,
    project_name: str
    ) -> str:

    #call to load_metadata
    metadata_dir = os.path.dirname(metadata_path)

    # Define paths
    if submission_mode == 1:
        print(f'[INFO] Submitting metadata in ADD mode')
        submission_path = os.path.join(
            template_dir,
            "submission_ADD.xml"
        )
    elif submission_mode == 2:
        print(f'[INFO] Submitting metadata in MODIFY mode')
        submission_path = os.path.join(
            template_dir,
            "submission_MOD.xml"
        )
    experiment_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_experiment_{experiment_type}.xml"
    )
    run_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_run_{experiment_type}.xml"
    )
    output_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_object_receipt_{experiment_type}.xml"
    )

    if os.path.exists(output_path):
        raise FileExistsError(f"Il file '{output_path}' esiste già e non deve essere sovrascritto!")

    # --- Preview-only mode ---
    if not registration_type:
        print("[INFO] Registration_type is empty. Dry-run mode: returning output path only.")
        return output_path
    
    # --- Validate submission type ---
    normalized = registration_type.lower()
    if normalized in ['y', 'yes']:

        url_ebi_ac_uk = "https://www.ebi.ac.uk/ena/submit/drop-box/submit/"
        print('[STEP0][+] Submitting to Permanent partition ..')
        permanent = True

    elif normalized in ['n','no']:

        url_ebi_ac_uk = "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/"
        print('[STEP0][+] Submitted to TEST partition ..')
        permanent = False

    else:
        print("[!] Invalid value for --registration_type \n " \
        "--> Use 'y' or 'Yes' or 'yes' for permanent submission \n " \
        "--> Use 'n','No','no' for temporary (Test) submission")
        sys.exit(1)

    # Check all files exist beforehand
    for path in (submission_path, experiment_path, run_path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required file not found: {path}")

    command = [
        "curl",
        "-u", user_password,
        "-F", f"SUBMISSION=@{submission_path}", 
        "-F", f"EXPERIMENT=@{experiment_path}",
        "-F", f"RUN=@{run_path}",
        "-o", output_path,
        url_ebi_ac_uk
    ]
    # # Execute the command
    try:
        subprocess.run(command, check=True, text=True)
        print(f"[+] Objects receipt XML created: {os.path.basename(output_path)}")

    except subprocess.CalledProcessError as e:
        print(f"[!] Error:", {e.stderr})
    
    message = receipt_output_handling(output_path)
    
    if message['success']:
        print(f"[STEP5][+]  Object receipt saved to: {output_path}")
        if permanent:
            print(f"[STEP5][+][+] Objects registered Permanently")
        else:
            print(f"[STEP5][+] Objects registered Temporarily")
    else:
        print('\n'.join(f'[!] {k} --> {v}' for k, v in message.items()))
        print('Exiting....')
        sys.exit(1)

    return output_path


def receipt_output_handling(receipt_path: str)-> dict:
    """
    Parses a BioSamples receipt XML file using BeautifulSoup and returns a status summary.
    Args:
        file_path (str): Path to the XML file.
    Returns:
        dict: A dictionary with keys:
            - 'success' (bool)
            - 'message' (str)
            - 'errors' (list of str)
            - 'info' (list of str)
    """
    with open(receipt_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    soup = bs.BeautifulSoup(content, 'xml')
    receipt = soup.find('RECEIPT')
    success = receipt.get('success').lower() == 'true'

    errors = [err.text for err in soup.find_all('ERROR')]
    info = [inf.text for inf in soup.find_all('INFO')]

    if success:
        message = "Submission successful. No errors reported."
    else:
        message = "Submission failed. See error messages." if errors else "Submission failed. No specific errors reported."

    info_submission = {
        'success': success,
        'message': message,
        'errors': errors,
        'info': info
    }

    return info_submission



def parse_args():
    parser = argparse.ArgumentParser("Register objects")
    parser.add_argument(
        "-s", "--config_path", 
        help="config yaml file containing direcotries for the whole workflow.",
        type=str
    )
    parser.add_argument(
        "-e", "--experiment_type",
        help="String defining either 16S, WGS or both.",
        type=str,
        choices=["16S","WGS"]
    )
    parser.add_argument(
        "-u", "--user_password",
        help="User and password for the submission (e.g. user1:password1234).",
        type=str
    )
    parser.add_argument(
        "-x", "--registration_type",
        help="Registration type: 'y' or 'yes' for permanent; 'n' or 'no' for test. Leave empty for dry run.",
        type=str,
        default="null",
        choices=['y', 'yes', 'n', 'no', 'null']
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
 