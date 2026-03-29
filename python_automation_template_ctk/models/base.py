import os
from pathlib import Path
import json
import time


class SettingsModel:
    """A generic model for saving settings"""

    def __init__(self, fields, file_name: str):
        self.fields = fields
        file_name = file_name
        self.dir_path = "settings"
        file_path = os.path.join(self.dir_path, file_name)

        self.file = Path(file_path)
        self.load()

    def load(self):
        """Loads the values from the json to fields after validating"""
        if not self.file.exists():
            return

        with open(file=self.file, mode="r", encoding="utf-8", newline="") as fh:
            raw_values = json.load(fh)

        for key in self.fields:  # if json file key doesn't match the settings
            if key in raw_values and "value" in raw_values[key]:
                raw_value = raw_values[key]["value"]
                self.fields[key]["value"] = raw_value

    def save(self):

        # create a dir if not exists
        if not os.path.isdir(self.dir_path):
            os.makedirs(self.dir_path)
            time.sleep(1)

        with open(self.file, "w") as fh:
            json.dump(self.fields, fh, indent=4)

    def set(self, key, value):

        if key in self.fields and type(value).__name__ == self.fields[key]["type"]:
            self.fields[key]["value"] = value
        else:
            raise ValueError("Bad key or wrong variable type")
