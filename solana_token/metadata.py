"""
Token metadata helpers — read/write Metaplex token metadata on-chain.
Uses metaboss CLI when available for writes; RPC for reads.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional

from solana_token.rpc import SolanaRPC

METAPLEX_PROGRAM = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"


@dataclass
class TokenMetadata:
    mint: str
    name: str
    symbol: str
    uri: str
    seller_fee_basis_points: int = 0
    creators: list = None
    is_mutable: bool = True


def _try_metaboss(args: list[str], keypair_path: str, rpc_url: str) -> str:
    """Run metaboss if available, return stdout. Raises if not installed."""
    mb = shutil.which("metaboss")
    if not mb:
        raise RuntimeError(
            "metaboss not found. Install with:\n"
            "  cargo install metaboss\n"
            "Or download from https://github.com/samuelvanderwaal/metaboss"
        )
    cmd = [mb] + args + ["--keypair", keypair_path, "--rpc", rpc_url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"metaboss error: {result.stderr.strip()}")
    return result.stdout.strip()


def get_metadata(rpc: SolanaRPC, mint: str) -> Optional[TokenMetadata]:
    """Fetch Metaplex token metadata via RPC DAS (getAsset)."""
    try:
        result = rpc._call("getAsset", [mint])
        if not result:
            return None
        content = result.get("content", {})
        meta = content.get("metadata", {})
        return TokenMetadata(
            mint=mint,
            name=meta.get("name", ""),
            symbol=meta.get("symbol", ""),
            uri=content.get("json_uri", ""),
        )
    except Exception:
        # Fallback: try getTokenMetadata (Token-2022)
        try:
            result = rpc._call("getTokenMetadata", [mint])
            if result:
                return TokenMetadata(
                    mint=mint,
                    name=result.get("name", ""),
                    symbol=result.get("symbol", ""),
                    uri=result.get("uri", ""),
                )
        except Exception:
            pass
    return None


def build_metadata_json(
    name: str,
    symbol: str,
    description: str = "",
    image_url: str = "",
    external_url: str = "",
    attributes: list[dict] | None = None,
) -> dict:
    """Build a standard token metadata JSON object (Metaplex standard)."""
    meta = {
        "name": name,
        "symbol": symbol,
        "description": description,
        "image": image_url,
        "external_url": external_url,
        "attributes": attributes or [],
        "properties": {
            "files": [{"uri": image_url, "type": "image/png"}] if image_url else [],
            "category": "fungible",
        },
    }
    return meta


def upload_metadata_to_arweave_public(metadata: dict) -> str:
    """
    Upload metadata JSON to nftstorage.link (free, IPFS-backed).
    Returns the IPFS gateway URL.
    """
    import requests
    nft_storage_key = os.environ.get("NFT_STORAGE_KEY", "")
    if not nft_storage_key:
        # Fallback: use a temporary pastebin-style service for devnet testing
        resp = requests.post(
            "https://api.nft.storage/upload",
            headers={"Content-Type": "application/json"},
            data=json.dumps(metadata),
            timeout=30,
        )
        if resp.ok:
            cid = resp.json()["value"]["cid"]
            return f"https://nftstorage.link/ipfs/{cid}"
    raise ValueError(
        "Set NFT_STORAGE_KEY env var for metadata upload.\n"
        "Get a free key at https://nft.storage"
    )
