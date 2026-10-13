from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class FileStorage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...
    def delete(self, key: str) -> None: ...


class LocalFileStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir.resolve()

    def _path(self, key: str) -> Path:
        path = (self._base / key).resolve()
        if self._base not in path.parents:  # blocks path traversal like ../../x
            raise ValueError("Invalid storage key")
        return path

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


@lru_cache
def get_storage() -> FileStorage:
    return LocalFileStorage(get_settings().storage_dir)