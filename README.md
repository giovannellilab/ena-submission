# ENA-submission

Compilation of utilities for the programmatic ENA submission of RAW sequenced data

Are you ascared to loose you precious and expensive data by a faulty hard disk or crippled PC?. That is quite a hot potato to handle but luckily for you there is the ENA or Europena Nucleotide Archive, Long storage, geographically redundant and FREE! In other words, your data are secured forever, in most of the chances.
  
More info at [ENA:guidelines](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html)

## Concepts

Before diving further in the technicalities, i would like you to know that ENA implements quite a convoluted relationhsip between different intities that we will define below, which is not trivial at a first glance, but you will understand and appreciate their reasons afterwards. 

### Biological sample
The Giovannelli Lab, works prominently with environemntal microbial data, therefore we assign to the label biological sample any DNA that is extracted from it.  
ENA asks you to 'endowe' with information this sample, to better characterize its origin. To this purpose, the SAMPLE object exists. Which can be tought as standalone Object in the ENA database, to which we are going to associate or relate at least other two objects in a moment.   
Visit [ENA:SAMPLE objecte](https://ena-docs.readthedocs.io/en/latest/submit/samples/programmatic.html#the-sample-object) for more information.  
Each sample metadata must conform to the so called 'ENA checklists' of expected metadata values.
Visit [ENA:Sample Checklist](https://www.ebi.ac.uk/ena/browser/checklists) for choosing the right checklist tht best suits you submission. Moreover, these checklist are customizable and can be downloaded as a file.tsv from the 'Register sample' window within the ENA account.  


### Experimental object
Is the second object, and describes the type of 'sequencing experiment' conducted on your biological samples. It points directly to the sample and says: 'Was it seqeunced for WGS? 16s analysis? ITS or 18S?'. You must append this information, in addition to the machinery and library protocol used.ENA is very strict! Luckily for you, there are already two pre-compiled XML files, with this informations. You are free to modify them according to the specifics of your comapny sequencing platform!  NOTE: There cane more than one experiemnt object pointing to the same SAMPLE, since in our lab we already do multiple sequencing on the same biological data.  
Visit [ENA experiemnt object](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html#create-the-run-and-experiment-xml) for more information

### Run object
The third object is represented by the RUN. this object is strictly related to its experiment and contains infromation solely related to your files. This contains actual file namings wioth their computed checksum!  
Visit [ENA run object](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html#create-the-run-and-experiment-xml) for more information

In general, you first register your biological samples enriched with all the information possible

## Getting Started
Create the ena conda env
```bash
conda env create -f environment.yaml
```
First of all navigate to:  
```bash 
cd ena-submission/data
```
create and move all the requested files inside:  
```bash
mkdir $project_name
```

Before starting, it is assumed that you already have created your study in ENA [PRJEBI_Umbrella_project](https://ena-docs.readthedocs.io/en/latest/submit/study/interactive.html) within your [ENA-account](https://www.ebi.ac.uk/ena/submit/webin/login) and compiled the ENA_checklist with all the proper information. In our google drive you can find multiple ENA_submission spreadsheet, an example is given by the data/ExpID_ena_submission_ERC000025.xlsx


In addition, you will be asked to compile a mandatory TSV *sample table.tsv* (the likes used in [geomosaic_setup](https://giovannellilab.github.io/Geomosaic/commands/setup.html) ) (tab separated format) to be sure that the sequences you are about to upload are referenced to the right sample alias in your Ena_submission spreadsheet. To note, this table must be created for each different experiment!
The namings are stored under the following columns: forward (r1),reverse (r2),samples_alias. An example:

| r1              | r2              | sample_alias |
| ----------------|-----------------|--------------|
| G255_1.fastq.gz | G255_2.fastq.gz | AC_280625_F  |
| G256_1.fastq.gz | G256_2.fastq.gz | BC_200625_S  |
| G257_1.fastq.gz | G257_2.fastq.gz | LS_230625_F  |
| G258_1.fastq.gz | G258_2.fastq.gz | SF_221019_F  |
| G259_1.fastq.gz | G259_2.fastq.gz | SF_221019_S  |

In the case your forward and reverse sequence files are nested within each sample's name ( our sequenced data is returned from seq company typically in this way ), it is suggested to add a further column namedd 'sample_id' which MUST correspond at the sample directory in your folder.This will help to find each files in the correct location. In the case the 'sample_alias' corrsponds to the 'sample_id', copy and paste!

| r1              | r2              | sample_alias | sample_id |
|-----------------|-----------------|--------------|-----------|
| G255_1.fastq.gz | G255_2.fastq.gz | AC_280625_F  | G255      |
| G256_1.fastq.gz | G256_2.fastq.gz | BC_200625_S  | G256      | 
| G257_1.fastq.gz | G257_2.fastq.gz | LS_230625_F  | G257      | 
| G258_1.fastq.gz | G258_2.fastq.gz | SF_221019_F  | G258      | 
| G259_1.fastq.gz | G259_2.fastq.gz | SF_221019_S  | G259      | 

*IMPORTANT*
The table above MUST be created for each different experiment type you are willing to upload! As we usually seqeunce both WGS and 16S biological materials, these tables are requested in 2/5 STEPs below

## Writing config file
We use a config file to insert information regarding required files and directories for the submission.
You can edit this file such taht matches your ENA_checklist, your ENA metadata file, and data related paths..
- template_dir -> directory containing templates used by the scripts, mut not be changed.
- metadata_file -> absolute path to your edited ENA checklist list file
- raw_data_dir* -> absolute path to your raw sequencing data to be uploaded.
- readmapping_table_* -> absolute path to tables (see previous chapter) mapping file names to sample_aliases.
- submission_type -> defualt to ADD, you can change it to MODIFY if you wish to change already registered metadata.

A snapshot is provided.
```bash
### MAIN SETTINGS ###
# Edit this line to your projectname
project_name: PRJEB113292
# Edit this line to your template ERC ID
ena_checklist: ERC000025
template_dir: /home/edotacca/working_dir/ena-submission/data/templates
metadata_file: 
  /home/edotacca/working_dir/ena-submission/data/AEO25/AEO25_ena_submission_ERC000025.xlsx
# Defualt to ADD, you can change it to MODIFY if widh to chenge info of already registered metadata
submission_type: ADD

#### DATA-RELATED PATHS ####
# Edit to raw WGS seqeunce data folder
raw_data_dir_wgs:
# Edit to your AMPLICON sequence data folder
raw_data_dir_amp: /SERVER/sequences/vulcano_suoli/16s
#  Edit to your table mapping
readmapping_table_wgs:
# Edit to your table mapping
readmapping_table_amp: 
  /SERVER/sequences/vulcano_suoli/16s/ena-submission/data/Mapping_filenames.tsv

#### RECEIPT PATHS ####
receipt_samples_dry_run:
receipt_objects_permanent: /SERVER/sequences/vulcano_suoli/16s/ena-submission/data/PRJEB113292_ena_object_receipt_16S.xml
receipt_objects_dry_run:
receipt_samples_permanent: /home/edotacca/working_dir/ena-submission/data/AEO25/PRJEB113292_ena_samples_receipt.xml

#### EXPERIMENT DETAILS ####
SEQUENCING_YEAR: 2026
SEQUENCING_PLATFORM: ILLUMINA
SEQUENCING_INSTRUMENT_MODEL: Illumina Novaseq X Plus
SEQUENCING_LIBRARY_CONSTRUCTION_PROTOCOL: Sequencing was carried out by Novogene
  (UK). The NGS DNA Library Prep Set (Cat No.PT004). Before sequencing DNA 
  samples were quantified using a Qubit (invitrogen) dsDNA Broad Range or High 
  Sensitivity assay and visually inspected on a 1% agarose gel colored with 
  EtBr.

```

## Workflow ENA-submission/upload

The workflow  is divided into 5 mandatory steps to be executed in numerical order:
### Creating and registering sample metadata under projectID
STEP-1) Registering samples: This step is executed ONLY ONE TIME to register all your samples metadata to ENA   
*NOTE* this step allow the user to choose:  
- the registration type via: [-x, --registration_type] allowing to choose between a TEST partition for cehcking the results of your submisison  
AND permanent submission, where your smaple_aliases are registered and assoicated to an internal ID withou possibility to change.
- the submission type: [-s, --submission_type {1,2}] allowing To *ADD* the metadata (every new submission has this as default) OR *MODIFY* existant metadata;  However, samples_aliases columns cannot be modified! So be aware of this when writing them. 

```bash
python s01_create_samples_xml.py -h

usage: Register sample metadata [-h] [-s CONFIG_FILE] [-x {y,yes,n,no,null}] [-u USER_PASSWORD]
options:
  -h, --help            show this help message and exit
  -s CONFIG_FILE, --config_file CONFIG_FILE
                        config yaml file containing direcotries for the whole workflow.
  -x {y,yes,n,no,null}, --registration_type {y,yes,n,no,null}
                        Registration type: 'y' or 'yes' for permanent; 'n' or 'no' for test. Leave empty for dry run.
  -u USER_PASSWORD, --user_password USER_PASSWORD
                        User and password for the submission (e.g. user1:password1234).
```

### Create experiment type and associated run metadata for existing files
The steps 2) and 3) are executed a number of times N equal to you experiment types. Tipically you will have WGS and 16S seqeunced data, sometimes also 18S and ITS. Thus these steps MUST be repeates for all the experiments you wish to register. As pointed out above, you will provide a differetn *sample_table.tsv* for tracking each different seqeunced data.

STEP 2) Create experiments files:
```bash
python s02_create_experiment_xml.py -h

usage: Create experiments Objects [-h] [-s CONFIG_PATH] [-e {16S,WGS}]
options:
  -h, --help            show this help message and exit
  -s CONFIG_PATH, --config_path CONFIG_PATH
                        config yaml file containing direcotries for the whole workflow.
  -e {16S,WGS}, --experiment_type {16S,WGS}
                        String defining either 16S, WGS, 18S or ITS sequences
```

STEP 3) Create run files:

```bash

python s03_create_run_xml.py -h

usage: Create run objects [-h] -s CONFIG_PATH -e {16S,WGS} [-n]
options:
  -h, --help            show this help message and exit
  -s CONFIG_PATH, --config_path CONFIG_PATH
                        config yaml file containing direcotries for the whole workflow.
  -e {16S,WGS}, --experiment_types {16S,WGS}
                        String defining either 16S or WGS
  -n, --nested          If sequences files are nested within each corrispective sample dir names
```

### Uploading data files (Can be done indepdenlty BUT always before registering)

STEP 4) Upload files: is also executed a number of times N equal to your experiment types. Or in alternitive you can compile a comprehensive sample_table.tsv with all the sequences for all the experiemtnal conditions.
```bash
python s04_upload_files.py -h

usage: Uploading raw sequences [-h] [-s CONFIG_PATH] [-e {WGS,16S}] [-n] [-u USERNAME] [-i INTERACTIVE] [--dry_run]
options:
  -h, --help            show this help message and exit
  -s CONFIG_PATH, --config_path CONFIG_PATH
                        config yaml file containing direcotries for the whole workflow.
  -e {WGS,16S}, --experiment_type {WGS,16S}
                        Either 16S or metagenomics.
  -n, --nested          If sequences files are nested within each corrispective sample dir names
  -u USERNAME, --username USERNAME
                        User for the submission (e.g. user1).
  -i INTERACTIVE, --interactive INTERACTIVE
                        Whether to perform the upload in interactive mode.
  -z, --dry_run         Execute a dry_run with only printing the command
```
You can check the presence of your files in the ENA bay area with your user:password by typing:
```bash
lftp webin2.ebi.ac.uk  -u Webin-XXXXX:passw

```
### Associating Metadata Objects with Sequence files

STEP 5) Register Objects:
*NOTE* this step allow the user to choose:  
- the registration type via: [-x, --registration_type] allowing to choose between a TEST partition for cehcking the results of your submisison  
AND permanent submission, where your experiment_aliases and run_aliases are registered and assoicated to an internal ID, further mapped to the right sample in STEP1) without possibility to change.

