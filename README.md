# ENA-submission

Compilation of utilities for the programmatic ENA submission of RAW sequenced data

You have just received your newly sequenced biological material and you are scared to loose you precious and expensive data by a faulty hard disk or crippled PC'
That is quite a hot potato to handle but luckily for you and me there is the ENA or Europena Nucleotide Archive, which is the answer you were looking for! 
Long storage, geographically redundant and FREE! In other words, your data are secured forever, in most of the chances.
  
More info at [ENA:guidelines](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html)


## Installation

```bash
# Create and activate environment
conda env create -f environment.yml
conda activate ena
```
## Concepts

Before diving further in the technicalities, i would like you to know that ENA implements quite a convoluted relationhsip between different intities that we will define below, which is not trivial at a first glance, but you will understand and appreciate their reasons afterwards.  

[lin image]

The above image represents simplified diagram of the objects's relationship your data needs to satisfy in order to be secured in the ENA database.  

### Biological sample
The Giovannelli Lab, works prominently with environemntal microbial data, therefore we assign to the label biological sample any DNA that is extracted from it.
ENA asks you to 'endowe' with information this sample, to better characterize its origin. To this purpose, the SAMPLE object exists. Which can be tought as
standalone Object in the ENA database, to which we are going to associate or relate at least other two objects in a moment.  
Visit [ENA:SAMPLE objecte](https://ena-docs.readthedocs.io/en/latest/submit/samples/programmatic.html#the-sample-object) for more information


### Experimental object
Is the second object, and describes the type of 'sequencing experiment' conducted on your biological samples. It points directly to the sample and says: 'Was it seqeunced for WGS? 16s analysis? ITS or 18S?'. You must append this information, in addition to the machinery and library protocol used.ENA is very strict! Luckily for you, there are already two pre-compiled XML files, with this informations. You are free to modify them according to the specifics of your comapny sequencing platform!
NOTE: There cane more than one experiemnt object pointing to the same SAMPLE, since in our lab we already do multiple sequencing on the same biological data.  
Visit [ENA experiemnt object](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html#create-the-run-and-experiment-xml) for more information

### Run object
The third object is represented by the RUN. this object is strictly related to its experiment and contains infromation solely related to your files (yes your TESSORO ). This contains actual file namings wioth their computed checksum!  
Visit [ENA run object](https://ena-docs.readthedocs.io/en/latest/submit/reads/programmatic.html#create-the-run-and-experiment-xml) for more information

In general, you first register your biological samples enriched with all the information possible

## Workflow

ENA requires the following workflow to programmatically submit your reads to ENA Archive

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

2) Uploading file reads
ENA requires the raw read files to be trimmed/clean prior upload. IN our case we are going to use clean data
already pre-processed by the sequencing company.
Moreover, for each file .fastq.gz, an MD5 checksum must be computed and saved for the next step
With this procedure, data are submitted in the 'ENA upload area', where can stay up to 2 months prior deletion.
Therefore, we must 'push' these files from this stage area to a permament storage by registering the relationship between these files
and the experiments to which are associated and their MD5 checksums.



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
