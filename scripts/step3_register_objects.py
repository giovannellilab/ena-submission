# ENA submission: STEP 3

# This script performs the following steps programmatically:

# 1. Experiment and run registration

# 2. Metadata generation for tracking purposes

# ---------------------------------------------------------------------------- #

# IMPORTANT! Some considerations must be taken into account:
# 1) Project name is assumed to be the first field in the metadata filename
# 2) Sample alias is assumed to be the first three fields in the sample filename

# ---------------------------------------------------------------------------- #

import os

import argparse

import subprocess

import bs4 as bs

import pandas as pd


def register_objects(
    metadata_path: str,
    template_dir: str,
    user_password: str
) -> str:

    project_name = os.path.basename(metadata_path).split("_")[0]
    metadata_dir = os.path.dirname(metadata_path)

    # Define paths
    submission_path = os.path.join(
        template_dir,
        "submission.xml"
    )
    experiment_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_experiment.xml"
    )
    run_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_run.xml"
    )
    output_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_object_receipt.xml"
    )

    # Check all files exist beforehand
    for path in (submission_path, experiment_path, run_path):
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


def mapping(
    runs: dict,
    exps: dict
) -> dict:
    results_dict = {}
    for k, v in runs.items():
        alias = k[4:]

        if alias in exps.keys():
            # In order: EXP, RUN, RUN_alias
            results_dict[alias] = [exps[alias], v, k]

    return results_dict


def parse_objects_receipts(
    metadata_path: str,
    template_dir: str,
    experiment_type: str
) -> pd.DataFrame:

    # Associate:
    # - SAMPLE accession: ERS00000000 and SAMEA
    # - EXP accession:    ERX00000000
    # - RUN accession:    ERR00000000

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]
    metadata_dir = os.path.dirname(metadata_path)

    sample_receipt_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_samples_receipt.xml"
    )
    experiment_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_experiment.xml"
    )
    run_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_run.xml"
    )
    object_receipt_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_object_receipt.xml"
    )

    # ------------------------------------------------------------------------ #

    # RETRIEVING METADATA from samples_receipt.xml file
    with open(sample_receipt_path, mode="r") as handle:
        xml_data = bs.BeautifulSoup(handle, "xml")

        samples = {}
        for sample in xml_data.find_all("SAMPLE"):
            accession = sample.get("accession")                      # ERS
            samea_accession = sample.find("EXT_ID").get("accession") # SAMEA
            custom_accession = sample.get("alias")                   # Custom
            samples[accession] = [custom_accession, samea_accession]

    # ------------------------------------------------------------------------ #

    # RETRIEVING METADATA from Object-registration-receipt.xml file
    with open(object_receipt_path, mode="r") as handle:
        xml_data = bs.BeautifulSoup(handle, "xml")

    exps = {}
    for exp in xml_data.find_all("EXPERIMENT"):
        alias_exp = exp.get("alias")
        exp_accession = exp.get("accession")
        exps[alias_exp] = exp_accession
    runs = {}
    for run in xml_data.find_all("RUN"):
        alias_run = run.get("alias")
        run_accession = run.get("accession")
        runs[alias_run] = run_accession

    object_receipt = mapping(
        runs=runs,
        exps=exps
    )

    # ------------------------------------------------------------------------ #

    # RETRIEVING METADATA from experiment.xml AND run.xml
    with open(experiment_path, mode="r") as ef, open(run_path, mode="r") as rf:
        xml_exp = bs.BeautifulSoup(ef, "xml")
        xml_run = bs.BeautifulSoup(rf, "xml")

        exp_meta = {}
        for exp in xml_exp.find_all("EXPERIMENT"):
            exp_ref = exp.get("alias")
            descriptor = exp.find("SAMPLE_DESCRIPTOR")
            sample_accession = descriptor.get("accession")
            exp_meta[exp_ref] = sample_accession

        run_meta = {}
        for run in xml_run.find_all("RUN"):
            exp_ref = run.find("EXPERIMENT_REF")
            name_exp = exp_ref.get("refname")
            files = run.find("FILES")
            names_files = files.find_all("FILE")

            run_file = []
            for file in names_files:
                f = file.get("filename")
                md5 = file.get("checksum")
                run_file.append(f)
                run_file.append(md5)

            run_meta[name_exp] = run_file

    # ------------------------------------------------------------------------ #

    results_df  = []

    # 1) Iterate over samples (ERS)
    for k, values in samples.items():

        # 2) Retrieve experiments (16S or WGS or both) from XML (using ERS)
        if k in exp_meta.values():
            # There are at max two keys with same value: one experiment for 16S
            # and another one for WGS, need to inlucde ONLY the one we are
            # passing in the loop when we call function
            exp_aliases = [
                key for key, val in exp_meta.items()
                if val == k and key.split("-")[-1] == experiment_type
            ]

            # 3) Iterate over experiments
            for exp_alias in exp_aliases:

                # 4) Retrieve runs from XML (using ERX)
                if exp_alias in run_meta.keys():
                    run_info = run_meta[exp_alias]

                if exp_alias in object_receipt.keys():
                    receipt = object_receipt[exp_alias]

                row = pd.Series({
                    "sample_alias": values[0],     # Custom
                    "sample_id_paper": values[1],  # SAMEA
                    "sample_accession": k,
                    "experiment_alias": exp_alias,
                    "experiment_accession": receipt[0],
                    "run_alias": receipt[2],
                    "run_accession": receipt[1],
                    "forward_file": run_info[0],
                    "reverse_file": run_info[2],
                    "forward_checksum": run_info[1],
                    "reverse_checksum": run_info[3]
                }).to_frame().T

                results_df.append(row)

    return pd.concat(results_df)


