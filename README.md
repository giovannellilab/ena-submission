# ENA-submission

Compilation of utilities for the programmatic ENA submission of RAW sequenced data

Are you ascared to loose you precious and expensive data by a faulty hard disk or crippled PC?. That is quite a hot potato to handle but luckily for you there is the ENA or Europena Nucleotide Archive, Long storage, geographically redundant and FREE! In other words, your data are secured forever, in most of the chances.
  
More info at [ENA:guidelines](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html)


## Installation

```bash
# Create and activate environment
conda env create -f environment.yaml
conda activate ena
```
## Concepts

Before diving further in the technicalities, i would like you to know that ENA implements quite a convoluted relationhsip between different intities that we will define below, which is not trivial at a first glance, but you will understand and appreciate their reasons afterwards.  

[link image]

The above image represents simplified diagram of the objects's relationship your data needs to satisfy in order to be secured in the ENA database.  

### Biological sample
The Giovannelli Lab, works prominently with environemntal microbial data, therefore we assign to the label biological sample any DNA that is extracted from it.
ENA asks you to 'endowe' with information this sample, to better characterize its origin. To this purpose, the SAMPLE object exists. Which can be tought as standalone Object in the ENA database, to which we are going to associate or relate at least other two objects in a moment.  
Visit [ENA:SAMPLE objecte](https://ena-docs.readthedocs.io/en/latest/submit/samples/programmatic.html#the-sample-object) for more information
Each sample metadata must conform to the so called 'ENA checklists' of expected metadata values.
Visit [ENA:Sample Checklist](https://www.ebi.ac.uk/ena/browser/checklists) for choosing the right checklist tht best suits you submission. Moreover, these checlsits are customizable and can be downloaded as a file.tsv from the 'Register sample' window within the ENA account.


### Experimental object
Is the second object, and describes the type of 'sequencing experiment' conducted on your biological samples. It points directly to the sample and says: 'Was it seqeunced for WGS? 16s analysis? ITS or 18S?'. You must append this information, in addition to the machinery and library protocol used.ENA is very strict! Luckily for you, there are already two pre-compiled XML files, with this informations. You are free to modify them according to the specifics of your comapny sequencing platform!
NOTE: There cane more than one experiemnt object pointing to the same SAMPLE, since in our lab we already do multiple sequencing on the same biological data.  
Visit [ENA experiemnt object](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html#create-the-run-and-experiment-xml) for more information

### Run object
The third object is represented by the RUN. this object is strictly related to its experiment and contains infromation solely related to your files (yes your TESSORO ). This contains actual file namings wioth their computed checksum!  
Visit [ENA run object](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html#create-the-run-and-experiment-xml) for more information

In general, you first register your biological samples enriched with all the information possible

## Getting Started
Once you have created you PRJEBI Umbrella project in ENA, you will get a PRJID which must be inserted

Before starting, it is assumed that you already have created your study in ENA [PRJEBI_Umbrella_project](https://ena-docs.readthedocs.io/en/latest/submit/study/interactive.html) within your account and compiled the ENA_checklist with all the proper information.  you can find multiple ENA_submission spreadsheet at the following link: () 
And an real example: ()


In addition, you will be asked to compile a mandatory TSV *sample table.tsv* (the likes used in [geomosaic_setup](https://giovannellilab.github.io/Geomosaic/commands/setup.html) ) (tab separated format) to be sure that the sequences you are about to upload are referenced to the right sample alias in your Ena_submission spreadsheet. To note, this table must be created for each different experiment!
The namings are stored under the following columns: forward,reverse,samples_alias. An example:

| forward         | reverse         | sample_alias |
| ----------------|-----------------|--------------|
| G255_1.fastq.gz | G255_2.fastq.gz | AC_280625_F  |
| G256_1.fastq.gz | G256_2.fastq.gz | BC_200625_S  |
| G257_1.fastq.gz | G257_2.fastq.gz | LS_230625_F  |
| G258_1.fastq.gz | G258_2.fastq.gz | SF_221019_F  |
| G259_1.fastq.gz | G259_2.fastq.gz | SF_221019_S  |

In the case your forward and reverse sequence files are nested within each sample's name ( our sequenced data is returned from seq company typically in this way ), it is suggested to add a further column namedd 'sample_id' which MUST correspond at the sample directory in your folder.This will help to find each files in the correct location. 

| forward         | reverse         | sample_alias | sample_id |
|-----------------|-----------------|--------------|-----------|
| G255_1.fastq.gz | G255_2.fastq.gz | AC_280625_F  | G255      |
| G256_1.fastq.gz | G256_2.fastq.gz | BC_200625_S  | G256      | 
| G257_1.fastq.gz | G257_2.fastq.gz | LS_230625_F  | G257      | 
| G258_1.fastq.gz | G258_2.fastq.gz | SF_221019_F  | G258      | 
| G259_1.fastq.gz | G259_2.fastq.gz | SF_221019_S  | G259      | 


## Workflow

The workflow  is divided into 5 mandatory steps to be executed in numerical order:
### Creating and registering sample metadata under projectID
-   STEP-1) Registering samples: This step is executed once to register all your samples metadata to ENA 
	*NOTE* this step allow the use to choose the registration type via: [-x, --registration_type]

```bash
python s01_create_samples_xml.py -h

usage: preprocess_sequences [-h] [-i METADATA_PATH] [-t TEMPLATE_DIR] [-s {1,2}] [-x {y,yes,n,no,null}] [-u USER_PASSWORD]
options:
  -h, --help            show this help message and exit
  -i, --metadata_path METADATA_PATH
                        Excel file containing the metadata for the sequences.
  -t, --template_dir TEMPLATE_DIR
                        Directory containing the templates for the submission.
  -s, --submission_type {1,2}
                        Submission type: -type 1 for ADD mode; -type 2 fpr MODIFY mode
  -x, --registration_type {y,yes,n,no,null}
                        Submission type: 'y' or 'yes' for permanent; 'n' or 'no' for test. Leave empty for dry run.
  -u, --user_password USER_PASSWORD
                        User and password for the submission (e.g. user1:password1234).
```

### Create experiment type and associated run metadata for existing files
The steps 2) and 3) are executed a number of times N equal to you experiment types. Tipically you will have WGS and 16S seqeunced data, sometimes also 18S and ITS. Thus these steps MUST be repeates for all the experiments you wish to register.

-   STEP 2) Create experiments files:


-   STEP 3) Create run files:
```bash
python s02_create_experiment_xml.py -h

usage: preprocess_sequences [-h] [-e {16S,WGS,ITS}] [-i METADATA_PATH] [-t TEMPLATE_DIR] [-r RECIPE] [-m MAPPING_WGS] [-k MAPPING_AMP]
options:
  -h, --help            show this help message and exit
  -e, --experiment_type {16S,WGS,ITS}
                        String defining either 16S, WGS or ITS sequences
  -i, --metadata_path METADATA_PATH
                        Excel file containing the metadata for the sequences.
  -t, --template_dir TEMPLATE_DIR
                        Directory containing the templates for the submission.
  -r, --recipe RECIPE   XML File obtained from the s01 script.
  -m, --mapping_WGS MAPPING_WGS
                        Table containing rawreads filename (forward and reverse) and sample_alias for WGS
  -k, --mapping_AMP MAPPING_AMP
                        Table containing rawreads filename (forward and reverse) and sample_alias for AMPLICON
```

### Uploading data files (Can be done indepdenlty BUT always before registering)

-   STEP 4) Upload files: is also executed a number of times N equal to your experiment types. Or in alternitive you can compile a comprehensive sample_table.tsv with all the sequences for all the experiemtnal conditions.
```bash
python s04_upload_files.py -h

usage: Uploading raw sequences [-h] [-e {WGS,16S}] [-w FILES_SAMPLES_DIR] [-a AMP_SAMPLES_DIR] [-n] [-m MAPPING_WGS] [-k MAPPING_AMP] [-u USERNAME] [-i INTERACTIVE] [--dry_run]
options:
  -h, --help            show this help message and exit
  -e, --experiment_type {WGS,16S}
                        Either 16S or metagenomics.
  -w, --files_samples_dir FILES_SAMPLES_DIR
                        Directory containing the sequences to submit.
  -a, --AMP_samples_dir AMP_SAMPLES_DIR
                        Directory containing the 16S sequences to submit.
  -n, --nested          If sequences files are nested within each corrispective sample dir names
  -m, --mapping_WGS MAPPING_WGS
                        Table containing rawreads filename (forward and reverse), sample_alias for your reads AND/or sample_id if nested
  -k, --mapping_AMP MAPPING_AMP
                        Table containing rawreads filename (forward and reverse) and sample_alias for AMPLICON
  -u, --username USERNAME
                        Username for the submission.
  -i, --interactive INTERACTIVE
                        Whether to perform the upload in interactive mode.
  --dry_run             Execute a dry_run with only printing the command
```
### Associating Metadata Objects with Sequence files

-   STEP 5) Register Objects: this step is:
	*NOTE* this step allow the use to choose the registration type via: [-x, --registration_type]
```bash
python s05_register_object.py -h
usage: Register objects [-h] [-i METADATA_PATH] [-t TEMPLATE_DIR] [-e EXPERIMENT_TYPES] [-u USER_PASSWORD] [-s {1,2}] [-x {y,yes,n,no,null}]
options:
  -h, --help            show this help message and exit
  -i, --metadata_path METADATA_PATH
                        Excel file containing the metadata for the sequences.
  -t, --template_dir TEMPLATE_DIR
                        Directory containing the templates for the submission.
  -e, --experiment_types EXPERIMENT_TYPES
                        String defining either 16S, WGS or both.
  -u, --user_password USER_PASSWORD
                        User and password for the submission (e.g. user1:password1234).
  -s, --submission_type {1,2}
                        Submission type: -type 1 for ADD mode; -type 2 fpr MODIFY mode
  -x, --registration_type {y,yes,n,no,null}
                        Registration type: 'y' or 'yes' for permanent; 'n' or 'no' for test. Leave empty for dry run.
```



STEP-1) Registering samples

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
    - Register Samples --> sample receipt
    - Outputs -->

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

----------
