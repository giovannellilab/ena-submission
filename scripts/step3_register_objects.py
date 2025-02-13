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
    experiment_type: str,
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
        f"{project_name}_ena_experiment_{experiment_type}.xml"
    )
    run_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_run_{experiment_type}.xml"
    )
    output_path = os.path.join(
        metadata_dir,
        f"{project_name}_ena_object_receipt_{experiment_type}.xml"
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
        d1: dict,
        d2: dict
    )-> dict:
        
    d3 = {}
    for k,v in d1.items():
        alias = k[4:]

        if alias in d2.keys():
            d3[alias] = [d2[alias],v,k] #In order: EXP,RUN,RUN_alias
        
    return d3



def metadata_upload(
    metadata_path: str,
    template_dir: str,
    experiment_type: str

)-> list:
    
    # associate 
    # - EXP accession: ERX13763087
    # - RUN accession: ERR14361731

    project_name = os.path.basename(metadata_path).split("_")[0]
    metadata_path = os.path.dirname(metadata_path)

    run_path = os.path.join(metadata_path,
                    f"{project_name}_ena_run_{experiment_type}.xml"
                    )
    experiment_path = os.path.join(metadata_path,
                    f"{project_name}_ena_experiment_{experiment_type}.xml"
                    )
    object_receipt_path = os.path.join(metadata_path,
                     f"{project_name}_ena_object_receipt_{experiment_type}.xml"                  
                    )
    sample_receipt_path = os.path.join(metadata_path,
                     f"{project_name}_ena_samples_receipt.xml"                  
                    )
    # RETRIEVING METADATA from sample_receipt.xml file
    with open(sample_receipt_path, mode="r") as handle:
        xml_data = bs.BeautifulSoup(handle, "xml")

        samples =  {}
        for sample in xml_data.find_all("SAMPLE"):
            accession = sample.get('accession')   #ERS10
            glab_accession = sample.get('alias')  #oURS
            get = sample.find('EXT_ID')           
            samea_accession = get.get('accession') # SAMEA10
            samples[accession] = [glab_accession,samea_accession]
        print(f'Samples:{next(iter(samples.items()))}')

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

    object_receipt = mapping(runs,exps)
    print(f'Onject:{next(iter(object_receipt.items()))}')
    
    # RETRIEVING METADATA from experiment.xml AND run.xml

    with open(run_path, mode="r") as read1, open(experiment_path, mode="r") as read2:
        xml_run = bs.BeautifulSoup(read1, "xml")
        xml_exp = bs.BeautifulSoup(read2, "xml")

        run_meta = {}
        for run in xml_run.find_all("RUN"):
            exp_ref = run.find("EXPERIMENT_REF")
            name_exp = exp_ref.get("refname")
            files = run.find("FILES")
            names_files = files.find_all("FILE")

            run_object = {}
            run_file = []
            for file in names_files:
                f = file.get("filename")
                md5 = file.get("checksum")
                run_file.append(f)
                run_file.append(md5)

            run_meta[name_exp] = run_file

        exp_meta = {}
        for exp in xml_exp.find_all("EXPERIMENT"):
            exp_ref = exp.get("alias")
            descriptor = exp.find("SAMPLE_DESCRIPTOR")
            sample_accession = descriptor.get("accession")
            exp_meta[exp_ref] = sample_accession

    print(f'run_meta:{next(iter(run_meta.items()))}')
    print(f'exp_meta:{next(iter(exp_meta.items()))}')

    WGS_df = []
    Amplicon_df  = []
    # 1) iterate over samples (ERS)
    for k,values in samples.items():
        # 2) retrieve experiments (16S or WGS or both) from XML (using ERS)
        if k in exp_meta.values():

            exp_aliases = [key for key,val in exp_meta.items() if val == k]  #if there are going to be at max two keys with same value
            # 3) iterate over experiments
            for exp_alias in exp_aliases:
                
                # 4) retrieve runs from XML (using ERX)
                if exp_alias in run_meta.keys():
                    run_info = run_meta[exp_ref]
                    print(run_info)
                if exp_alias in object_receipt.keys():
                    receipt = object_receipt[exp_ref]

                row = pd.Series({
                        "sample_alias": values[0],#Glab
                        "sample_accession": values[1], #SAmea
                        "experiment_alias": exp_ref,
                        "alternative_accession":k,
                        "experiment_ref":receipt[0],
                        "run_ref": receipt[1],
                        "run_alias":receipt[2],
                        "forward_file":run_info[0],
                        "reverse_file":run_info[2],
                        "forward_checksum":run_info[1],
                        "reverse_checksum":run_info[3]
                    }).to_frame().T

                if exp_ref.split('-')[-1] == 'WGS':
                    WGS_df.append(row)
                elif exp_ref.split('-')[-1] == '16S':
                    Amplicon_df.append(row)

    return pd.concat(WGS_df)


def to_sheet(
        dataframe: pd.DataFrame,
        metadata_path: str,
        template_dir: str,
        experiment_type:str,
)-> str:
    
    print(dataframe)
    project_name = os.path.basename(metadata_path).split("_")[0]

    output_dir = os.path.dirname(metadata_path)
    output_path = os.path.join(output_dir,
            f'{project_name}_details_{experiment_type}.csv')


    cols_study = ['expID','study_accession']
    study_data = [project_name,'PRJEB67767']

    cols_ngs = ['sequencing_platform','sequencing_instrument','library_source',
            'library_selection','library_strategy']
    if experiment_type == '16S':
        ngs_data = ['ILLUMINA',' Illumina NovaSeq 6000','METAGENOMIC','PCR','AMPLICON']
    else:
        ngs_data = ['ILLUMINA','Illumina NovaSeq 6000','GENOMIC','RANDOM','WGS']
    
    for col,value in zip(cols_study,study_data):
        dataframe[col] = value
    for col, value in zip(cols_ngs, ngs_data):
        dataframe[col] = value

    #re-ordering the columns
    dataframe = dataframe[cols_study + dataframe.columns.drop(cols_study).tolist()]
    dataframe.to_csv(output_path, index = False) 

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

    final_receipt_path = register_objects(
        metadata_path=args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type,
        user_password=args.user_password
    )
    print(f"[STEP3][1] Experiments and runs info saved to {final_receipt_path}")
    
    df_wgs = metadata_upload(
        metadata_path = args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type,
    )

    sheets = [('WGS',df_wgs)]
    for exp in sheets:

        details_submission = to_sheet(
            dataframe=exp[1],
            metadata_path = args.metadata_path,
            template_dir=args.template_dir,
            experiment_type=exp[0]
        )

    print(f"[STEP3][2] Metadata written to {details_submission}")