# ENA submission script

# This script performs the following steps programmatically:

# 1. Sample registration
#   1.1. Load sample metadata
#   1.2. Create the sample.xml file for registering the samples
#   1.3. Register the samples in ENA according to that metadata

# 2. Experiment registration
# 2.1. Parse the receipt after sample registration
# 2.2. Register the experiments according to that information

# 3. Run registration
# 3.1 iterate through sample directories for computing checksums
# 3.2 Register the runs according to the information

# ---------------------------------------------------------------------------- #

import re

import os

import argparse

import pandas as pd

import bs4 as bs

import subprocess


def load_metadata(metadata_path: str) -> pd.DataFrame:

    metadata_df = pd.read_excel(
        metadata_path,
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
    metadata_path: str,
    template_dir: str
) -> str:

    metadata_df = load_metadata(metadata_path)

    template_path = os.path.join(
        template_dir,
        "samples.xml"
    )

    samples_all = []

    # Create a template for each sample
    for _, row in metadata_df.iterrows():

        # Avoid errors while formatting numbers
        row = row.astype(str)

        with open(template_path, mode="r") as handle:
            template_xml = handle.read()

        template_xml = template_xml\
            .replace("$$$SAMPLE_TITLE$$$", row["sample_title"])\
            .replace("$$$SAMPLE_ALIAS$$$", row["sample_alias"])\
            .replace("$$$ENV_TAX_ID$$$", row["tax_id"])\
            .replace("$$$ENV_SCI_NAME$$$", row["scientific_name"])\
            .replace("$$$PROJECT_NAME$$$", row["project name"])\
            .replace("$$$COLLECTION_DATE$$$", row["collection date"])\
            .replace("$$$LATITUDE$$$", row["geographic location (latitude)"])\
            .replace("$$$LONGITUDE$$$", row["geographic location (longitude)"])\
            .replace(
                "$$$ENV_BROAD$$$",
                row["broad-scale environmental context"]
            )\
            .replace("$$$ENV_LOCAL$$$", row["local environmental context"])\
            .replace("$$$ENV_MEDIUM$$$", row["environmental medium"])\
            .replace("$$$ELEVATION$$$", row["elevation"])\
            .replace(
                "$$$LOC$$$",
                row["geographic location (country and/or sea)"]
            )

        samples_all += [template_xml]

    samples_all = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<SAMPLE_SET>" + "\n" + \
        "\n".join(samples_all) + "\n" + \
        "</SAMPLE_SET>" + "\n"

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_samples.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(samples_all)

    return output_path


def register_samples(
    samples_xml_path: str,
    template_dir: str,
    user_password: str
) -> str:

    # Define input XML files
    submission_path = os.path.join(
        template_dir,
        "submission.xml"
    )

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(samples_xml_path).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(samples_xml_path),
        f"{project_name}_ena_samples_receipt.xml"
    )

    # Build the command
    command = [
        "curl",
        "-u", user_password,
        "-F", f"SUBMISSION=@{submission_path}", 
        "-F", f"SAMPLE=@{samples_xml_path}",
        "-F", "LAUNCH=YES",
        "-o", output_path,
        "https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/"
    ]

    # # Execute the command
    # try:
    #     subprocess.run(command, check=True, text=True)
    #     print(f"Response successfully written to {output_path}")

    # except subprocess.CalledProcessError as e:
    #     print(f"Error:", {e.stderr})

    return output_path


def parse_samples_receipt(
    receipt_path: str,
    metadata_path: str
) -> pd.DataFrame:

    # Programmatically assign study ID
    metadata_df = load_metadata(metadata_path)

    # Load receipt
    with open(receipt_path, mode="r") as handle:
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


def create_experiment(
    receipt_path: str,
    metadata_path: str,
    template_dir: str,
    experiment_type: str
) -> str:

    template_path = os.path.join(
        template_dir,
        f"experiment_{experiment_type}.xml"
    )

    receipt_df = parse_samples_receipt(
        receipt_path=receipt_path,
        metadata_path=metadata_path
    )

    experiment_all = []

    for _, row in receipt_df.iterrows():
        row = row.astype(str)

        with open(template_path, mode="r") as handle:
            template_xml = handle.read()

        template_xml = template_xml\
            .replace("$$$STUDY_ID$$$", row["project_id"])\
            .replace("$$$EXPERIMENT_ALIAS$$$", row["sample_alias"])\
            .replace("$$$SAMPLE_ACCESSION$$$", row["sample_accession"])

        experiment_all += [template_xml]

    experiment_all = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<EXPERIMENT_SET>" + "\n" + \
        "\n".join(experiment_all) + "\n" + \
        "</EXPERIMENT_SET>" + "\n"

    # WARNING: project name is assumed to be in the first field of the path
    project_name = os.path.basename(metadata_path).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_experiment.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(experiment_all)

    return output_path


