#!/usr/bin/env python3

import argparse
import os
import csv
import subprocess
import bs4 as bs
import sys 
import pandas as pd


def main():
    args = parse_args()

    submissionType = None if args.submission_type == "null" else args.submission_type

    final_receipt_path = register_objects(
        metadata_path=args.metadata_path,
        template_dir=args.template_dir,
        user_password=args.user_password,
        submission_type=submissionType
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


def register_objects(
    metadata_path: str,
    template_dir: str,
    user_password: str,
    submission_type: str
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

    if os.path.exists(output_path):
        raise FileExistsError(f"Il file '{output_path}' esiste già e non deve essere sovrascritto!")

    # --- Preview-only mode ---
    if not submission_type:
        print("[INFO] submission_type is empty. Dry-run mode: returning output path only.")
        return output_path
    
    # --- Validate submission type ---
    normalized = submission_type.lower()
    if normalized in ['y', 'yes']:

        url_ebi_ac_uk = "https://www.ebi.ac.uk/ena/submit/drop-box/submit/"
        print('[STEP0][+] Submitting to Permanent partition ..')
        permanent = True

    elif normalized in ['n','no']:

        url_ebi_ac_uk = "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/"
        print('[STEP0][+] Submitted to TEST partition ..')
        permanent = False

    else:
        print("[!] Invalid value for --submission_type \n " \
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
        print(f"[STEP3][+]  Object receipt saved to: {output_path}")
        if permanent:
            print(f"[STEP3][+] Objects registered Permanently")
        else:
            print(f"[STEP3][+] Objects registered Temporarily")
    else:
        print('\n'.join(f'[!] {k} --> {v}' for k, v in message.items()))
        print('Exiting....')
        sys.exit(1)

    return output_path


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
    # project ACCESSION such : PRJEB67767
    metadata_dir = os.path.dirname(metadata_path)
    sample_xml_file = f'{project_name}_ena_samples.xml'
    
    with open(os.path.join(metadata_dir,sample_xml_file), mode="r") as handle:
        xml_sample = bs.BeautifulSoup(handle, "xml")

        for attr in xml_sample.find_all("SAMPLE_ATTRIBUTE"):
            tag = attr.find("TAG")
            value = attr.find("VALUE")

            if tag and tag.text.strip() == "project name" and value:
                project_accession = value.text.strip()
                break  

    output_dir = os.path.dirname(metadata_path)
    output_path = os.path.join(
        output_dir,
        f"{project_name}_details_{experiment_type}.csv"
    )

    cols_study = ["expID", "study_accession"]
    study_data = [project_name, project_accession]

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


def parse_args():
    parser = argparse.ArgumentParser("Register objects")
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
        default=["16S","WGS"]
    )
    parser.add_argument(
        "-u", "--user_password",
        help="User and password for the submission (e.g. user1:password1234).",
        type=str
    )
    parser.add_argument(
        "-x", "--submission_type",
        help="Submission type: 'y' or 'yes' for permanent; 'n' or 'no' for test. Leave empty for dry run.",
        type=str,
        default="null",
        choices=['y', 'yes', 'n', 'no', 'null']  # Accept only known values
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
 