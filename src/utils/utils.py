import yaml
from dotenv import load_dotenv

load_dotenv()


def load_yaml_config(config_file: str):
    try:
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            return config
    except FileNotFoundError:
        raise Exception(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        raise Exception(f"Error parsing the YAML file: {e}")

# ADD ALL THE UTILS FUNCTIONS HERE