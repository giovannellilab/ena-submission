#!/usr/bin/env python3

from typing import List
import os
import glob
import hashlib
import sys
import argparse
from datetime import datetime
import pandas as pd
import subprocess
from tqdm import tqdm
from ruamel.yaml import YAML
from ena_utils import read_config, get_config_variable, write_config


def main():
    args = parse_args()

    config_file = args.config_path
    data = read_config(config_file)


    project_name = get_config_variable(data, "project_name")
    template_dir = get_config_variable(data, "template_dir")
    metadata_file = get_config_variable(data, "metadata_file")

    readmapping_table_wgs = get_config_variable(data,"readmapping_table_wgs")
    readmapping_table_amp = get_config_variable(data,"readmapping_table_amp")
    raw_data_dir_amp = get_config_variable(data,"raw_data_dir_amp")
    raw_data_dir_wgs = get_config_variable(data,"raw_data_dir_wgs")

    if args.experiment_types == "16S":
        updated_table, table_file = compute_gather_amp(
            AMP_samples_dir=raw_data_dir_amp,
            mapping_AMP=readmapping_table_amp,
            metadata_path=metadata_file,
            nested=args.nested
        )
    elif args.experiment_types == "WGS":
        updated_table, table_file = compute_gather_wgs(
            WGS_samples_dir=raw_data_dir_wgs,
            mapping_WGS=readmapping_table_wgs,
            metadata_path=metadata_file,
            nested=args.nested
        )

    mapping_info = updated_table if not updated_table.empty else table_file

    run_path = create_run(
        metadata_path=metadata_file,
        template_dir=template_dir,
        experiment_type=args.experiment_types,
        project_name=project_name,
        mapping=mapping_info,
    )


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

    # Use copy() to avoid "SettingWithCopyWarning" later
    # Removing first row if it's a sub-header/example and dropping invalid aliases
    spreadsheet = spreadsheet.iloc[1:].copy()
    spreadsheet = spreadsheet.dropna(subset=["sample_alias"])

    # 4. Date Standardization
    if "collection_date" in spreadsheet.columns:
        spreadsheet["collection_date"] = pd.to_datetime(spreadsheet["collection_date"], errors='coerce')\
            .dt.strftime("%Y-%m-%d")

    return spreadsheet

