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

3) Registering Experiement - Run Objects
Another important relationship in the ENA workflow is the Experiment -Run object association which refers to a single sample.
This allows to have different experiements and runs to be associated to the same SAMPLE (biological material)
For exmaple in our Lab, is common to have 2 Exp-run objects for each sample: 16S and Metagenomes experiments.
Moreover, an Experiemtn could have more than one run associated to it, referring to the sequencing pits (during sequencing), 
In our case, we will ahve just one run for experiment.

## Workflow

1) Registering smaples

python ena_submission.py 

    - Outputs --> sample receipt

2) Uploading samples

----------