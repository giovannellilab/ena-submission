# ena-submission

Compilation of utilities for the ENA submission


## Installation

```bash
# Create and activate environment
conda create -n ena -y
conda activate ena

# Install dependencies
conda install bs4 openpyxl -y
```


## Concepts

ENA requires the following workflow to programmatically submit your reads to ENA Archive

1) Registering samples

Any sample, thoguht as a unit of biological material (DNA) must be registered as a sample.
Each sample must be correlated with metadata (sampling location,type of sample,ecc..).
This information must be compiled prior registration in a google sheet 

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

## Workflow

1) Registering smaples
'''python

python step1_register_samples.py

'''
    - Register Samples --> sample receipt
    - Outputs -->

2) Uploading raw reads files
'''python

python step2_upload_files.py

'''

    - Uploads 16_S forward/reverse.fastq.gz
    - Uploads Metagenomes forward/reverse.fastq.gz

3) Registering Experiments-Runs Objects
'''python

python step3_register_objects.py 

'''

----------