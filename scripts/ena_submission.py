import os

import argparse

import pandas as pd


def read_input(input_file: str) -> pd.DataFrame:

    project_df = pd.read_excel(
        input_file,
        sheet_name="sample_submission"
    )

    # Drop first and last empty rows
    project_df = project_df\
        .iloc[1:]\
        .dropna(subset=["sample_alias"])

    # Remove time from the date
    project_df["collection date"] = \
        pd.to_datetime(project_df["collection date"])\
        .dt.strftime("%Y-%m-%d")

    return project_df


def create_template(
    input_file: str,
    template_file: str
) -> None:

    project_df = read_input(input_file)

    samples_all = []

    # Create a template for each sample
    for _, row in project_df.iterrows():

        # Avoid errors while formatting numbers
        row = row.astype(str)

        with open(template_file, mode="r") as handle:
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
    project_name = os.path.basename(input_file).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(input_file),
        f"{project_name}_ena_samples.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(samples_all)

    return None


if __name__ == "__main__":

    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument(
        "-i", "--input_file",
        help="Excel file containing the metadata for the sequences.",
        type=str
    )
    parser.add_argument(
        "-t", "--template_file",
        help="Template file for creating the XML for submission.",
        type=str
    )
    args = parser.parse_args()

    create_template(
        input_file=args.input_file,
        template_file=args.template_file
    )
