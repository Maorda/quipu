from abc import ABC, abstractmethod
from pathlib import Path

class BaseWorkspaceLayout(ABC):
    @abstractmethod
    def get_paths(self, base_dir: Path) -> dict[str, Path]:
        pass