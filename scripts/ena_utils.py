from ruamel.yaml import YAML
import os


VALID_EXPERIMENTS = ["16S","WGS","18S","ITS"]
VALID_PLATFORMS = ["ILLUMINA", "OXFORD_NANOPORE", "PACBIO_SMRT"]
# Keys that are allowed to be null/missing
OPTIONAL_KEYS = {
    "receipt_samples_dry_run",
    "receipt_objects_permanent",
    "receipt_objects_dry_run",
    "receipt_samples_permanent",
}
# MAIN KEYS
MAIN_KEYS = {
    "template_dir",
    "metadata_file",
    "submission_type"
}
# Keys that must point to existing paths
PATH_KEYS = {
    "readmapping_table_wgs",
    "raw_data_dir_wgs",
    "readmapping_table_amp",
    "raw_data_dir_amp",
}


def read_config(config_file: str):
    yaml = YAML(typ="safe")

    try:
        with open(config_file, "r") as file:
            data = yaml.load(file) or {}
    except FileNotFoundError:
        # If the file doesn't exist yet, start with a fresh dictionary
        data = {}

    with open(config_file, "r") as file:
        data = yaml.load(file)
    return data


def get_config_variable(data: dict, key, experiment_type: str = None):
    check_sanity(data, key, experiment_type)
    return data.get(key)


def write_config(config_file: str, key: str, value: str,):
    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with open(config_file, "r") as file:
            data = yaml.load(file) or {}
    except FileNotFoundError:
        # If the file doesn't exist yet, start with a fresh dictionary
        data = {}

    data[key] = value

    with open(config_file, "w") as file:
        data = yaml.dump(data, file)

    return data



def check_sanity(data: dict, key: str, experiment_type: str = None) -> None:

    submission_type = data.get("submission_type")
    if submission_type is not None and submission_type not in ["ADD", "MODIFY"]:
        raise ValueError(
            f"Invalid submission_type '{submission_type}': must be 'ADD' or 'MODIFY'."
        )

    value = data.get(key)
    is_optional = key in OPTIONAL_KEYS
    is_path_key = key in PATH_KEYS

    if value is None:
        if is_optional:
            return
        elif is_path_key:
            return
        raise KeyError(f"Config key '{key}' is missing or null in the config file.")

    if isinstance(value, str) and not value.strip():
        if is_optional:
            return
        elif is_path_key:
            return
        raise ValueError(f"Config key '{key}' is set but empty.")

    if key == "SEQUENCING_YEAR":
        try:
            year = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"SEQUENCING_YEAR '{value}' must be an integer.")
        if not (1000 <= year <= 9999):
            raise ValueError(f"SEQUENCING_YEAR '{year}' must be a 4-digit year.")

    elif key == "SEQUENCING_PLATFORM":
        if value not in VALID_PLATFORMS:
            raise ValueError(
                f"SEQUENCING_PLATFORM '{value}' is not valid. "
                f"Allowed values: {VALID_PLATFORMS}"
            )

    elif key in PATH_KEYS:
        # Experiment-type-aware required path checks
        if key == "readmapping_table_amp" and experiment_type == "16S":
            if not os.path.exists(value):
                raise FileNotFoundError(
                    f"[16S] Path for '{key}' does not exist: {value}"
                )

        elif key == "raw_data_dir_amp" and experiment_type == "16S":
            if not os.path.exists(value):
                raise FileNotFoundError(
                    f"[16S] Path for '{key}' does not exist: {value}"
                )

        elif key == "readmapping_table_wgs" and experiment_type == "WGS":
            if not os.path.exists(value):
                raise FileNotFoundError(
                    f"[WGS] Path for '{key}' does not exist: {value}"
                )

        elif key == "raw_data_dir_wgs" and experiment_type == "WGS":
            if not os.path.exists(value):
                raise FileNotFoundError(
                    f"[WGS] Path for '{key}' does not exist: {value}"
                )

        else:
            # All other PATH_KEYS (template_dir, metadata_file) — always required
            if not os.path.exists(value):
                raise FileNotFoundError(
                    f"Path for '{key}' does not exist: {value}"
                )