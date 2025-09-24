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


def main():
    args = parse_args()

    print(f"[INFO] Using 16S forward pattern {args.forward_pattern_16s}")
    print(f"[INFO] Using WGS forward pattern {args.forward_pattern_wgs}")
    forward_pattern_dict = {
        "16S": args.forward_pattern_16s,
        "WGS": args.forward_pattern_wgs
    }
    
    create_experiment(
        samples_receipt_path=args.recipe,
        metadata_path=args.metadata_path,
        samples_dir=args.samples_dir,
        template_dir=args.template_dir,
        forward_pattern_dict=forward_pattern_dict,
        experiment_types=args.experiment_types,
        check=args.check
    )


def create_experiment(
    samples_receipt_path: str,
    metadata_path: str,
    samples_dir: str,
    template_dir: str,
    forward_pattern_dict: dict,
    experiment_types: List[str],
    check: bool
) -> str:

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]

    receipt_df = parse_samples_receipt(
        samples_receipt_path=samples_receipt_path,
        metadata_path=metadata_path
    )
    
    experiment_xml = []
    for experiment_type in experiment_types:
        template_path = os.path.join(
            template_dir,
            f"experiment_{experiment_type}.xml"
        )
        #rmeove it after MILOS 
        
        print(receipt_df)
        for _, row in receipt_df.iterrows():
            print(f"ROW: {row}")
            row = row.astype(str)
            with open(template_path, mode="r") as handle:
                template_xml = handle.read()

            sample_alias = row["sample_alias"]  

            if check:          
                # Modify since WGS folders are named Metagenomes
                if experiment_type == "16S":
                    experiment_dir = "16_S"
                    sample_alias_dir = sample_alias

                elif experiment_type == "WGS":
                    experiment_dir = "Metagenomes"
                    sample_alias_dir = sample_alias
        
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


def parse_samples_receipt(samples_receipt_path: str, metadata_path: str) -> pd.DataFrame:
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


def load_metadata(metadata_path: str) -> pd.DataFrame:
    metadata_df = pd.read_excel(metadata_path, sheet_name="sample_submission")

    # Drop first and last empty rows
    metadata_df = metadata_df.iloc[1:].dropna(subset=["sample_alias"])

    # Remove time from the date
    metadata_df["collection date"] = pd.to_datetime(metadata_df["collection date"])\
        .dt.strftime("%Y-%m-%d")

    return metadata_df


def parse_args():
    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument("-i", "--metadata_path", 
                        help="Excel file containing the metadata for the sequences.",
                        type=str
                        )
    parser.add_argument("-t", "--template_dir",
                        help="Directory containing the templates for the submission.",
                        type=str
                        )
    parser.add_argument("-e", "--experiment_types",
                        help="String defining either 16S, WGS or both.",
                        type=lambda t: [s.strip() for s in t.split(",")],
                        default=["16S", "WGS"]    
                        )
    parser.add_argument("-r", "--recipe",
                        help="XML File obtained from the s01 script.",
                        type=str    
                        )
    parser.add_argument('-c' ,'--check', 
                        action='store_true', help="Mandatory command if you need string pattern for forward and reverse filenames.")
    parser.add_argument("-s", "--samples_dir",
                        help="Directory containing the sequences to submit. (Useful only if you are going to use --check)",
                        type=str
                        )
    parser.add_argument("-f", "--forward_pattern_16s",
                        help="Pattern followed in naming the forward sequence files (16S). (Useful only if you are going to use --check)",
                        type=str,
                        default="*1.fastq.gz")
    parser.add_argument("-w", "--forward_pattern_wgs",
                        help="Pattern followed in naming the forward sequence files (WGS). (Useful only if you are going to use --check)",
                        type=str,
                        default="*1.fq.gz"
                        )

    return parser.parse_args()


if __name__ == "__main__":
    main()