```bash
python s05_register_object.py -h

usage: Register objects [-h] [-s CONFIG_PATH] [-e {16S,WGS}] [-u USER_PASSWORD] [-x {y,yes,n,no,null}]
options:
  -h, --help            show this help message and exit
  -s CONFIG_PATH, --config_path CONFIG_PATH
                        config yaml file containing direcotries for the whole workflow.
  -e {16S,WGS}, --experiment_type {16S,WGS}
                        String defining either 16S, WGS or both.
  -u USER_PASSWORD, --user_password USER_PASSWORD
                        User and password for the submission (e.g. user1:password1234).
  -x {y,yes,n,no,null}, --registration_type {y,yes,n,no,null}
                        Registration type: 'y' or 'yes' for permanent; 'n' or 'no' for test. Leave empty for dry run.
```
STEP 6) Parse receipts objects:
This step allows you to store all the informations for your submission & registrations in tabular data for tracking purposes
```bash
python s06_gather_receipts.py -h

usage: Register objects [-h] [-s CONFIG_PATH] [-e {16S,WGS} [{16S,WGS} ...]]
options:
  -h, --help            show this help message and exit
  -s CONFIG_PATH, --config_path CONFIG_PATH
                        config yaml file containing direcotries for the whole workflow.
  -e {16S,WGS} [{16S,WGS} ...], --experiment_types {16S,WGS} [{16S,WGS} ...]
                        String defining either 16S, WGS or both.


## Workflow ENA-data-download
STEP 1) Download data from ENA database

```bash
python3 ena_aspera_download.py -h

