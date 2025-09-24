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

    run_path = create_run(
        metadata_path=args.metadata_path,
        template_dir=args.template_dir,
        experiment_types=args.experiment_types,

        WGS_samples_dir=args.WGS_samples_dir,
        AMP_samples_dir=args.AMP_samples_dir,

        mapping_WGS=args.mapping_WGS,
        mapping_AMP=args.mapping_AMP
    )


def create_run(
    metadata_path: str,
    template_dir: str,
    experiment_types: List[str],
    WGS_samples_dir: str,
    AMP_samples_dir: str,
    mapping_WGS,
    mapping_AMP
) -> str:

    # Raise error if samples directory does not exist
    if WGS_samples_dir and not os.path.exists(WGS_samples_dir):
        raise FileNotFoundError(f"{WGS_samples_dir} does not exist!")
    
    if AMP_samples_dir and not os.path.exists(AMP_samples_dir):
        raise FileNotFoundError(f"{AMP_samples_dir} does not exist!")

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]

    template_path = os.path.join(
        template_dir,
        f"run.xml"
    )
    
    run_xml = []
    for experiment_type in experiment_types:
        if experiment_type == '16S':
            exp_dir = AMP_samples_dir
            table_mapping = pd.read_csv(mapping_AMP, sep="\t")
        elif experiment_type == 'WGS':
            exp_dir = WGS_samples_dir
            table_mapping = pd.read_csv(mapping_WGS, sep="\t")
        
        for row in table_mapping.itertuples():
            # Retrieve checksum (MD5.txt)
            checksum_path = os.path.join(os.path.dirname(exp_dir), f"MD5.txt")
            try:
                if checksum_path:
                    print("MD5.txt ESISTE!!!!")
                    with open(checksum_path, mode="r") as file:
                        for line in file:
                            if row.sample_alias in line and row.forward in line:
                                hash_for = line.split(" ")[0]
                            elif row.sample_alias in line and row.reverse in line:
                                hash_rev = line.split(" ")[0]
                else:
                    raise FileNotFoundError

            except (FileNotFoundError):
                r1= os.path.join(os.path.dirname(exp_dir), row.forward)
                r2= os.path.join(os.path.dirname(exp_dir), row.reverse)

                hash_for = hashlib.md5(open(r1, mode="rb").read())\
                    .hexdigest()
                hash_rev = hashlib.md5(open(r2, mode="rb").read())\
                        .hexdigest()
                
                checksum_file = os.path.join(os.path.dirname(exp_dir), 
                                             f"{row.sample_alias}_MD5.txt")
                
                with open(checksum_file, mode='w') as writer:
                    writer.write(f"{hash_for} {row.forward}\n")
                    writer.write(f"{hash_rev} {row.reverse}\n")

            with open(template_path, mode="r") as handle:
                template_xml = handle.read()

            # WARNING: sample alias is assumed to be the first three fields
            sample_alias = row.sample_alias
            exp_alias = f"{project_name}-{sample_alias}-{experiment_type}"

            template_xml = template_xml\
                .replace("$$$EXPERIMENT_ALIAS$$$",  exp_alias)\
                .replace("$$$FORWARD_R1_FASTQ$$$",  row.forward)\
                .replace("$$$FORWARD_R1_MD5SUM$$$", hash_for)\
                .replace("$$$REVERSE_R2_FASTQ$$$",  row.reverse)\
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


def parse_args():
    parser = argparse.ArgumentParser("preprocess_sequences")
    parser.add_argument("-i", "--metadata_path", 
                        help="Excel file containing the metadata for the sequences.",
                        type=str
                        )
    parser.add_argument("-w", "--WGS_samples_dir",
                        help="Directory containing the sequences to submit.",
                        type=str
                        )
    parser.add_argument("-a", "--AMP_samples_dir",
                        help="Directory containing the 16S sequences to submit.",
                        type=str
                        )
    parser.add_argument("-m", "--mapping_WGS",
                        help="Table containing rawreads filename (forward and reverse) and sample_alias for WGS",
                        type=str,)
    parser.add_argument("-k", "--mapping_AMP",
                        help="Table containing rawreads filename (forward and reverse) and sample_alias for AMPLICON",
                        type=str,)
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

    return parser.parse_args()


if __name__ == "__main__":
    main()
