#!/usr/bin/env python3

from typing import List
import os
import glob
import hashlib
import sys
import argparse
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import subprocess
import json
from ruamel.yaml import YAML
from ena_utils import read_config, get_config_variable, write_config


def main():
    args = parse_args()


    config_file = args.config_file
    data = read_config(config_file)


    project_name = get_config_variable(data, "project_name")
    template_dir = get_config_variable(data, "template_dir")
    metadata_file = get_config_variable(data, "metadata_file")
    submission_type = get_config_variable(data, "submission_type")
    ena_checklist = get_config_variable(data, "ena_checklist")

    samples_xml_path = create_samples_file(
        project_name=project_name,
        metadata_path=metadata_file,
        template_dir=template_dir,
        ena_checklist=ena_checklist
        
    )

    registrationType = None if args.registration_type == "null" else args.registration_type

    samples_receipt_path = register_samples(
        template_dir=template_dir,
        samples_xml_path=samples_xml_path,
        user_password=args.user_password,
        submission_type=submission_type,
        registration_type=registrationType,
        project_name=project_name
    )

    if registrationType:

        write_config(
            config_file=config_file, 
            key="receipt_samples_permanent",
            value=samples_receipt_path
            )
    elif not registrationType:
        
        write_config(
            config_file=config_file, 
            key="receipt_samples_dry_run",
            value=samples_receipt_path
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


def write_config(config_file: str, key: str, value: str,):

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with open(config_file, "r") as file:
            data = yaml.load(file) or {}
    except FileNotFoundError:
        # If the file doesn't exist yet, start with a fresh dictionary
        data = {}

    data[key] = value

    with open(config_file, "w") as file:
        data = yaml.dump(data, file)

    return data


def register_samples(
                samples_xml_path: str,
                template_dir: str,
                user_password: str,
                submission_type: str,
                registration_type: str,
                project_name: str
                ) -> str:

    # Define input XML files
    #set submission type, ADD new metadata (new sample/s), or MODIFY existant metadata (already registered sample/s)
    if submission_type == "ADD":
        print(f'[INFO] Submitting metadata in ADD mode')
        submission_path = os.path.join(
            template_dir,
            "submission_ADD.xml"
        )
    elif submission_type == "MODIFY":
        print(f'[INFO] Submitting metadata in MODIFY mode')
        submission_path = os.path.join(
            template_dir,
            "submission_MOD.xml"
        )
    
    output_path = os.path.join(os.path.dirname(samples_xml_path),
                               f"{project_name}_ena_samples_receipt.xml")
    
    if os.path.exists(output_path):
        raise FileExistsError(f"Sample receipt file '{output_path}' already exists and must not be ovewritten!")

    # --- Preview-only mode ---
    if not registration_type:
        print("[INFO] submission_type is empty. Dry-run mode: returning output path only.")
        return output_path
    
    # --- Validate submission type ---
    normalized = registration_type.lower()
    if normalized in ['y', 'yes']:
        url_ebi_ac_uk = "https://www.ebi.ac.uk/ena/submit/drop-box/submit/"
        print('[STEP0][+] Registering to Permanent partition ..')
        permanent = True

    elif normalized in ['n','no']:
        url_ebi_ac_uk = "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/"
        print('[STEP0][+] Registering to TEST partition ..')
        permanent = False

    else:
        print("[!] Invalid value for --registration_type \n " \
        "--> Use 'y' or 'Yes' or 'yes' for permanent submission \n " \
        "--> Use 'n','No','no' for temporary (Test) submission")
        sys.exit(1)

    # Check all files exist beforehand
    if not os.path.exists(submission_path):
        raise FileNotFoundError(f"Required file not found: {submission_path}")

    # Build the command
    command = [
        "curl",
        "-u", user_password,
        "-F", f"SUBMISSION=@{submission_path}", 
        "-F", f"SAMPLE=@{samples_xml_path}",
        "-F", "LAUNCH=YES",
        "-o", output_path,
        url_ebi_ac_uk
    ]

    # Execute the command
    try:
        subprocess.run(command, check=True, text=True)
        print(f"[+] Samples receipt XML created: {output_path}")

    except subprocess.CalledProcessError as e:
        print(f"[!] Error:", {e.stderr})

    message = receipt_output_handling(output_path)

    if message['success']:
        print(f"[STEP1][+] Samples receipt saved to: {output_path}")

        if permanent:
            print(f"[STEP1][+] Samples registered Permanently")
        else:
            print(f"[STEP1][+] Samples registered Temporarily")
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
    
    soup = BeautifulSoup(content, 'xml')
    receipt = soup.find('RECEIPT')
    success = receipt.get('success', 'false').lower() == 'true'

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

### RETRIEVE XML template
def select_template(template_dir:str, metadata_df:pd.DataFrame, checklist_code: str)-> tuple[dict, str, str]:
    
    assert not metadata_df.empty, f"Input file at {os.path.join(template_dir)} contains no data rows."

    json_file = os.path.join(template_dir,'checklists.json')

    if not os.path.exists(json_file):
        raise FileNotFoundError(f"Missing configuration file: {json_file}")

    with open(json_file, 'r') as f:
        data = json.load(f)

    if checklist_code not in data['checklist_templates']:
        print(f"No {checklist_code} in available templates, please check {json_file} schema")
        sys.exit(1)

    template_name = data['checklist_templates'][checklist_code]
    mapping_dict = data.get(checklist_code)
    
    if not mapping_dict:
        raise ValueError(f"No mapping dictionary found for {checklist_code}")
    
    missing = set(mapping_dict.values()) - set(metadata_df.columns)

    if missing:
        raise ValueError(
            f"Validation Failed. {len(missing)} column(s) not found in "
            f"DataFrame: {', '.join(missing)}"
        )
            
    template_xml_filename = f"{template_name}.xml"
    file_template_xml = os.path.join(template_dir,template_xml_filename)
 
    if not os.path.exists(file_template_xml):
        raise FileNotFoundError(f"Missing xml template file: {file_template_xml}")

    
    return mapping_dict, file_template_xml, template_name


### CREATING SAMPLES XML
def create_samples_file(project_name:str,  metadata_path: str, template_dir: str, ena_checklist: str) -> str:

    metadata_df = load_metadata(metadata_path)

    mapping_dict, template_xml, checklist_code = select_template(template_dir, metadata_df, ena_checklist)
    samples_all = []

    # Create a template for each sample
    for _, row in metadata_df.iterrows():
        row = row.astype(str)
        
        with open(template_xml, 'r') as handler:
            xml_file = handler.read()

            for key,value in mapping_dict.items():
                val = row[value]
                xml_file = xml_file.replace(key,val)
            print(xml_file)
            samples_all += [xml_file]

    samples_all = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<SAMPLE_SET>" + "\n" + \
        "\n".join(samples_all) + "\n" + \
        "</SAMPLE_SET>" + "\n"

    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_{checklist_code}.xml"
    )

    with open(output_path, mode="w") as handle:
        handle.write(samples_all)
    
    print(f"[STEP1][+] Samples XML saved to:    {output_path}")


    return output_path


