# ENA submission: STEP 1

# This script performs the following steps programmatically:

# 1. Sample registration
#   1.1. Load sample metadata
#   1.2. Create the sample.xml file for registering the samples
#   1.3. Register the samples in ENA according to that metadata

# 2. Experiment and run metadata retrieval
#   2.1 Iterate through sample directories for computing checksums
#   2.2 Create experiment and run XML files that will be used in STEP 3

# NOTE: the final registration of experiments and runs will be done in STEP 3

# ---------------------------------------------------------------------------- #

# IMPORTANT! Some considerations must be taken into account:
# 1) Project name is assumed to be the first field in the metadata filename
# 2) Sample alias is assumed to be the first three fields in the sample filename
# 3) The file pattern for forward reads must contain just one "1"

# ---------------------------------------------------------------------------- #

from typing import List

import os

import glob

import hashlib

import argparse

from datetime import datetime

import pandas as pd

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

    print(f"[STEP1][+] Samples XML saved to:     {output_path}")

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

    print(f"[STEP1][+] Registering samples...")

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
    try:
        subprocess.run(command, check=True, text=True)
        print(f"[+] Samples receipt XML created: {output_path}")

    except subprocess.CalledProcessError as e:
        print(f"[!] Error:", {e.stderr})

    print(f"[STEP1][+] Samples receipt saved to: {output_path}")

    return output_path


def parse_samples_receipt(
    samples_receipt_path: str,
    metadata_path: str
) -> pd.DataFrame:

    # Programmatically assign study ID
    metadata_df = load_metadata(metadata_path)

    # Load receipt
    with open(samples_receipt_path, mode="r") as handle:
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
    samples_receipt_path: str,
    metadata_path: str,
    samples_dir: str,
    template_dir: str,
    forward_pattern_dict: dict,
    experiment_types: List[str]
) -> str:

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]

    experiment_xml = []

    for experiment_type in experiment_types:

        template_path = os.path.join(
            template_dir,
            f"experiment_{experiment_type}.xml"
        )

        receipt_df = parse_samples_receipt(
            samples_receipt_path=samples_receipt_path,
            metadata_path=metadata_path
        )
        print(receipt_df)
        for _, row in receipt_df.iterrows():
            row = row.astype(str)

            with open(template_path, mode="r") as handle:
                template_xml = handle.read()

            sample_alias = row["sample_alias"]

            # Modify since WGS folders are named Metagenomes
            if experiment_type == "16S":
                experiment_dir = "16_S"
                sample_alias_dir = sample_alias
                #forward_pattern = "*_1.fastq.gz"

            elif experiment_type == "WGS":
                experiment_dir = "Metagenomes"
                #sample_alias_dir = sample_alias
                sample_alias_dir = sample_alias
                #forward_pattern = "*_1.fq.gz"
      
            forward_pattern = forward_pattern_dict[experiment_type]

            sample_pattern = os.path.join(
                samples_dir,
                experiment_dir,
                f"{sample_alias_dir}/{sample_alias_dir}{forward_pattern}"
            )
            print('Check:',sample_pattern)
            sample_files = glob.glob(sample_pattern, recursive=False)
            print(sample_files)

            if not len(sample_files):
                print(f"[WARNING] Sample file for {sample_alias_dir} not found!")
                print(sample_files)
                continue
            
            exp_alias = f"{project_name}-{sample_alias}-{experiment_type}"

            template_xml = template_xml\
                .replace("$$$STUDY_ID$$$", row["project_id"])\
                .replace("$$$EXPERIMENT_ALIAS$$$", exp_alias)\
                .replace("$$$EXPERIMENT_TITLE$$$", exp_alias)\
                .replace("$$$SAMPLE_ACCESSION$$$", row["sample_accession"])\
                .replace("$$$YEAR$$$", str(datetime.now().year))

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

    print(f"[STEP1][+] Experiment XML saved to:  {output_path}")

    return output_path


