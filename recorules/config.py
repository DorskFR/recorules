"""Configuration management."""

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "recorules" / "config.ini"


@dataclass
class Config:
    """Recoru authentication configuration."""

    recoru_contract_id: str
    recoru_auth_id: str
    recoru_password: str

    @classmethod
    def from_env(cls) -> "Config | None":
        """Load configuration from environment variables."""
        try:
            return cls(
                recoru_contract_id=os.environ["RECORU_CONTRACT_ID"],
                recoru_auth_id=os.environ["RECORU_AUTH_ID"],
                recoru_password=os.environ["RECORU_PASSWORD"],
            )
        except KeyError:
            return None

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Config | None":
        """Load configuration from file."""
        if not path.is_file():
            return None

        config = configparser.ConfigParser(interpolation=None)
        config.read(path)
        return cls(
            recoru_contract_id=config["recoru"]["contractId"],
            recoru_auth_id=config["recoru"]["authId"],
            recoru_password=config["recoru"]["password"],
        )

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        """Save configuration to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        config = configparser.ConfigParser(interpolation=None)
        config["recoru"] = {
            "authId": self.recoru_auth_id,
            "contractId": self.recoru_contract_id,
            "password": self.recoru_password,
        }
        with path.open("w") as config_file:
            config.write(config_file)