usage: ena_aspera_download.py [-h] -l TABLE --preset PRESET -o OUTDIR [-t THREADS] [-r RETRIES] [--host HOST] [--rate-kbps RATE_KBPS] [--log-level {error,warn,info,debug}]
                              [--dry-run]

ena_aspera_download.py

Bulk-downloads ENA read files via Aspera (ascli), in parallel.

Accepts TWO possible kinds of input table, and figures out which one you
gave it automatically:

  1. A table that already has run_accession + fastq_ftp columns
     (e.g. straight from the ENA Portal API, or already converted).

  2. A raw Webin Reports Service file report, with id + fileName columns
     (id = run accession, fileName = your original submitted filename).
     In this case, the fastq_ftp path is built for you automatically,
     using ENA's "submitted files" convention:
         vol1/run/<first 6 chars of accession>/<accession>/<fileName>

Either way, only two things matter for the download step: which run each
file belongs to, and its path on the server. Everything else in your file
is ignored.

Prerequisites (must already be done once, outside this script):
  1. aspera-cli installed (`gem install aspera-cli`) and
     `ascli config transferd install` run successfully.
  2. A configured ascli preset, e.g. for public data:
       ascli conf preset update era --url=ssh://fasp.sra.ebi.ac.uk:33001 \
         --username=era-fasp \
         --ssh-keys=@ruby:Fasp::Installation.instance.bypass_keys.first \
         --ts=@json:'{"target_rate_kbps":300000}'

