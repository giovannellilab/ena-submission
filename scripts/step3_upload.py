
import re

import os

import argparse

import pandas as pd

import bs4 as bs

import subprocess

import glob



def uploader(
        file_list: list ,
        interactive: bool = False

)-> None:

    #NOTA: ftp will ask for each file confirmation, to disable interactive mode, issue the prompt command or
    # OR use -i flag in ftp command
    #save credentials in netrc file 
    if interactive:
        mput_command =  "mput "+ " ".join(file_list) + "; bye"
    else:

        #mput_command = "set cmd:interactive no; mput " + " ".join(file_list) + "; bye"
        mput_command = "mput -c " + " ".join(file_list) + "; bye"

    ftp_connection = [
        "lftp",
        "webin2.ebi.ac.uk",
        "-e", mput_command
    ]
    
    # try:
    #     print(f"Submitting files to ENA..")
    #     subprocess.run(ftp_connection, check=True, text=True)
    #     print(f"End connection")

    # except subprocess.CalledProcessError as e:
    #     print(f"Error:", {e.stderr})
    
    return None




def main(
        sample_path: str,
        experiment_type: str
):

    if not os.path.exists(sample_path):
        print(f'Error {sample_path} not correctly inputed')
        return 

    if experiment_type == '16S':
        sample_path = os.path.join(sample_path,'16_S')
    elif experiment_type == 'Metagenomics' or experiment_type == 'metagenomics':
        sample_path = os.path.join(sample_path,'Metagenomics')

    #iterating over subdirectories
    subdirs = [d for d in os.listdir(sample_path)
    if os.path.isdir(os.path.join(sample_path, d))]

    

    #INFO for both 16_S and Meta
    #receipt information:
    # sample_accession --> receipt.xml or pandas dataframe
    # experiment name  --> 
    # name_file_1  --> directory
    # name_file_2  --> directory

    # Example HYD22-Sample_alias-experiment_type

    df = pd.DataFrame(columns=['sample_alias','sample_accession','experiment_name','uploaded file 1','uploaded file 2','checksum_file_1','checksum_file_2'])

    cols =['experiment_alias','forward_r1_fastq','reverse_r2_fastq','forward_r1_md5sum','reverse_r2_md5sum']


    for subdir in sorted(subdirs):
        subdir_path = os.path.join(sample_path, subdir)
        print(f"\n Processing directory: {subdir}")
        print()

        #regex = r"^(?!.*raw).*_[12]\.{fastq,fq}\.gz$"
        regex = r"*_[12]\.fastq\.gz$"

        all_files = glob.glob(os.path.join(subdir_path,"*.gz"))
        matching_files = [f for f in all_files if re.match(regex, f)]
        print(len(matching_files))
        print(matching_files)


        if not matching_files:
            print(f"Error: No files matching the pattern {regex} were found.")
            return False   
        else:
            for f in matching_files:
                size_mb = os.path.getsize(f) / (1024 * 1024)
                print(f" - {f} ({size_mb:.2f} MB)")
            
            uploader(
                sample_path= args.sample_dir,
                file_list = matching_files
                )


    return None




    
        
if __name__ == "__main__":

    parser = argparse.ArgumentParser("Uploading raw sequences")
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
    parser.add_argument(
        "-s", "--sample_dir",
        help = "Directory containing sample subdirectories for the submisssion",
        type=str
    )
    args = parser.parse_args()


    main(
        sample_path = args.sample_dir,
        experiment_type=args.experiment_type
    )
    