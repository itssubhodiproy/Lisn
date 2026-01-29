"""
Configuration management for Lisn.

Handles loading, saving, and validating configuration from ~/.config/lisn/config.yaml
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


# Default config directory
CONFIG_DIR = Path.home() / ".config" / "lisn"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


@dataclass
class AudioConfig:
    """Audio recording settings."""
    sample_rate: int = 16000  # 16kHz for Whisper
    channels: int = 1  # Mono
    device: Optional[str] = None  # Default audio device




@dataclass
class ApiConfig:
    """Groq API settings."""
    api_key: str = ""
    whisper_model: str = "whisper-large-v3-turbo"
    llm_model: str = "openai/gpt-oss-20b"


@dataclass
class Config:
    """Main configuration for Lisn."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    api: ApiConfig = field(default_factory=ApiConfig)

    @classmethod
    def get_config_path(cls) -> Path:
        """Return the path to the config file."""
        return CONFIG_FILE

    @classmethod
    def load(cls) -> "Config":
        """
        Load configuration from file.
        Creates default config if file doesn't exist.
        """
        if not CONFIG_FILE.exists():
            config = cls()
            config.save()
            return config

        with open(CONFIG_FILE, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary."""
        audio_data = data.get("audio", {})
        api_data = data.get("api", {})

        return cls(
            audio=AudioConfig(
                sample_rate=audio_data.get("sample_rate", 16000),
                channels=audio_data.get("channels", 1),
                device=audio_data.get("device"),
            ),
            api=ApiConfig(
                api_key=api_data.get("api_key", ""),
                whisper_model=api_data.get("whisper_model", "whisper-large-v3-turbo"),
                llm_model=api_data.get("llm_model", "openai/gpt-oss-20b"),
            ),
        )

    def save(self) -> None:
        """Save configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        data = {
            "audio": {
                "sample_rate": self.audio.sample_rate,
                "channels": self.audio.channels,
                "device": self.audio.device,
            },
            "api": {
                "api_key": self.api.api_key,
                "whisper_model": self.api.whisper_model,
                "llm_model": self.api.llm_model,
            },
        }

        with open(CONFIG_FILE, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def validate(self) -> list[str]:
        """
        Validate the configuration.
        Returns a list of error messages (empty if valid).
        """
        errors = []

        # Validate audio settings
        if self.audio.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            errors.append(f"Invalid sample_rate: {self.audio.sample_rate}")
        if self.audio.channels not in [1, 2]:
            errors.append(f"Invalid channels: {self.audio.channels}")

        # Validate API settings
        if not self.api.api_key:
            errors.append("API key is not set. Run 'lisn setup' to configure.")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0