def create_run(
    metadata_path: str,
    samples_dir: str,
    template_dir: str,
    forward_pattern_dict: dict,
    experiment_types: List[str]
) -> str:

    # Raise error if samples directory does not exist
    if not os.path.exists(samples_dir):
        raise FileNotFoundError(f"{samples_dir} does not exist!")

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]

    template_path = os.path.join(
        template_dir,
        f"run.xml"
    )

    run_xml = []

    for experiment_type in experiment_types:

        if experiment_type == '16S':
            exp_dir = '16_S'
        elif experiment_type == 'WGS':
            exp_dir = 'Metagenomes'

        forward_pattern = forward_pattern_dict[experiment_type]
        pattern_for = f"{samples_dir}{exp_dir}/**/{forward_pattern}"

        exclude_dirs = ['BP2_220829_F_EW_lanes','BS_220902_F_EW_lanes']

        for filename_for in glob.glob(pattern_for, recursive=True):
            print(filename_for)

            if any(excluded in filename_for for excluded in exclude_dirs):
                continue

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

            # Raise error when reverse file does not exist
            if not os.path.exists(filename_rev):
                raise ValueError(f"[!] Reverse file not found: {filename_rev}")

            if experiment_type == "WGS":
                # Retrieve checksum (MD5.txt)
                checksum_path = os.path.join(
                    os.path.dirname(filename_for),
                    "MD5.txt"
                )

                with open(checksum_path, mode="r") as reader:
                    lines = reader.readlines()
                    print(lines)
                    # WARNING: assuming for and rev are in the 1st and 2nd lines
                    hash_for = lines[0].split(" ")[0]
                    hash_rev = lines[1].split(" ")[0]

            elif experiment_type == "16S":
                # Compute the checksum (MD5)
                hash_for = hashlib.md5(open(filename_for, mode="rb").read())\
                    .hexdigest()
                hash_rev = hashlib.md5(open(filename_rev, mode="rb").read())\
                    .hexdigest()

            else:
                raise NotImplementedError(
                    f"[ERROR] Experiment {experiment_type} is not supported!"
                )

            with open(template_path, mode="r") as handle:
                template_xml = handle.read()

            # WARNING: sample alias is assumed to be the first three fields
            sample_alias = os.path.basename(filename_for)
            sample_alias = "_".join(sample_alias.split("_")[:3])
            exp_alias = f"{project_name}-{sample_alias}-{experiment_type}"

            # Add only the filename instead of the whole path
            filename_for = os.path.basename(filename_for)
            filename_rev = os.path.basename(filename_rev)

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
        f"{project_name}_ena_run.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(run_xml)

    print(f"[STEP1][+] Run XML saved to:         {output_path}")

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
        "-f", "--forward_pattern_16s",
        help="Pattern followed in naming the forward sequence files (16S).",
        type=str,
        default="*_1.fastq.gz"
    )
    parser.add_argument(
        "-w", "--forward_pattern_wgs",
        help="Pattern followed in naming the forward sequence files (WGS).",
        type=str,
        default="*_1.fq.gz"
    )
    parser.add_argument(
        "-e", "--experiment_types",
        help="String defining either 16S, WGS or both.",
        type=lambda t: [s.strip() for s in t.split(",")],
        default=["16S", "WGS"]    
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

    print(f"[INFO] Using 16S forward pattern {args.forward_pattern_16s}")
    print(f"[INFO] Using WGS forward pattern {args.forward_pattern_wgs}")
    forward_pattern_dict = {
        "16S": args.forward_pattern_16s,
        "WGS": args.forward_pattern_wgs
    }

    experiment_path = create_experiment(
        samples_receipt_path=samples_receipt_path,
        metadata_path=args.metadata_path,
        samples_dir=args.samples_dir,
        template_dir=args.template_dir,
        forward_pattern_dict=forward_pattern_dict,
        experiment_types=args.experiment_types
    )

    run_path = create_run(
        metadata_path=args.metadata_path,
        samples_dir=args.samples_dir,
        template_dir=args.template_dir,
        forward_pattern_dict=forward_pattern_dict,
        experiment_types=args.experiment_types
    )
