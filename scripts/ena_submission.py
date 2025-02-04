# ENA submission script

# This script performs the following steps programmatically:

# 1. Sample registration
#   1.1. Load sample metadata
#   1.2. Create the sample.xml file for registering the samples
#   1.3. Register the samples in ENA according to that metadata

# 2. Experiment registration
# 2.1. Parse the receipt after sample registration
# 2.2. Register the experiments according to that information

# 3. Run registration
# 3.1 iterate through sample directories for computing checksums
# 3.2 Register the runs according to the information

# ---------------------------------------------------------------------------- #

# IMPORTANT! Some considerations must be taken into account:
# Project name is assumed to be the first field in the metadata filename
# Sample alias is assumed to be the first three fields in the sample filename

# ---------------------------------------------------------------------------- #

import re

import os

import glob

import hashlib

import argparse

import pandas as pd

import bs4 as bs

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
    #     print(f"Response successfully written to {output_path}")

    # except subprocess.CalledProcessError as e:
    #     print(f"Error:", {e.stderr})

    return output_path


def parse_samples_receipt(
    receipt_path: str,
    metadata_path: str
) -> pd.DataFrame:

    # Programmatically assign study ID
    metadata_df = load_metadata(metadata_path)

    # Load receipt
    with open(receipt_path, mode="r") as handle:
        xml_data = bs.BeautifulSoup(handle, "xml")

    data_df = []

    for sample in xml_data.find_all("SAMPLE"):

        alias = sample.get("alias")
        title = sample.get("accession")
        ext_id_element = sample.find("EXT_ID")
        ext_id = ext_id_element.get("accession")

        study_id = metadata_df[metadata_df["sample_alias"] == alias]\
            ["project name"]\
            .values[0]

        row = pd.Series({
            "project_id": study_id,
            "sample_alias": alias,
            "sample_accession": title,
            "biosample_id": ext_id
        }).to_frame().T

        data_df.append(row)

    return pd.concat(data_df)


def create_experiment(
    receipt_path: str,
    metadata_path: str,
    template_dir: str,
    experiment_type: str
) -> str:

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]

    template_path = os.path.join(
        template_dir,
        f"experiment_{experiment_type}.xml"
    )

    receipt_df = parse_samples_receipt(
        receipt_path=receipt_path,
        metadata_path=metadata_path
    )

    experiment_xml = []

    for _, row in receipt_df.iterrows():
        row = row.astype(str)

        with open(template_path, mode="r") as handle:
            template_xml = handle.read()

        exp_alias = f"{project_name}-{row['sample_alias']}-{experiment_type}"

        template_xml = template_xml\
            .replace("$$$STUDY_ID$$$", row["project_id"])\
            .replace("$$$EXPERIMENT_ALIAS$$$", exp_alias)\
            .replace("$$$SAMPLE_ACCESSION$$$", row["sample_accession"])

        experiment_xml += [template_xml]

    experiment_xml = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<EXPERIMENT_SET>" + "\n" + \
        "\n".join(experiment_xml) + "\n" + \
        "</EXPERIMENT_SET>" + "\n"

    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_experiment.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(experiment_xml)

    return output_path


def create_run(
    samples_dir: str,
    metadata_path: str,
    template_dir: str,
    experiment_type: str,
    file_pattern: str
) -> str:

    # Raise error if samples directory does not exist
    if not os.path.exists(samples_dir):
        raise FileNotFoundError(f"{samples_dir} does not exist!")

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]

    template_path = os.path.join(
        template_dir,
        f"run_{experiment_type}.xml"
    )

    run_xml = []

    pattern_for = f"{samples_dir}/**/{file_pattern}"

    for filename_for in glob.glob(pattern_for, recursive=True):

        # Avoid raw reads
        if "raw" in filename_for:
            continue

        # Get reverse file from forward one
        # WARNING: may generate errors there are multiple "1" in the pattern
        pattern_rev = f"{samples_dir}/**/{file_pattern.replace('1', '2')}"
        filename_rev = glob.glob(pattern_rev, recursive=True)

        # Raise error when there is not exactly one reverse file
        if len(filename_rev) != 1:
            raise ValueError(f"Found {len(filename_rev)} reverse files!")

        filename_rev = filename_rev[0]

        # Compute the checksum (MD5)
        hash_for = hashlib.md5(open(filename_for, mode="rb").read()).hexdigest()
        hash_rev = hashlib.md5(open(filename_rev, mode="rb").read()).hexdigest()

        with open(template_path, mode="r") as handle:
            template_xml = handle.read()

        # WARNING: sample alias is assumed to be the first three fields
        sample_alias = os.path.basename(filename_for)
        sample_alias = "_".join(sample_alias.split("_")[:3])
        exp_alias = f"{project_name}-{sample_alias}-{experiment_type}"

        template_xml = template_xml\
            .replace("$$$EXPERIMENT_ALIAS$$$",  exp_alias)\
            .replace("$$$FORWARD_R1_FASTQ$$$",  filename_for)\
            .replace("$$$FORWARD_R1_MD5SUM$$$", hash_for)\
            .replace("$$$REVERSE_R2_FASTQ$$$",  filename_rev)\
            .replace("$$$REVERSE_R2_MD5SUM$$$", hash_rev)

        run_xml += [template_xml]

    run_xml = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<RUN_SET>" + "\n" + \
        "\n".join(run_xml) + "\n" + \
        "</RUN_SET>" + "\n"

    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_run_{experiment_type}.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(run_xml)

    return output_path


if __name__ == "__main__":

    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument(
        "-i", "--metadata_path",
        help="Excel file containing the metadata for the sequences.",
        type=str
    )
    parser.add_argument(
        "-s", "--samples_dir",
        help="Directory containing the sequences to submit.",
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
        "-f", "--file_pattern",
        help="Pattern followed in naming the forward sequence files.",
        type=str,
        default="*_1.fastq.gz"
    )
    args = parser.parse_args()

    samples_xml_path = create_samples_file(
        metadata_path=args.metadata_path,
        template_dir=args.template_dir
    )

    receipt_path = register_samples(
        samples_xml_path=samples_xml_path,
        template_dir=args.template_dir,
        user_password=args.user_password
    )

    experiment_path = create_experiment(
        receipt_path=receipt_path,
        metadata_path=args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type
    )

    run_path = create_run(
        samples_dir=args.samples_dir,
        metadata_path=args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type,
        file_pattern=args.file_pattern
    )

    print(f"[SUCCESS] Run XML file saved to {run_path}")
