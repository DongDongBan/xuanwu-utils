import warnings
import pyedflib
import os

import __main__
if "DEBUG_MODE" in dir(__main__): DEBUG_MODE = __main__.DEBUG_MODE
else:                             DEBUG_MODE = False

class EdfReaderContextManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.edf_reader = None

    def __enter__(self):
        if not os.path.isfile(self.filepath):
            warnings.warn(f"File not found: {self.filepath}")
            return None
        try:
            self.edf_reader = pyedflib.EdfReader(self.filepath)
        except Exception as e:
            warnings.warn(f"An error occurred while opening the EDF file: {e}")
            self.edf_reader = None
        return self.edf_reader

    def __exit__(self, exc_type, exc_value, traceback):
        if self.edf_reader is not None:
            try:
                self.edf_reader.close()
            except Exception as e:
                warnings.warn(f"An error occurred while closing the EDF file: {e}")
        if exc_type or exc_value or traceback: warnings.warn(f"获取{self.filepath}的过程中出现以下错误{exc_type}: {exc_value}]\n{traceback}")
        return True  


