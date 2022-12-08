import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv


class BasicConfig:
    def __init__(self, default_values: Dict[str, Any] = {}, directory_keys: List[str] = [], required: List[str] = [],
                 env_file=".env"):
        self.config = {}
        self.default_values = default_values
        self.directory_keys = directory_keys
        self.required_keys = required
        self._env_file = env_file
        self._load_config()

    def _load_config(self):
        # read out existing os environment
        load_dotenv(self._env_file)
        self.config = {}

        # apply defaults for missing config params
        for key in self.default_values:
            val = os.getenv(key)
            if key in self.required_keys and val is None:
                raise EnvironmentError(f"You need to provide an environment variable specifying {key}")
            self.config[key] = self.default_values[key] if val is None else val

        # check that all directories exist
        for dir_type in self.directory_keys:
            self._create_directory(dir_type)

    def get_config_value(self, config_key: str, default_value: Optional[Any] = None) -> Optional[Any]:
        if config_key in self.config:
            return self.config.get(config_key, default_value)

        # read fresh from environment
        val = os.getenv(config_key)
        # store in local cache and return
        self.config[config_key] = val
        return val

    def _create_directory(self, config_key=str):
        if self.config.get(config_key, None) is None:
            return
        current_dir = self.config[config_key]
        if not os.path.isdir(current_dir):
            os.mkdir(current_dir)
