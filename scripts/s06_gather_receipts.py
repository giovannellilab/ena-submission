#!/usr/bin/env python3
import argparse
import os
import csv
import subprocess
from bs4 import BeautifulSoup
import sys 
import pandas as pd
from ruamel.yaml import YAML
from ena_utils import read_config, get_config_variable, write_config


def main():
    args = parse_args()

    config_file = args.config_path
    data = read_config(config_file)


    project_name = get_config_variable(data, "project_name")
    ena_checklist = get_config_variable(data, "ena_checklist")
    metadata_file = get_config_variable(data, "metadata_file")
    sequencing_platform = get_config_variable(data,"SEQUENCING_PLATFORM")
    sequencing_instrument_model = get_config_variable(data,"SEQUENCING_INSTRUMENT_MODEL")
    recipe_samples = get_config_variable(data, "receipt_samples_permanent")
    object_receipt = get_config_variable(data, "receipt_objects_permanent")

    for experiment_type in args.experiment_types:

        print(f"Creating details registration for {experiment_type}")
        receipt_df = parse_objects_receipts(
            metadata_path = metadata_file,
            sample_receipt_path = recipe_samples,
            object_receipt_path = object_receipt,
            experiment_type=experiment_type,
            project_name=project_name
        )

        details_path = save_results_metadata(
            dataframe=receipt_df,
            metadata_path=metadata_file,
            experiment_type=experiment_type,
            ena_checklist=ena_checklist,
            project_name=project_name,
            sequencing_platform=sequencing_platform,
            sequencing_instrument_model=sequencing_instrument_model
        )

        print(f"[STEP6][+] Metadata written to {details_path}")


def parse_objects_receipts(
    metadata_path: str,
    sample_receipt_path: str,
    object_receipt_path: str,
    experiment_type: str,
    project_name: str
) -> pd.DataFrame:

    # Associate:
    # - SAMPLE accession: ERS00000000 and SAMEA
    # - EXP accession:    ERX00000000
    # - RUN accession:    ERR00000000

    # WARNING: project name is assumed to be in the first field of the path
    metadata_dir = os.path.dirname(metadata_path)

    experiment_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_experiment_{experiment_type}.xml"
    )
    run_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_run_{experiment_type}.xml"
    )

    # ------------------------------------------------------------------------ #
    for path in (sample_receipt_path, object_receipt_path, experiment_path, run_path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required file not found: {path}")
    # ------------------------------------------------------------------------ #
    # RETRIEVING METADATA from samples_receipt.xml file
    with open(sample_receipt_path, mode="r") as handle:
        xml_data = BeautifulSoup(handle, "xml")

        samples = {}
        for sample in xml_data.find_all("SAMPLE"):
            accession = sample.get("accession")                      # ERS
            samea_accession = sample.find("EXT_ID").get("accession") # SAMEA
            custom_accession = sample.get("alias")                   # Custom
            samples[accession] = [custom_accession, samea_accession]
    # ------------------------------------------------------------------------ #
    # RETRIEVING METADATA from Object-registration-receipt.xml file
    with open(object_receipt_path, mode="r") as handle:
        xml_data = BeautifulSoup(handle, "xml")

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
        xml_exp = BeautifulSoup(ef, "xml")
        xml_run = BeautifulSoup(rf, "xml")

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

    dataframe = pd.concat(results_df)
    output_file = os.path.join(metadata_dir,f'{project_name}_{experiment_type}_info_registration.tsv')
    dataframe.to_csv(output_file, sep = '\t', index = False)

    return dataframe


def save_results_metadata(
    dataframe: pd.DataFrame,
    metadata_path: str,
    experiment_type: str,
    ena_checklist: str,
    project_name: str,
    sequencing_platform: str,
    sequencing_instrument_model: str

)-> str:

    # WARNING: project name is assumed to be in the first field of the path
    print(ena_checklist)
    # project ACCESSION such : PRJEB67767
    metadata_dir = os.path.dirname(metadata_path)
    sample_xml_file = f'{project_name}_ena_sample_{ena_checklist}.xml'
    
    with open(os.path.join(metadata_dir,sample_xml_file), mode="r") as handle:
        xml_sample = BeautifulSoup(handle, "xml")

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
            str(sequencing_platform),
            str(sequencing_instrument_model),
            "METAGENOMIC",
            "PCR",
            "AMPLICON"
        ]
    else:
        ngs_data = [
            str(sequencing_platform),
            str(sequencing_instrument_model),
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
        "-s", "--config_path", 
        help="config yaml file containing direcotries for the whole workflow.",
        type=str
    )
    parser.add_argument(
        "-e", "--experiment_types",
        help="String defining either 16S, WGS or both.",
        type=str,
        nargs='+',              
        choices=["16S", "WGS"],
        default=["16S", "WGS"]
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()