def load_metadata(metadata_path: str) -> pd.DataFrame:
    
    spreadsheet_file = os.path.abspath(metadata_path)
    base, extension = os.path.splitext(spreadsheet_file)

    if not extension:
        print(f"Error: Path '{metadata_path}' looks like a directory. Please provide a file.")    
        sys.exit(1)

    try:
        if extension in [".xlsx", ".xls"]:
            spreadsheet = pd.read_excel(spreadsheet_file, sheet_name="sample_submission", header=0)
        elif extension == ".csv":
            spreadsheet = pd.read_csv(spreadsheet_file, header=0, sep=",")
        elif extension in [".txt", ".tsv"]:
            spreadsheet = pd.read_csv(spreadsheet_file, header=0, sep="\t")
        else:
            print(f"Error: Unsupported file format '{extension}'")
            sys.exit(1)
    except Exception as e:
        print(f"Error reading the file: {e}")
        sys.exit(1)

    # Use copy() to avoid "SettingWithCopyWarning" later
    # Removing first row if it's a sub-header/example and dropping invalid aliases
    spreadsheet = spreadsheet.iloc[1:].copy()
    spreadsheet = spreadsheet.dropna(subset=["sample_alias"])

    # 4. Date Standardization
    if "collection date" in spreadsheet.columns:
        spreadsheet["collection date"] = pd.to_datetime(spreadsheet["collection date"], errors='coerce')\
            .dt.strftime("%Y-%m-%d")

    return spreadsheet



def parse_args():
    parser = argparse.ArgumentParser("Register sample metadata")
    parser.add_argument("-s", "--config_file", 
                        help="config yaml file containing direcotries for the whole workflow.",
                        type=str
                        )
    parser.add_argument("-x", "--registration_type",
                        help="Registration type: 'y' or 'yes' for permanent; 'n' or 'no' for test. Leave empty for dry run.",
                        type=str,
                        default="null",
                        choices=['y', 'yes', 'n', 'no', "null"]  # Accept only known values
    )
    parser.add_argument("-u", "--user_password",
                        help="User and password for the submission (e.g. user1:password1234).",
                        type=str
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
