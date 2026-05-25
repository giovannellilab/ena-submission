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
from ena_utils import read_config, get_config_variable


def main():
    args = parse_args()

    config_file = args.config_path
    data = read_config(config_file)

    project_name = get_config_variable(data, "project_name") 
    template_dir = get_config_variable(data, "template_dir") 
    metadata_file = get_config_variable(data, "metadata_file") 
    readmapping_table_wgs = get_config_variable(data, "readmapping_table_wgs")
    readmapping_table_ampl = get_config_variable(data, "readmapping_table_amplicon")
    recipe = get_config_variable(data, "receipt_samples_permanent") 
    sequencing_year = get_config_variable(data, "SEQUENCING_YEAR")
    sequencing_platform = get_config_variable(data,"SEQUENCING_PLATFORM")
    sequencing_instrument_model = get_config_variable(data,"SEQUENCING_INSTRUMENT_MODEL")
    sequencing_library_construction_protocol = get_config_variable(data,"SEQUENCING_LIBRARY_CONSTRUCTION_PROTOCOL")


    create_experiment(
        samples_receipt_path=recipe,
        metadata_path=metadata_file,
        template_dir=template_dir,
        experiment_type=args.experiment_type,

        mapping_WGS = readmapping_table_wgs,
        mapping_AMP = readmapping_table_ampl,
        project_name = project_name,

        sequencing_year = sequencing_year
    )


def create_experiment(
    samples_receipt_path: str,
    metadata_path: str,
    template_dir: str,
    experiment_type: str,
    mapping_WGS : str,
    mapping_AMP : str,
    project_name : str,
    sequencing_year : str,
) -> str:

    receipt_df = parse_samples_receipt(
        project_name=project_name,
        samples_receipt_path=samples_receipt_path,
        metadata_path=metadata_path
    )
    
    
    if experiment_type in ["16S","18S","ITS"]:
        if not os.path.exists(mapping_AMP):
            raise FileNotFoundError(f"{mapping_AMP} does not exist!")
        
        table_mapping = pd.read_csv(mapping_AMP, sep="\t")
        template_path = os.path.join(
            template_dir,
            f"experiment_{experiment_type}.xml"
        )
    elif experiment_type == 'WGS':
        if not os.path.exists(mapping_WGS):
            raise FileNotFoundError(f"{mapping_AMP} does not exist!")
        
        table_mapping = pd.read_csv(mapping_WGS, sep="\t")
        template_path = os.path.join(
            template_dir,
            f"experiment_{experiment_type}.xml"
        )

    experiment_xml = []

    for _, row in receipt_df.iterrows():
        row = row.astype(str)

        with open(template_path, mode="r") as handle:
            template_xml = handle.read()

            sample_alias = row["sample_alias"]
            exist = [ True for i in table_mapping.itertuples() if i.sample_alias ==  sample_alias]

            if exist:
                print('Check TRUE:',sample_alias)
                exp_alias = f"{project_name}-{row.sample_alias}-{experiment_type}"

                template_xml = template_xml\
                    .replace("$$$STUDY_ID$$$", row["project_id"])\
                    .replace("$$$EXPERIMENT_ALIAS$$$", exp_alias)\
                    .replace("$$$EXPERIMENT_TITLE$$$", exp_alias)\
                    .replace("$$$SAMPLE_ACCESSION$$$", row["sample_accession"])\
                    .replace("$$$YEAR$$$", str(sequencing_year))

                experiment_xml += [template_xml]
            else:
                print('Check !FALSE! -> :',row.sample_alias)
                continue

            exist = False

    experiment_xml = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<EXPERIMENT_SET>" + "\n" + \
        "\n".join(experiment_xml) + "\n" + \
        "</EXPERIMENT_SET>" + "\n"

    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_experiment_{experiment_type}.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(experiment_xml)
    
    print(f"\nIn the case a Sample alias check is FALSE. it means either:\n"
                "NO experiment was generated for this alias, do not bother, continue with STEP3\n"
                "Otherwise, check naming correspondence, it might be wrong. check, modify,repeat! \n")
    print(f"[STEP2][+] Experiment XML saved to:  {output_path}")

    return output_path


def parse_samples_receipt(project_name:str, samples_receipt_path: str, metadata_path: str) -> pd.DataFrame:
    # Programmatically assign study ID
    metadata_df = load_metadata(metadata_path)

    if os.path.exists(samples_receipt_path):

        with open(samples_receipt_path, mode="r") as handle:
            xml_data = bs.BeautifulSoup(handle, "xml")

        data_df = []
        for sample in xml_data.find_all("SAMPLE"):

            alias = sample.get("alias")
            title = sample.get("accession")
            ext_id_element = sample.find("EXT_ID")
            ext_id = ext_id_element.get("accession")
            study_id = project_name

            row = pd.Series({
                "project_id": study_id,
                "sample_alias": alias,
                "sample_accession": title,
                "biosample_id": ext_id
            }).to_frame().T

            data_df.append(row)
    else:
        print(f'Sample receipt file: {samples_receipt_path} NOT found')

    return pd.concat(data_df)


def load_metadata(metadata_path: str) -> pd.DataFrame:

    spreadsheet_file = os.path.abspath(metadata_path)
    base, extension = os.path.splitext(spreadsheet_file)

    if not extension:
        print(f"Error: Path '{metadata_path}' looks like a directory. Please provide a file.")    
        sys.exit(1)

    try:
        if extension in [".xlsx", ".xls"]:
            spreadsheet = pd.read_excel(spreadsheet_file, sheet_name="sample_submission", header=0)
        elif extension == ".csv":
            spreadsheet = pd.read_csv(spreadsheet_file, header=0, sep=",")
        elif extension in [".txt", ".tsv"]:
            spreadsheet = pd.read_csv(spreadsheet_file, header=0, sep="\t")
        else:
            print(f"Error: Unsupported file format '{extension}'")
            sys.exit(1)
    except Exception as e:
        print(f"Error reading the file: {e}")
        sys.exit(1)

    spreadsheet = spreadsheet.iloc[1:].copy()
    spreadsheet = spreadsheet.dropna(subset=["sample_alias"])

    if "collection_date" in spreadsheet.columns:
        spreadsheet["collection_date"] = pd.to_datetime(spreadsheet["collection_date"], errors='coerce')\
            .dt.strftime("%Y-%m-%d")

    return spreadsheet


def parse_args():
    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument("-s", "--config_path", 
                        help="config yaml file containing direcotries for the whole workflow.",
                        type=str
                        )
    parser.add_argument("-e", "--experiment_type",
                        help="String defining either 16S, WGS, 18S or ITS sequences",
                        choices=["16S", "WGS"]
                        )

    return parser.parse_args()


if __name__ == "__main__":
    main()
