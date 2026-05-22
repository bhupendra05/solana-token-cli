"""Keypair management — generate, load from file/env, derive PDA."""
from __future__ import annotations

import base58
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Keypair:
    pubkey: str        # base58 public key
    secret: bytes      # 64-byte secret (seed + pubkey)

    @classmethod
    def generate(cls) -> "Keypair":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        private_key = Ed25519PrivateKey.generate()
        raw_private = private_key.private_bytes_raw()
        raw_public = private_key.public_key().public_bytes_raw()
        secret = raw_private + raw_public
        pubkey = base58.b58encode(raw_public).decode()
        return cls(pubkey=pubkey, secret=secret)

    @classmethod
    def from_secret_key(cls, secret: bytes) -> "Keypair":
        """Create from 64-byte secret key."""
        pubkey = base58.b58encode(secret[32:]).decode()
        return cls(pubkey=pubkey, secret=secret)

    @classmethod
    def from_base58(cls, b58_str: str) -> "Keypair":
        secret = base58.b58decode(b58_str)
        return cls.from_secret_key(secret)

    @classmethod
    def from_file(cls, path: str) -> "Keypair":
        """Load from Solana CLI JSON keypair file (array of ints)."""
        data = json.loads(Path(path).read_text())
        secret = bytes(data)
        return cls.from_secret_key(secret)

    @classmethod
    def from_env(cls, env_var: str = "SOLANA_PRIVATE_KEY") -> "Keypair":
        """Load from environment variable (base58 or JSON array)."""
        val = os.environ.get(env_var, "")
        if not val:
            raise ValueError(f"Environment variable {env_var} not set")
        if val.startswith("["):
            secret = bytes(json.loads(val))
        else:
            secret = base58.b58decode(val)
        return cls.from_secret_key(secret)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Keypair":
        """Smart loader: env var → file path → default Solana CLI path."""
        if os.environ.get("SOLANA_PRIVATE_KEY"):
            return cls.from_env()
        target = path or os.path.expanduser("~/.config/solana/id.json")
        if Path(target).exists():
            return cls.from_file(target)
        raise FileNotFoundError(
            f"No keypair found. Provide --keypair path or set SOLANA_PRIVATE_KEY env var.\n"
            f"Generate one with: sol-token keygen"
        )

    def to_file(self, path: str) -> None:
        """Save as Solana CLI-compatible JSON keypair file."""
        Path(path).write_text(json.dumps(list(self.secret)))

    def sign(self, message: bytes) -> bytes:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        private_key = Ed25519PrivateKey.from_private_bytes(self.secret[:32])
        return private_key.sign(message)

    def __repr__(self) -> str:
        return f"Keypair(pubkey={self.pubkey[:12]}…)"
