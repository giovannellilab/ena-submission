# ENA submission: STEP 3

# This script performs the following steps programmatically:

# 1. Experiment and run registration

# ---------------------------------------------------------------------------- #

# IMPORTANT! Some considerations must be taken into account:
# 1) Project name is assumed to be the first field in the metadata filename
# 2) Sample alias is assumed to be the first three fields in the sample filename

# ---------------------------------------------------------------------------- #

import os

import argparse

import subprocess


def register_objects(
    metadata_path: str,
    template_dir: str,
    experiment_type: str,
    user_password: str
) -> str:

    project_name = os.path.basename(metadata_path).split("_")[0]
    metadata_dir = os.path.dirname(metadata_path)

    # Define paths
    run_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_run_{experiment_type}.xml"
    )
    experiment_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_experiment_{experiment_type}.xml"
    )
    submission_path = os.path.join(
        template_dir,
        "submission.xml"
    )
    output_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_object_receipt.xml"
    )

    # Check all files exist beforehand
    for path in (run_path, experiment_path, submission_path):
        if not os.path.exists(path):
            raise FileNotFoundError(path)

    command = [
        "curl",
        "-u", user_password,
        "-F", f"SUBMISSION=@{submission_path}", 
        "-F", f"EXPERIMENT=@{experiment_path}",
        "-F", f"RUN=@{run_path}",
        "-o", output_path,
        "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/"
    ]

    # # Execute the command
    # try:
    #     subprocess.run(command, check=True, text=True)
    #     print(f"[+] Objects receipt XML created: {output_path}")

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
        "-e", "--experiment_type",
        help="Either 16S or metagenomics.",
        type=str
    )
    parser.add_argument(
        "-u", "--user_password",
        help="User and password for the submission (e.g. user1:password1234).",
        type=str
    )
    args = parser.parse_args()

    final_receipt_path = register_objects(
        metadata_path=args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type,
        user_password=args.user_password
    )

    print(f"[STEP3][+] Experiments and runs info saved to {final_receipt_path}")