def save_results_metadata(
    dataframe: pd.DataFrame,
    metadata_path: str,
    template_dir: str,
    experiment_type: str,
)-> str:

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]

    output_dir = os.path.dirname(metadata_path)
    output_path = os.path.join(
        output_dir,
        f"{project_name}_details_{experiment_type}.csv"
    )

    cols_study = ["expID", "study_accession"]
    study_data = [project_name, "PRJEB67767"]

    cols_ngs = [
        "sequencing_platform",
        "sequencing_instrument",
        "library_source",
        "library_selection",
        "library_strategy"
    ]
    if experiment_type == "16S":
        ngs_data = [
            "ILLUMINA",
            "Illumina NovaSeq 6000",
            "METAGENOMIC",
            "PCR",
            "AMPLICON"
        ]
    else:
        ngs_data = [
            "ILLUMINA",
            "Illumina NovaSeq 6000",
            "GENOMIC",
            "RANDOM",
            "WGS"
        ]

    for col, value in zip(cols_study, study_data):
        dataframe[col] = value
    for col, value in zip(cols_ngs, ngs_data):
        dataframe[col] = value

    # Re-order the columns
    dataframe = dataframe[
        cols_study + dataframe.columns.drop(cols_study).tolist()
    ]
    dataframe.to_csv(
        output_path,
        index=False,
        sep=","
    )

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
        "-e", "--experiment_types",
        help="String defining either 16S, WGS or both.",
        type=lambda t: [s.strip() for s in t.split(",")],
        default="16S,WGS"
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
        user_password=args.user_password
    )
    print(f"[STEP3][+] Experiments and runs info saved to {final_receipt_path}")

    for experiment_type in args.experiment_types:
        receipt_df = parse_objects_receipts(
            metadata_path = args.metadata_path,
            template_dir=args.template_dir,
            experiment_type=experiment_type,
        )

        details_path = save_results_metadata(
            dataframe=receipt_df,
            metadata_path=args.metadata_path,
            template_dir=args.template_dir,
            experiment_type=experiment_type
        )

        print(f"[STEP3][+] Metadata written to {details_path}")
