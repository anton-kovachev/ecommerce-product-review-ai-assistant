"""Configuration from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    ssh_host: str
    ssh_user: str
    ssh_key: str  # path to SSH private key
    ssh_key_pass: str | None
    ssh_port: int  # SSH port; defaults to 22 if OPENCART_SSH_PORT is unset
    db_host: str  # MySQL host; if empty, DB_HOSTNAME from config.php is used
    db_user: str
    db_pass: str
    db_name: str
    db_prefix: str  # table prefix; if empty, DB_PREFIX from config.php is used
    oc_root: str  # OpenCart root directory (container path for DDEV)
    storage_dir: str  # Storage directory (container path for DDEV)
    local_root: str  # Local project path (cwd for ddev commands)

    @property
    def is_ddev(self) -> bool:
        return self.ssh_host.lower() == "ddev"

    @staticmethod
    def _resolve_path(path_value: str, *, cwd_hint: str | None = None) -> str:
        """Resolve a config path relative to the repo or current working dir."""
        expanded = os.path.expanduser(path_value or "~/.ssh/id_ed25519")
        if os.path.isabs(expanded):
            return expanded

        search_roots = [
            Path(cwd_hint).resolve() if cwd_hint else None,
            Path.cwd(),
            Path(__file__).resolve().parent,
            Path(__file__).resolve().parent.parent,
            Path.home(),
        ]
        for root in search_roots:
            if root is None:
                continue
            candidate = (root / expanded).resolve()
            if candidate.exists():
                return str(candidate)

        return str((Path.cwd() / expanded).resolve())

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv(
            override=True
        )  # the documented setup flow writes .env; nothing else read it
        ssh_host = os.environ.get("OPENCART_SSH_HOST", "")
        local_root = os.environ.get("OPENCART_ROOT", "")

        if ssh_host.lower() == "ddev":
            oc_root = "/var/www/html"
            storage_dir = f"{oc_root}/system/storage"
        else:
            oc_root = local_root
            storage_dir = os.environ.get(
                "OPENCART_STORAGE", f"{oc_root}/system/storage"
            )

        ssh_key_value = os.environ.get("OPENCART_SSH_KEY", "~/.ssh/id_ed25519")
        ssh_key = cls._resolve_path(
            ssh_key_value, cwd_hint=local_root or str(Path.cwd())
        )

        return cls(
            ssh_host=ssh_host,
            ssh_user=os.environ.get("OPENCART_SSH_USER", ""),
            ssh_key=ssh_key,
            ssh_key_pass=os.environ.get("OPENCART_SSH_KEY_PASS", None),
            ssh_port=int(os.environ.get("OPENCART_SSH_PORT", "22")),
            db_host=os.environ.get("OPENCART_DB_HOST", ""),
            db_user=os.environ.get("OPENCART_DB_USER", ""),
            db_pass=os.environ.get("OPENCART_DB_PASS", ""),
            db_name=os.environ.get("OPENCART_DB_NAME", ""),
            db_prefix=os.environ.get("OPENCART_DB_PREFIX", ""),
            oc_root=oc_root,
            storage_dir=storage_dir,
            local_root=local_root,
        )
