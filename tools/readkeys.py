"""
save .keys file in project root dir
.gitignore  add `.keys`
"""
from pathlib import Path
import os


class SecretKeys:
    _cur_path = Path(__file__).parent
    _project_path = _cur_path.parent
    _key_path = _project_path / ".keys"
    _keys = {}

    @classmethod
    @property
    def key_path(cls):
        return cls._key_path

    @classmethod
    def _read_keys(cls):
        if not cls.key_path.exists():
            # create empty file
            cls.key_path.touch()
        with open(cls.key_path, "r") as f:
            for line in f:
                cols = line.split("=", 1)
                if len(cols) < 2:
                    cls._keys[cols[0].strip()] = ""
                    continue
                else:
                    cls._keys[cols[0].strip()] = cols[1].strip()
                    continue

    @classmethod
    @property
    def keys(cls):
        if not cls._keys:
            cls._read_keys()
        return cls._keys

    @classmethod
    def get(cls, key, default=""):
        return os.getenv(key, cls.keys.get(key, default))


if __name__ == "__main__":
    print(SecretKeys.keys)
    print(SecretKeys.get("INFLUXDB_TOKEN"))
