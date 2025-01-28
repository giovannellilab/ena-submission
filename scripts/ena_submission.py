import os

import argparse

import pandas as pd

import subprocess


def load_metadata(input_path: str) -> pd.DataFrame:

    metadata_df = pd.read_excel(
        input_path,
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
    input_path: str,
    template_path: str
) -> str:

    metadata_df = load_metadata(input_path)

    samples_all = []

    # Create a template for each sample
    for _, row in metadata_df.iterrows():

        # Avoid errors while formatting numbers
        row = row.astype(str)

        with open(template_path, mode="r") as handle:
            template_xml = handle.read()

        template_xml = template_xml\
            .replace("$SAMPLE_TITLE$", row["sample_title"])\
            .replace("$SAMPLE_ALIAS$", row["sample_alias"])\
            .replace("$ENV_TAX_ID$", row["tax_id"])\
            .replace("$ENV_SCI_NAME$", row["scientific_name"])\
            .replace("$PROJECT_NAME$", row["project name"])\
            .replace("$COLLECTION_DATE$", row["collection date"])\
            .replace("$LATITUDE$", row["geographic location (latitude)"])\
            .replace("$LONGITUDE$", row["geographic location (longitude)"])\
            .replace("$ENV_BROAD$", row["broad-scale environmental context"])\
            .replace("$ENV_LOCAL$", row["local environmental context"])\
            .replace("$ENV_MEDIUM$", row["environmental medium"])\
            .replace("$ELEVATION$", row["elevation"])\
            .replace("$LOC$", row["geographic location (country and/or sea)"])

        samples_all += [template_xml]

    samples_all = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<SAMPLE_SET>" + "\n" + \
        "\n".join(samples_all) + "\n" + \
        "</SAMPLE_SET>" + "\n"

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(input_path).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(input_path),
        f"{project_name}_ena_samples.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(samples_all)

    return output_path


def register_samples(
    samples_path: str,
    template_path: str,
    user_password: str
) -> str:

    # Define input XML files
    submission_path = os.path.join(
        os.path.dirname(template_path),
        "submission.xml"
    )

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(samples_path).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(samples_path),
        f"{project_name}_ena_samples_receipt.xml"
    )

    # Build the command
    command = [
        "curl",
        "-u", user_password,
        "-F", f"SUBMISSION=@{submission_path}", 
        "-F", f"SAMPLE=@{samples_path}",
        "-F", "LAUNCH=YES",
        "-o", output_path,
        "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/"
    ]

    # Execute the command
    try:
        subprocess.run(command, check=True, text=True)
        print(f"Response successfully written to {output_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error:", {e.stderr})

    return output_path


if __name__ == "__main__":

    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument(
        "-i", "--input_path",
        help="Excel file containing the metadata for the sequences.",
        type=str
    )
    parser.add_argument(
        "-t", "--template_path",
        help="Template file for creating the XML for submission.",
        type=str
    )
    parser.add_argument(
        "-u", "--user_password",
        help="User and password for the submission (e.g. user1:password1234).",
        type=str
    )
    args = parser.parse_args()

    samples_path = create_samples_file(
        input_path=args.input_path,
        template_path=args.template_path
    )

    receipt_path = register_samples(
        samples_path=samples_path,
        template_path=args.template_path,
        user_password=args.user_password
    )
