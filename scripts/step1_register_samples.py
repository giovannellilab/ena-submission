# ENA submission: FIRST STEP

# This script performs the following steps programmatically:

# 1. Sample registration
#   1.1. Load sample metadata
#   1.2. Create the sample.xml file for registering the samples
#   1.3. Register the samples in ENA according to that metadata

# ---------------------------------------------------------------------------- #

# IMPORTANT! Some considerations must be taken into account:
# 1) Project name is assumed to be the first field in the metadata filename
# 2) Sample alias is assumed to be the first three fields in the sample filename

# ---------------------------------------------------------------------------- #

import os

import argparse

from datetime import datetime

import pandas as pd

import subprocess


def load_metadata(metadata_path: str) -> pd.DataFrame:

    metadata_df = pd.read_excel(
        metadata_path,
        sheet_name="sample_submission"
    )

    # Drop first and last empty rows
    metadata_df = metadata_df\
        .iloc[1:]\
        .dropna(subset=["sample_alias"])

    # Remove time from the date
    metadata_df["collection date"] = \
        pd.to_datetime(metadata_df["collection date"])\
        .dt.strftime("%Y-%m-%d")

    return metadata_df


def create_samples_file(
    metadata_path: str,
    template_dir: str
) -> str:

    metadata_df = load_metadata(metadata_path)

    template_path = os.path.join(
        template_dir,
        "samples.xml"
    )

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
            )

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
    with open(output_path, mode="w") as handle:
        handle.write(samples_all)

    print(f"[STEP1][+] Samples XML created: {output_path}")

    return output_path


def register_samples(
    samples_xml_path: str,
    template_dir: str,
    user_password: str
) -> str:

    # Define input XML files
    submission_path = os.path.join(
        template_dir,
        "submission.xml"
    )

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(samples_xml_path).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(samples_xml_path),
        f"{project_name}_ena_samples_receipt.xml"
    )

    # Build the command
    command = [
        "curl",
        "-u", user_password,
        "-F", f"SUBMISSION=@{submission_path}", 
        "-F", f"SAMPLE=@{samples_xml_path}",
        "-F", "LAUNCH=YES",
        "-o", output_path,
        "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/"
    ]

    # # Execute the command
    # try:
    #     subprocess.run(command, check=True, text=True)
    #     print(f"[+] Samples receipt XML created: {output_path}")

    # except subprocess.CalledProcessError as e:
    #     print(f"[!] Error:", {e.stderr})

    return output_path


if __name__ == "__main__":

    parser = argparse.ArgumentParser("preprocess_sequences")
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
        "-u", "--user_password",
        help="User and password for the submission (e.g. user1:password1234).",
        type=str
    )
    args = parser.parse_args()

    samples_xml_path = create_samples_file(
        metadata_path=args.metadata_path,
        template_dir=args.template_dir
    )

    samples_receipt_path = register_samples(
        samples_xml_path=samples_xml_path,
        template_dir=args.template_dir,
        user_password=args.user_password
    )

    print(f"[STEP1][+] Samples receipt saved to: {samples_receipt_path}")
