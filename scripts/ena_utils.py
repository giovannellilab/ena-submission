from ruamel.yaml import YAML

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


def get_config_variable(data: dict, key):
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
