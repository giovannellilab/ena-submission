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

    samples_xml_path = create_samples_file(
        metadata_path=args.metadata_path,
        template_dir=args.template_dir
    )

    registrationType = None if args.registration_type == "null" else args.registration_type

    samples_receipt_path = register_samples(
        samples_xml_path=samples_xml_path,
        template_dir=args.template_dir,
        user_password=args.user_password,
        registration_type=registrationType
    )


def register_samples(samples_xml_path: str,template_dir: str,user_password: str,registration_type: str) -> str:
    # Define input XML files
    submission_path = os.path.join(template_dir, "submission.xml")

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(samples_xml_path).split("_")[0]
    
    output_path = os.path.join(os.path.dirname(samples_xml_path),
                               f"{project_name}_ena_samples_receipt.xml")
    
    if os.path.exists(output_path):
        raise FileExistsError(f"Il file '{output_path}' esiste già e non deve essere sovrascritto!")

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
    
    soup = bs.BeautifulSoup(content, 'xml')
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


### CREATING SAMPLES XML
def create_samples_file( metadata_path: str, template_dir: str) -> str:
    metadata_df = load_metadata(metadata_path)

    template_path = os.path.join(template_dir, "samples.xml")

    samples_all = []

    # Create a template for each sample
    for _, row in metadata_df.iterrows():

        # Avoid errors while formatting numbers
        row = row.astype(str)

        with open(template_path, mode="r") as handle:
            template_xml = handle.read()

        template_xml = template_xml\
            .replace("$$$SAMPLE_TITLE$$$", row["sample_title"])\
            .replace("$$$SAMPLE_ALIAS$$$", row["sample_alias"])\
            .replace("$$$ENV_TAX_ID$$$", row["tax_id"])\
            .replace("$$$ENV_SCI_NAME$$$", row["scientific_name"])\
            .replace("$$$PROJECT_NAME$$$", row["project name"])\
            .replace("$$$COLLECTION_DATE$$$", row["collection date"])\
            .replace("$$$LATITUDE$$$", row["geographic location (latitude)"])\
            .replace("$$$LONGITUDE$$$", row["geographic location (longitude)"])\
            .replace(
                "$$$ENV_BROAD$$$",
                row["broad-scale environmental context"]
            )\
            .replace("$$$ENV_LOCAL$$$", row["local environmental context"])\
            .replace("$$$ENV_MEDIUM$$$", row["environmental medium"])\
            .replace("$$$ELEVATION$$$", row["elevation"])\
            .replace(
                "$$$LOC$$$",
                row["geographic location (country and/or sea)"]
            )\
            .replace(
                "$$$REGLOC$$$",
                row["geographic location (region and locality)"]
            )\
            .replace("$$$DEPTH$$$", row["depth"])

        samples_all += [template_xml]

    samples_all = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<SAMPLE_SET>" + "\n" + \
        "\n".join(samples_all) + "\n" + \
        "</SAMPLE_SET>" + "\n"

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_samples.xml"
    )

    if os.path.exists(output_path):
        raise FileExistsError(f"Il file '{output_path}' esiste già!")

    with open(output_path, mode="w") as handle:
        handle.write(samples_all)

    print(f"[STEP1][+] Samples XML saved to:     {output_path}")

    return output_path


def load_metadata(metadata_path: str) -> pd.DataFrame:
    metadata_df = pd.read_excel(metadata_path, sheet_name="sample_submission")

    # Drop first and last empty rows
    metadata_df = metadata_df.iloc[1:].dropna(subset=["sample_alias"])

    # Remove time from the date
    metadata_df["collection date"] = pd.to_datetime(metadata_df["collection date"])\
        .dt.strftime("%Y-%m-%d")

    return metadata_df


def parse_args():
    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument("-i", "--metadata_path", 
                        help="Excel file containing the metadata for the sequences.",
                        type=str
                        )
    # parser.add_argument("-s", "--samples_dir",
    #                     help="Directory containing the sequences to submit.",
    #                     type=str
    #                     )
    parser.add_argument("-t", "--template_dir",
                        help="Directory containing the templates for the submission.",
                        type=str
                        )
    # parser.add_argument("-f", "--forward_pattern_16s",
    #                     help="Pattern followed in naming the forward sequence files (16S).",
    #                     type=str,
    #                     default="*1.fastq.gz")
    # parser.add_argument("-w", "--forward_pattern_wgs",
    #                     help="Pattern followed in naming the forward sequence files (WGS).",
    #                     type=str,
    #                     default="*1.fq.gz"
    #                     )
    # parser.add_argument("-e", "--experiment_types",
    #                     help="String defining either 16S, WGS or both.",
    #                     type=lambda t: [s.strip() for s in t.split(",")],
    #                     default=["16S", "WGS"]    
    #                     )
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