Usage:
    python3 ena_aspera_download.py --table runs.tsv --preset era --outdir ./downloads --threads 4
    python3 ena_aspera_download.py --table runs.tsv --preset era --outdir ./downloads --dry-run

options:
  -h, --help            show this help message and exit
  -l TABLE, --table TABLE
                        Input table: run_accession+fastq_ftp, or id+fileName
  --preset PRESET       ascli preset name, e.g. 'era' (passed as -P<preset>)
  -o OUTDIR, --outdir OUTDIR
                        Output directory (one subfolder per accession)
  -t THREADS, --threads THREADS
                        Parallel downloads (default: 4)
  -r RETRIES, --retries RETRIES
                        Retries per file (default: 3)
  --host HOST           Host to use when building paths from id+fileName (default: ftp.sra.ebi.ac.uk)
  --rate-kbps RATE_KBPS
                        Optional per-transfer rate cap in kbps
  --log-level {error,warn,info,debug}
                        ascli's own log verbosity (default: info)
  --dry-run             List planned downloads without transferring

```

'''

<!-- STEP-1) Registering samples

1) Registering samples

Any unit of biological material (DNA) must be registered 'figuratively' as a sample. it does not matter if that sample has either been sequenced as WGS or 16S or both. it counts as ONE!
Each sample must be correlated with metadata (sampling location,type of sample,ecc..).
To this purpose a google sheet [link image] must be compiled with all this informations. PLease do NOT leave empty spaces or will be interpreted as errors.
The script will take care of reading the google doc and writing its ionfromation as a XML file to be sent to ENA for registration:

```bash

python step1_register_samples.py -i SUBMISSION TABLE -t DIR METADATA -u USER:PASSWORD -x TYPE of REGISTRATION


```

If the SAMPLES registration is succesfull, it will provide a receipt.xml file with very important information regarding your SAMPLE:
- ENA accession: starting with ERS.. ; its an alternative accession in ENA for mapping purposes.
- BioSAMPLE accession: Starting with SAMEA.., it is used in journal pubblication
- sample ALIAS: it is an alias recognizable by you and decided while compiling the google sheet



IMPORTANT: you can decide wether registering the SAMPLEs for TEST production or directly to the permanent archive.
We suggeest you to first try to register them in the TEST, since they will be erased after 24 hours if some info is not correct.


```bash