def get_or_compute_md5(file_path: str, checksum_log: str) -> str:
    
    filename = os.path.basename(file_path)
    # 1. Try to find existing checksum in the log
    if os.path.exists(checksum_log):
        with open(checksum_log, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == filename:
                    return parts[0]

    # 2. If we reach this point, it means the hash wasn't found or log doesn't exist.
    # Compute it (using chunks is better for large fastq.gz files to avoid RAM issues)
    hash_obj = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    
    hash_md5 = hash_obj.hexdigest()

    # 3. Save the new hash to the log
    with open(checksum_log, 'a') as f:
        f.write(f"{hash_md5} {filename}\n")

    return hash_md5

def compute_gather_amp(
        AMP_samples_dir: str,
        mapping_AMP: str,
        metadata_path: str,
        nested: bool
) -> tuple[pd.DataFrame, str]:

    if AMP_samples_dir and not os.path.exists(AMP_samples_dir):
        raise FileNotFoundError(f"{AMP_samples_dir} does not exist!")

    table_mapping = pd.read_csv(mapping_AMP, sep="\t")

    required_cols = ["r1", "r2", "sample_alias"]
    has_sample_id = "sample_id" in table_mapping.columns

    assert all(col in table_mapping.columns for col in required_cols), \
        f"Logic Error: One or more columns from {required_cols} are missing."

    if nested and not has_sample_id:
        raise ValueError("nested_folders=True requires a 'sample_id' column.")

    if not nested:
        print('\n[INFO] Assuming read files are in the same directory\n')
    else:
        print('\n[INFO] Sequence files are nested, proceeding to retrieve...\n')

    md5_results = []

    for row in tqdm(table_mapping.itertuples(), total=len(table_mapping), desc="Computing md5sum.."):
        base_path = os.path.join(AMP_samples_dir, str(row.sample_id)) if has_sample_id and nested else AMP_samples_dir
        if os.path.exists(base_path):
            r1_path = os.path.join(base_path, row.r1)
            r2_path = os.path.join(base_path, row.r2)
            checksum_file = os.path.join(base_path, 'MD5.txt')

            if os.path.exists(r1_path) and os.path.exists(r2_path):
                h1 = get_or_compute_md5(r1_path, checksum_log=checksum_file)
                h2 = get_or_compute_md5(r2_path, checksum_log=checksum_file)
                md5_results.append({
                    "sample_alias": row.sample_alias,
                    "r1_md5sum": h1,
                    "r2_md5sum": h2
                })
            else:
                print(f'[WARN] Files not found for sample: {row.sample_alias}')

    md5_df = pd.DataFrame(md5_results)
    updated_table = pd.merge(table_mapping, md5_df, how='left', on='sample_alias')

    metadata_dir = os.path.dirname(metadata_path)
    updated_mapping_file = os.path.join(metadata_dir, 'mapping_table_amp.tsv')
    updated_table.to_csv(updated_mapping_file, sep='\t', index=False)

    print(f'[INFO] Updated mapping table saved to: {updated_mapping_file}')
    return updated_table, updated_mapping_file


def compute_gather_wgs(
        WGS_samples_dir: str,
        mapping_WGS: str,
        metadata_path: str,
        nested: bool
) -> tuple[pd.DataFrame, str]:

    if WGS_samples_dir and not os.path.exists(WGS_samples_dir):
        raise FileNotFoundError(f"{WGS_samples_dir} does not exist!")

    table_mapping = pd.read_csv(mapping_WGS, sep="\t")

    required_cols = ["r1", "r2", "sample_alias"]
    has_sample_id = "sample_id" in table_mapping.columns

    assert all(col in table_mapping.columns for col in required_cols), \
        f"Logic Error: One or more columns from {required_cols} are missing."

    if nested and not has_sample_id:
        raise ValueError("nested_folders=True requires a 'sample_id' column.")

    if not nested:
        print('\n[INFO] Assuming read files are in the same directory\n')
    else:
        print('\n[INFO] Sequence files are nested, proceeding to retrieve...\n')

    md5_results = []

    for row in tqdm(table_mapping.itertuples(), total=len(table_mapping), desc="Computing md5sum.."):
        base_path = os.path.join(WGS_samples_dir, str(row.sample_id)) if has_sample_id and nested else WGS_samples_dir
        if os.path.exists(base_path):
            r1_path = os.path.join(base_path, row.r1)
            r2_path = os.path.join(base_path, row.r2)
            checksum_file = os.path.join(base_path, 'MD5.txt')

            if os.path.exists(r1_path) and os.path.exists(r2_path):
                h1 = get_or_compute_md5(r1_path, checksum_log=checksum_file)
                h2 = get_or_compute_md5(r2_path, checksum_log=checksum_file)
                md5_results.append({
                    "sample_alias": row.sample_alias,
                    "r1_md5sum": h1,
                    "r2_md5sum": h2
                })
            else:
                print(f'[WARN] Files not found for sample: {row.sample_alias}')

    md5_df = pd.DataFrame(md5_results)
    updated_table = pd.merge(table_mapping, md5_df, how='left', on='sample_alias')

    metadata_dir = os.path.dirname(metadata_path)
    updated_mapping_file = os.path.join(metadata_dir, 'mapping_table_wgs.tsv')
    updated_table.to_csv(updated_mapping_file, sep='\t', index=False)

    print(f'[INFO] Updated mapping table saved to: {updated_mapping_file}')
    return updated_table, updated_mapping_file


def create_run(
    metadata_path: str,
    template_dir: str,
    experiment_type: str,
    project_name: str,
    mapping
) -> str:
    #ADD input parameter for project_name & experiment alias

    # if mapping_WGS and not os.path.exists(WGS_samples_dir):
    #     raise FileNotFoundError(f"{WGS_samples_dir} does not exist!")
    
    # # Raise error if samples directory does not exist
    # if WGS_samples_dir and not os.path.exists(WGS_samples_dir):
    #     raise FileNotFoundError(f"{WGS_samples_dir} does not exist!")
    
    # if AMP_samples_dir and not os.path.exists(AMP_samples_dir):
    #     raise FileNotFoundError(f"{AMP_samples_dir} does not exist!")

    template_path = os.path.join(
        template_dir,
        f"run.xml"
    )
    
    run_xml = []
    # if experiment_type == 'AMP':
    #     exp_dir = AMP_samples_dir
    #     table_mapping = pd.read_csv(mapping_AMP, sep="\t")
    # elif experiment_type == 'WGS':
    #     exp_dir = WGS_samples_dir
    if isinstance(mapping, str):
        table_mapping = pd.read_csv(mapping, sep="\t")
    else:
        table_mapping = mapping
    
    run_xml = []
    required_cols = ["r1", "r2","sample_alias","r1_md5sum","r2_md5sum"]
    
    assert all(col in table_mapping.columns for col in required_cols), \
    f"Logic Error: One or more columns from {required_cols} are missing."
    
    for row in tqdm(table_mapping.itertuples(),
                total=len(table_mapping),
                desc="Creating RUN xml file.."):

        # wrting to run.xml file
        with open(template_path, mode="r") as handle:
            template_xml = handle.read()
        # WARNING: sample alias is assumed to be the first three fields
        sample_alias = row.sample_alias

        exp_alias = f"{project_name}-{sample_alias}-{experiment_type}"
        template_xml = template_xml\
            .replace("$$$EXPERIMENT_ALIAS$$$",  exp_alias)\
            .replace("$$$FORWARD_R1_FASTQ$$$",  row.r1)\
            .replace("$$$FORWARD_R1_MD5SUM$$$", row.r1_md5sum)\
            .replace("$$$REVERSE_R2_FASTQ$$$",  row.r2)\
            .replace("$$$REVERSE_R2_MD5SUM$$$", row.r2_md5sum)
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

    print(f"[STEP3][+] Run XML saved to:         {output_path}")

    return output_path


def parse_args():
    parser = argparse.ArgumentParser("Create run objects")
    parser.add_argument("-s", "--config_path", 
                        help="config yaml file containing direcotries for the whole workflow.",
                        required=True,
                        type=str
                        )
    parser.add_argument("-e", "--experiment_types",
                        help="String defining either 16S or WGS",
                        required=True,
                        choices=["16S", "WGS"]    
                        )
    parser.add_argument("-n", "--nested",
                        help="If sequences files are nested within each corrispective sample dir names",
                        action='store_true'
                        )

    return parser.parse_args()


if __name__ == "__main__":
    main()
