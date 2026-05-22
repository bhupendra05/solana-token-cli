"""Solana JSON-RPC client — pure requests, no SDK needed."""
from __future__ import annotations

import os
from typing import Any, Optional

import requests

MAINNET = "https://api.mainnet-beta.solana.com"
DEVNET  = "https://api.devnet.solana.com"
TESTNET = "https://api.testnet.solana.com"

ENDPOINTS = {"mainnet": MAINNET, "devnet": DEVNET, "testnet": TESTNET}


class SolanaRPC:
    def __init__(self, cluster: str = "devnet", custom_url: Optional[str] = None):
        self.cluster = cluster
        self.url = custom_url or os.environ.get(
            "SOLANA_RPC_URL", ENDPOINTS.get(cluster, DEVNET)
        )
        self._id = 0

    def _call(self, method: str, params: list) -> Any:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": method,
            "params": params,
        }
        resp = requests.post(self.url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"RPC error [{method}]: {data['error']}")
        return data.get("result")

    # ── Core helpers ──────────────────────────────────────────────────

    def get_balance(self, pubkey: str) -> int:
        """Returns balance in lamports."""
        return self._call("getBalance", [pubkey, {"commitment": "confirmed"}])["value"]

    def get_account_info(self, pubkey: str, encoding: str = "jsonParsed") -> Optional[dict]:
        result = self._call("getAccountInfo", [pubkey, {"encoding": encoding, "commitment": "confirmed"}])
        return result.get("value")

    def get_latest_blockhash(self) -> str:
        result = self._call("getLatestBlockhash", [{"commitment": "confirmed"}])
        return result["value"]["blockhash"]

    def send_transaction(self, signed_tx_b64: str) -> str:
        """Send a base64-encoded signed transaction. Returns signature."""
        return self._call(
            "sendTransaction",
            [signed_tx_b64, {"encoding": "base64", "preflightCommitment": "confirmed"}],
        )

    def confirm_transaction(self, signature: str, max_retries: int = 30) -> bool:
        import time
        for _ in range(max_retries):
            result = self._call(
                "getSignatureStatuses",
                [[signature], {"searchTransactionHistory": True}],
            )
            statuses = result.get("value", [])
            if statuses and statuses[0]:
                status = statuses[0]
                if status.get("err"):
                    raise RuntimeError(f"Transaction failed: {status['err']}")
                if status.get("confirmationStatus") in ("confirmed", "finalized"):
                    return True
            time.sleep(2)
        raise TimeoutError(f"Transaction {signature} not confirmed after {max_retries * 2}s")

    def request_airdrop(self, pubkey: str, lamports: int = 1_000_000_000) -> str:
        """Request SOL airdrop (devnet/testnet only). Returns signature."""
        sig = self._call("requestAirdrop", [pubkey, lamports])
        return sig

    def get_token_accounts_by_owner(self, owner: str) -> list[dict]:
        result = self._call(
            "getTokenAccountsByOwner",
            [
                owner,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"},
            ],
        )
        return result.get("value", [])

    def get_token_supply(self, mint: str) -> dict:
        result = self._call("getTokenSupply", [mint])
        return result.get("value", {})

    def get_largest_token_accounts(self, mint: str) -> list[dict]:
        result = self._call("getTokenLargestAccounts", [mint])
        return result.get("value", [])
