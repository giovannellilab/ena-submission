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
        d1: dict,
        d2: dict
    )-> dict:
        
    d3 = {}
    for k,v in d1.items():
        alias = k[4:]

        if alias in d2.keys():
            d3[alias] = [d2[alias],v,k] #In order: EXP,RUN,RUN_alias
        
    return d3


def flatten_object(
    lista: list

)-> str:
    
    string_elements = []
    for item in lista:
        if isinstance(item, str):  # Direct string elements
            string_elements.append(item)
        elif isinstance(item, list):  # Flatten nested lists
            string_elements.extend([x for x in item if isinstance(x, str)])
        elif isinstance(item, dict):  # Extract values from dictionaries
            for k,v in item.items():
                if isinstance(v, str) and isinstance(k,str):
                    string_elements.append(k)
                    string_elements.append(v)
    print(string_elements)
    return string_elements



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
                     f"{project_name}_ena_object_receipt.xml"                  
                    )
    # RETRIEVING METADATA

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
                
    print(object_receipt)
    print(len(object_receipt.keys()))
    
    # RETRIEVING METADATA

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
            for file in names_files:
                f = file.get("filename")
                md5 = file.get("checksum")
                run_object[f] = md5

            run_meta[name_exp] = run_object

        exp_meta = {}
        for exp in xml_exp.find_all("EXPERIMENT"):
            exp_ref = exp.get("alias")
            descriptor = exp.find("SAMPLE_DESCRIPTOR")
            sample_accession = descriptor.get("accession")
            exp_meta[exp_ref] = sample_accession

    print(exp_meta)
    #print(next(iter(run_meta.items())))
    print(run_meta)
        #MAPPING RELATIONSHIPS
    listone = []
    # THIS THING IS AN ABOMINUM
    for key,value in object_receipt.items():
        object_relation = []
        if key in run_meta and key in exp_meta:
            object_relation.append(key) # EXP ref
            object_relation.append(exp_meta[key]) # sample accession
            object_relation.append(value) #exp and run accession numbers
            object_relation.append(run_meta[key]) # run files names and checksum

        listone.append(object_relation)

    output_list = []
    for item in listone:
        s = flatten_object(item)
        output_list.append(s)

    return  output_list

def to_sheet(
        lista: list,
        metadata_path: str,
        template_dir: str,
        experiment_type:str,
):
    cols = ['Experiment_title','Sample_alias','Experiment_accession',
            'Run_accession','Run_title','Forward_file',
            'Forward_md5','Reverse_file','Reverse_md5']
    dataframe = pd.DataFrame(columns=cols,data=lista)


    print(dataframe)


#    goolge_sheet = pd.read_csv(os.path.join(
#        template_dir, ))




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
    lista = metadata_upload(
        metadata_path = args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type,
    )

    to_sheet(
        lista = lista,
        metadata_path = args.metadata_path,
        template_dir=args.template_dir,
        experiment_type=args.experiment_type
    )

    print(f"[STEP3][+] Experiments and runs info saved to {final_receipt_path}")

    # for n,item in enumerate(lista):
    #     print(f"{n} : {lista}")

