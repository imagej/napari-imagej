from pathlib import Path

from dynaconf import Dynaconf

# Preferences settings

# The settings are in the root directory, three directories up
SETTINGS_PATH = (Path(__file__).parent / "settings.toml").resolve()

preferences = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=SETTINGS_PATH,
)
