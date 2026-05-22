"""
SPL Token operations via Solana JSON-RPC.

Uses spl-token CLI under the hood when available for transaction building,
with a pure-Python fallback for read operations and basic mint creation.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from solana_token.keypair import Keypair
from solana_token.rpc import SolanaRPC


LAMPORTS_PER_SOL = 1_000_000_000


@dataclass
class TokenInfo:
    mint: str
    decimals: int
    supply: float
    supply_raw: int
    freeze_authority: Optional[str]
    mint_authority: Optional[str]
    is_initialized: bool


@dataclass
class TokenAccount:
    address: str
    mint: str
    owner: str
    amount: float
    amount_raw: int
    decimals: int


def _require_spl_token() -> str:
    """Return path to spl-token binary or raise helpful error."""
    path = shutil.which("spl-token")
    if not path:
        raise RuntimeError(
            "spl-token CLI not found.\n"
            "Install with: sh -c \"$(curl -sSfL https://release.solana.com/stable/install)\"\n"
            "Or with cargo: cargo install spl-token-cli"
        )
    return path


def _run_spl(args: list[str], cluster_url: str, keypair_path: str) -> dict:
    """Run spl-token CLI and return parsed JSON output."""
    spl = _require_spl_token()
    cmd = [spl] + args + [
        "--url", cluster_url,
        "--keypair", keypair_path,
        "--output", "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"spl-token error: {result.stderr.strip() or result.stdout.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}


def create_token(
    keypair: Keypair,
    rpc: SolanaRPC,
    decimals: int = 9,
    enable_freeze: bool = False,
) -> str:
    """Create a new SPL token mint. Returns mint address."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        keypair.to_file(f.name)
        kp_path = f.name

    try:
        args = ["create-token", "--decimals", str(decimals)]
        if not enable_freeze:
            args.append("--disable-freeze")
        result = _run_spl(args, rpc.url, kp_path)
        return result.get("commandOutput", {}).get("address") or result.get("address") or result.get("raw", "")
    finally:
        os.unlink(kp_path)


def create_account(keypair: Keypair, rpc: SolanaRPC, mint: str) -> str:
    """Create an associated token account for the keypair. Returns account address."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        keypair.to_file(f.name)
        kp_path = f.name
    try:
        result = _run_spl(["create-account", mint], rpc.url, kp_path)
        return result.get("commandOutput", {}).get("address") or result.get("address") or result.get("raw", "")
    finally:
        os.unlink(kp_path)


def mint_tokens(
    keypair: Keypair,
    rpc: SolanaRPC,
    mint: str,
    amount: float,
    recipient: Optional[str] = None,
) -> str:
    """Mint tokens to an account. Returns signature."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        keypair.to_file(f.name)
        kp_path = f.name
    try:
        args = ["mint", mint, str(amount)]
        if recipient:
            args.append(recipient)
        result = _run_spl(args, rpc.url, kp_path)
        return result.get("signature") or result.get("raw", "")
    finally:
        os.unlink(kp_path)


def transfer_tokens(
    keypair: Keypair,
    rpc: SolanaRPC,
    mint: str,
    amount: float,
    recipient: str,
    fund_recipient: bool = True,
) -> str:
    """Transfer tokens to a recipient. Returns signature."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        keypair.to_file(f.name)
        kp_path = f.name
    try:
        args = ["transfer", mint, str(amount), recipient]
        if fund_recipient:
            args.append("--fund-recipient")
        result = _run_spl(args, rpc.url, kp_path)
        return result.get("signature") or result.get("raw", "")
    finally:
        os.unlink(kp_path)


def burn_tokens(keypair: Keypair, rpc: SolanaRPC, account: str, amount: float) -> str:
    """Burn tokens from an account. Returns signature."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        keypair.to_file(f.name)
        kp_path = f.name
    try:
        result = _run_spl(["burn", account, str(amount)], rpc.url, kp_path)
        return result.get("signature") or result.get("raw", "")
    finally:
        os.unlink(kp_path)


def revoke_mint_authority(keypair: Keypair, rpc: SolanaRPC, mint: str) -> str:
    """Revoke mint authority — makes supply permanently fixed. Returns signature."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        keypair.to_file(f.name)
        kp_path = f.name
    try:
        result = _run_spl(["authorize", mint, "mint", "--disable"], rpc.url, kp_path)
        return result.get("signature") or result.get("raw", "")
    finally:
        os.unlink(kp_path)


# ── Read-only operations via RPC (no spl-token CLI needed) ────────────────────

def get_token_info(rpc: SolanaRPC, mint: str) -> TokenInfo:
    """Get mint metadata via RPC."""
    account = rpc.get_account_info(mint)
    if not account:
        raise ValueError(f"Mint not found: {mint}")

    parsed = account.get("data", {}).get("parsed", {}).get("info", {})
    supply_info = rpc.get_token_supply(mint)

    return TokenInfo(
        mint=mint,
        decimals=parsed.get("decimals", 0),
        supply=float(supply_info.get("uiAmount") or 0),
        supply_raw=int(supply_info.get("amount", 0)),
        freeze_authority=parsed.get("freezeAuthority"),
        mint_authority=parsed.get("mintAuthority"),
        is_initialized=parsed.get("isInitialized", False),
    )


def get_token_accounts(rpc: SolanaRPC, owner: str) -> list[TokenAccount]:
    """List all SPL token accounts owned by an address."""
    raw = rpc.get_token_accounts_by_owner(owner)
    accounts = []
    for item in raw:
        info = item["account"]["data"]["parsed"]["info"]
        ta = info.get("tokenAmount", {})
        accounts.append(TokenAccount(
            address=item["pubkey"],
            mint=info.get("mint", ""),
            owner=info.get("owner", ""),
            amount=float(ta.get("uiAmount") or 0),
            amount_raw=int(ta.get("amount", 0)),
            decimals=int(ta.get("decimals", 0)),
        ))
    return accounts