python step1_register_samples.py -i data/HYD22/HYD22_ena_submission.xlsx -t data/templates/ -u User:password -x ['y', 'yes', 'n', 'no', None]

```

2) Upoading file reads
ENA requires the raw read files to be trimmed/clean prior upload. IN our case we are going to use clean data
already pre-processed by the sequencing company.
Moreover, for each file .fastq.gz, an MD5 checksum must be computed and saved for the next step
With this procedure, data are uploaded in the 'ENA upload area' or 'BAY area', where can stay up to 2 months prior deletion.
Therefore, we must 'push' these files from this stage area to a permament storage by registering the relationship between these files, their checksums
and the experiments and samples to which they are associated.

## Handling Errors
During your submission, many things can go wrong, most of the time erros arise during the STEP3, due to not correct checksums associated with you files. please have a look at ENA website for reference [Common-run-submission errors](https://ena-docs.readthedocs.io/en/latest/faq/runs.html#common-run-submission-errors)

One of the most common errors while uploading your data is the [Invalid File Checksum](https://ena-docs.readthedocs.io/en/latest/faq/runs.html#error-invalid-file-checksum). Which occurs when the checksum provide by you while creating the run object in the STEP1 does not match with the checksum computed by ENA. In this case i suggest you re-compute the checksum of the file in question and compare it with the one provided by you on the ***run.xml*** file. If it match:
- Remove the faulty sequence in the BAY area by:
```bash

lftp webin2.ebi.ac.uk <user:password> 

```

```bash
rm BS_231222_F_FGTH22_R1.fastq.gz
```
And reupload the single one with: 
```bash
mput '/absolute_path/BS_231222_F_FGTH22_R1.fastq.g'
```



3) Registering Experiement - Run Objects
Another important relationship in the ENA workflow is the Experiment -Run object association which refers to a single sample.
This allows to have different experiements and runs to be associated to the same SAMPLE (biological material)
For exmaple in our Lab, is common to have 2 Exp-run objects for each sample: 16S and Metagenomes experiments.
Moreover, an Experiemtn could have more than one run associated to it, referring to the sequencing pits (during sequencing), 
In our case, we will have just one run for experiment.
Once the RUN and EXPERIMENT .xml files are created, we can register the previously uploaded files permanently.

Sometimes things can go south pretty fast, it NOT uncommon to fail the registration for the RUN object


## Pre-processing

1) Preparing samples and directories

Before start ensures that samples directory names and file names match with the sample_alias provided in the google sheet template.
This will be helpful in retrieving files and their experiment from ENA  in the future. 
Most of the times smaples are named as G* followed by [0-9] such as G129, G230, G23 ecc. In this case, provide a tsv file (E.G map_samples_campaign.tsv ) specifying the
old/current direcotry and files names and new ones:

Current	New
G68	KJ_230721_F
G69	SJ_230730_F
G70	NR_230731_F
G71	TR_230731_F
G72	KJ_230721_S
G73	SJ_230730_S
G74	NR_230731_S
G75	TR_230731_S
G76	GRP_230724_S
G77	KJ_230721_BG
G78	SJ_230730_BG
G79	NR_230731_BG
G80	TR_230731_BG

The follwoing script will take care of this not so nice procedure:

```bash

python  pre-processing-dir.py -s /media/edotacca/Thor/raw_sequences/HYD22 -e 16S OR WGS -f data/HYD22/map_samples_HYD22.tsv

```

## ENA - steps

1) Registering smaples

```bash

python step1_register_samples.py -i data/HYD22/HYD22_ena_submission.xlsx -t data/templates/ -u User:password

```
    - Register Samples -> sample receipt
    - Outputs ->

2) Uploading raw reads files
```bash

python step2_upload_files.py -s /media/edotacca/Thor/raw_sequences/HYD22 -i data/HYD22/HYD22_ena_submission.xlsx -t data/templates/ -u User:password

```
    - Uploads 16_S forward/reverse.fastq.gz
    - Uploads Metagenomes forward/reverse.fastq.gz

3) Registering Experiments-Runs Objects
```bash

python step3_register_objects.py -i data/HYD22/HYD22_ena_submission.xlsx -t data/templates/ -u User:password

```

'''