def compute_checksum(subdir_path: str) -> dict:

    #computing checksums of for-rev cleaned reads: *_[12].fastq.gz
    os.chdir(subdir_path)
    exp_alias = subdir_path.split('/')[-1]
    print(exp_alias)
    bash_command = "for f in *_[12].fastq.gz; do md5sum $f; done > checksums.txt"

    try:
        subprocess.run(bash_command, shell=True, check=True, executable="/bin/bash")
        print(f"Successfully generated checksums.txt in {subdir_path}")

        checksum_file = os.path.join(subdir_path,'checksums.txt')


        files, checksums= [],[]
        
        #excludes raw reads: such TA_221020_S_EU.raw_2.fastq.gz
        regex = r"^(?!.*raw).*_[12]\.fastq\.gz$"

        with open(checksum_file,'r') as reader:
                for line in reader:

                    if re.search(regex,line):

                        line = line.strip()
                        [md5,id] = line.split()
                        files.append(id)
                        checksums.append(md5)
                        #files.append((id,md5))
                print(files)
                print(checksums)


        sample = {
            'experiment_alias' : exp_alias,'forward_r1_fastq' : files[0],
                     'reverse_r2_fastq' :  files[1],'forward_r1_md5sum' : checksums[0],
                     'reverse_r2_md5sum' : checksums[1] }


    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

    return sample


def create_run(
    sample_path: str,
    metadata_path: str,
    template_dir: str,
    experiment_type: str
) -> str:
    
    if not os.path.exists(sample_path):
        print(f'Error {sample_path} not correctly inputed')
        return
  
    #iterating over subdirectories
    subdirs = [d for d in os.listdir(sample_path) 
    if os.path.isdir(os.path.join(sample_path, d))]

    #setting dataframe
    df_run = pd.DataFrame(columns = ['experiment_alias','forward_r1_fastq','reverse_r2_fastq',
                                 'forward_r1_md5sum','reverse_r2_md5sum'])
    
    for subdir in sorted(subdirs):
        subdir_path = os.path.join(sample_path, subdir)
        print(f"\nProcessing directory: {subdir}")
        
        #computes paired-end cehcksums for each file in a subdirecotry (SAMPLE)
        #create a dataframe
        id_5dm_samples = compute_checksum(subdir_path=subdir_path)
        df_run.loc[len(df_run)] = id_5dm_samples
        
    #         f"experiment_{run_type}.xml"
    
        template_path = os.path.join(
            template_dir,f'run_template_{experiment_type}.xml'
        )
    

    run_all = []

    for _, row in df_run.iterrows():
        row = row.astype(str)

        with open(template_path, mode="r") as handle:
            template_xml = handle.read()

        template_xml = template_xml\
            .replace("$$$STUDY_ID$$$", row["experiment_alias"])\
            .replace("$$$EXPERIMENT_ALIAS$$$", row["experiment_alias"])\
            .replace("$$$FORWARD_R1_FASTQ$$$", row["forward_r1_fastq"])\
            .replace("$$$FORWARD_R1_MD5SUM$$$", row["forward_r1_md5sum"])\
            .replace("$$$REVERSE_R2_FASTQ$$$", row["reverse_r2_fastq"])\
            .replace("$$$REVERSE_R2_MD5SUM$$$", row["reverse_r2_md5sum"])

        run_all += [template_xml]

    run_all = \
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
        "<RUN_SET>" + "\n" + \
        "\n".join(run_all) + "\n" + \
        "</RUN_SET>" + "\n"
    
    print('\n')
    #change it absed on you metadata path

    project_name = os.path.basename(metadata_path).split("_")[0]
    output_path = os.path.join(
        os.path.dirname(metadata_path),
        f"{project_name}_ena_run_{experiment_type}.xml"
    )
    with open(output_path, mode="w") as handle:
        handle.write(run_all)


    return df_run,output_path


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

    samples_xml_path = create_samples_file(
        metadata_path=args.metadata_path,
        template_dir=args.template_dir
    )

    receipt_path = register_samples(
        samples_xml_path=samples_xml_path,
        template_dir=args.template_dir,
        user_password=args.user_password
    )

    experiment_path = create_experiment(
        receipt_path=receipt_path,
        metadata_path=args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type
    )

    run_path = create_run(
        samples_xml_path=samples_xml_path,
        metadata_path=args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type
    )