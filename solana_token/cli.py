"""Main CLI for solana-token-cli."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.prompt import Confirm

from solana_token.display import console, render_largest_holders, render_token_accounts, render_token_info, sol, shorten
from solana_token.keypair import Keypair
from solana_token.rpc import SolanaRPC
from solana_token.token import (
    TokenInfo, burn_tokens, create_account, create_token,
    get_token_accounts, get_token_info, mint_tokens,
    revoke_mint_authority, transfer_tokens,
)

load_dotenv()

CLUSTER_HELP = "Cluster: mainnet | devnet | testnet (default: devnet)"
KEY_HELP = "Path to keypair JSON file (default: ~/.config/solana/id.json or SOLANA_PRIVATE_KEY env)"


def _rpc(cluster: str, rpc_url: str | None) -> SolanaRPC:
    return SolanaRPC(cluster=cluster, custom_url=rpc_url)


def _load_keypair(keypair: str | None) -> Keypair:
    try:
        return Keypair.load(keypair)
    except FileNotFoundError as e:
        console.print(f"[red]✗[/] {e}")
        sys.exit(1)


@click.group()
def cli():
    """sol-token — Create and manage Solana SPL tokens from your terminal."""


# ────────────────────────────────────────────────────────────────────────────
# keygen
# ────────────────────────────────────────────────────────────────────────────

@cli.command("keygen")
@click.option("--output", "-o", default="keypair.json", show_default=True)
@click.option("--show", is_flag=True, help="Print public key and base58 secret")
def keygen_cmd(output, show):
    """Generate a new Solana keypair and save to a JSON file."""
    import base58
    kp = Keypair.generate()
    kp.to_file(output)
    console.print(f"[green]✓[/] Keypair saved to [bold]{output}[/]")
    console.print(f"[dim]Public key:[/] {kp.pubkey}")
    if show:
        console.print(f"[dim]Secret (base58):[/] {base58.b58encode(kp.secret).decode()}")
    console.print(f"\n[yellow]⚠ Keep {output} secure — never commit it to git.[/]")


# ────────────────────────────────────────────────────────────────────────────
# airdrop (devnet/testnet only)
# ────────────────────────────────────────────────────────────────────────────

@cli.command("airdrop")
@click.argument("address", required=False)
@click.option("--amount", "-a", default=1.0, show_default=True, help="SOL amount")
@click.option("--keypair", "-k", default=None, help=KEY_HELP)
@click.option("--cluster", "-c", default="devnet", type=click.Choice(["devnet", "testnet"]))
@click.option("--rpc", default=None)
def airdrop_cmd(address, amount, keypair, cluster, rpc):
    """Request a SOL airdrop on devnet/testnet."""
    rpc_client = _rpc(cluster, rpc)
    if not address:
        kp = _load_keypair(keypair)
        address = kp.pubkey

    lamports = int(amount * 1_000_000_000)
    with console.status(f"Requesting {amount} SOL airdrop to {shorten(address)}…"):
        try:
            sig = rpc_client.request_airdrop(address, lamports)
            rpc_client.confirm_transaction(sig)
        except Exception as e:
            console.print(f"[red]✗ Airdrop failed:[/] {e}")
            sys.exit(1)

    balance = rpc_client.get_balance(address)
    console.print(f"[green]✓[/] Airdrop complete! New balance: [bold]{sol(balance)}[/]")
    console.print(f"[dim]Tx:[/] https://explorer.solana.com/tx/{sig}?cluster={cluster}")


# ────────────────────────────────────────────────────────────────────────────
# create
# ────────────────────────────────────────────────────────────────────────────

@cli.command("create")
@click.option("--decimals", "-d", default=9, show_default=True, help="Token decimal places (0-9)")
@click.option("--keypair", "-k", default=None, help=KEY_HELP)
@click.option("--cluster", "-c", default="devnet", show_default=True, help=CLUSTER_HELP)
@click.option("--rpc", default=None, help="Custom RPC URL")
@click.option("--freeze/--no-freeze", default=False, help="Enable freeze authority")
@click.option("--name", default=None, help="Token name (informational)")
@click.option("--symbol", default=None, help="Token symbol (informational)")
def create_cmd(decimals, keypair, cluster, rpc, freeze, name, symbol):
    """Create a new SPL token mint.

    \b
    Examples:
      sol-token create --decimals 9 --cluster devnet
      sol-token create --decimals 6 --name "My Token" --symbol MTK
    """
    kp = _load_keypair(keypair)
    rpc_client = _rpc(cluster, rpc)

    # Check balance
    balance = rpc_client.get_balance(kp.pubkey)
    if balance < 5_000_000:  # 0.005 SOL
        console.print(
            f"[red]✗ Insufficient balance:[/] {sol(balance)}\n"
            f"[dim]On devnet, run: sol-token airdrop[/]"
        )
        sys.exit(1)

    label = f"{name} ({symbol})" if name and symbol else name or "new token"
    console.print(f"[dim]Creating {label} on {cluster}…[/]")
    console.print(f"[dim]Payer: {shorten(kp.pubkey)} · Balance: {sol(balance)}[/]")

    with console.status("Sending transaction…"):
        try:
            mint_address = create_token(kp, rpc_client, decimals=decimals, enable_freeze=freeze)
        except Exception as e:
            console.print(f"[red]✗ Create failed:[/] {e}")
            sys.exit(1)

    console.print(f"\n[bold green]✓ Token created![/]")
    console.print(f"[dim]Mint address:[/] [bold cyan]{mint_address}[/]")
    console.print(f"[dim]Decimals:[/]     {decimals}")
    console.print(f"[dim]Cluster:[/]      {cluster}")
    console.print(f"[dim]Explorer:[/]     https://explorer.solana.com/address/{mint_address}?cluster={cluster}")
    console.print(
        f"\n[dim]Next steps:[/]\n"
        f"  Create token account: sol-token create-account {mint_address}\n"
        f"  Mint tokens:          sol-token mint {mint_address} 1000000\n"
        f"  View info:            sol-token info {mint_address}"
    )


# ────────────────────────────────────────────────────────────────────────────
# create-account
# ────────────────────────────────────────────────────────────────────────────

@cli.command("create-account")
@click.argument("mint")
@click.option("--keypair", "-k", default=None, help=KEY_HELP)
@click.option("--cluster", "-c", default="devnet", show_default=True)
@click.option("--rpc", default=None)
def create_account_cmd(mint, keypair, cluster, rpc):
    """Create an associated token account for a mint."""
    kp = _load_keypair(keypair)
    rpc_client = _rpc(cluster, rpc)

    with console.status(f"Creating token account for {shorten(mint)}…"):
        try:
            account = create_account(kp, rpc_client, mint)
        except Exception as e:
            console.print(f"[red]✗[/] {e}")
            sys.exit(1)

    console.print(f"[green]✓[/] Token account: [bold]{account}[/]")
    console.print(f"[dim]Explorer:[/] https://explorer.solana.com/address/{account}?cluster={cluster}")


# ────────────────────────────────────────────────────────────────────────────
# mint
# ────────────────────────────────────────────────────────────────────────────

@cli.command("mint")
@click.argument("mint_address")
@click.argument("amount", type=float)
@click.option("--recipient", "-r", default=None, help="Recipient token account or wallet (default: own account)")
@click.option("--keypair", "-k", default=None, help=KEY_HELP)
@click.option("--cluster", "-c", default="devnet", show_default=True)
@click.option("--rpc", default=None)
def mint_cmd(mint_address, amount, recipient, keypair, cluster, rpc):
    """Mint tokens to an account.

    \b
    Examples:
      sol-token mint <MINT> 1000000
      sol-token mint <MINT> 500 --recipient <WALLET_ADDR>
    """
    kp = _load_keypair(keypair)
    rpc_client = _rpc(cluster, rpc)

    with console.status(f"Minting {amount:,.0f} tokens…"):
        try:
            sig = mint_tokens(kp, rpc_client, mint_address, amount, recipient)
        except Exception as e:
            console.print(f"[red]✗ Mint failed:[/] {e}")
            sys.exit(1)

    console.print(f"[green]✓[/] Minted [bold]{amount:,.0f}[/] tokens")
    console.print(f"[dim]Signature:[/] {sig}")
    console.print(f"[dim]Explorer:[/]  https://explorer.solana.com/tx/{sig}?cluster={cluster}")


# ────────────────────────────────────────────────────────────────────────────
# transfer
# ────────────────────────────────────────────────────────────────────────────

@cli.command("transfer")
@click.argument("mint_address")
@click.argument("amount", type=float)
@click.argument("recipient")
@click.option("--keypair", "-k", default=None, help=KEY_HELP)
@click.option("--cluster", "-c", default="devnet", show_default=True)
@click.option("--rpc", default=None)
@click.option("--yes", "-y", is_flag=True)
def transfer_cmd(mint_address, amount, recipient, keypair, cluster, rpc, yes):
    """Transfer tokens to a recipient wallet."""
    kp = _load_keypair(keypair)
    rpc_client = _rpc(cluster, rpc)

    if not yes:
        if not Confirm.ask(f"Transfer [bold]{amount:,.0f}[/] tokens to [cyan]{shorten(recipient)}[/]?"):
            console.print("[dim]Aborted.[/]")
            sys.exit(0)

    with console.status("Sending transfer…"):
        try:
            sig = transfer_tokens(kp, rpc_client, mint_address, amount, recipient)
        except Exception as e:
            console.print(f"[red]✗ Transfer failed:[/] {e}")
            sys.exit(1)

    console.print(f"[green]✓[/] Transferred [bold]{amount:,.0f}[/] → {shorten(recipient)}")
    console.print(f"[dim]Signature:[/] {sig}")
    console.print(f"[dim]Explorer:[/]  https://explorer.solana.com/tx/{sig}?cluster={cluster}")


# ────────────────────────────────────────────────────────────────────────────
# burn
# ────────────────────────────────────────────────────────────────────────────

@cli.command("burn")
@click.argument("token_account")
@click.argument("amount", type=float)
@click.option("--keypair", "-k", default=None, help=KEY_HELP)
@click.option("--cluster", "-c", default="devnet", show_default=True)
@click.option("--rpc", default=None)
@click.option("--yes", "-y", is_flag=True)
def burn_cmd(token_account, amount, keypair, cluster, rpc, yes):
    """Burn tokens (permanently remove from supply)."""
    kp = _load_keypair(keypair)
    rpc_client = _rpc(cluster, rpc)

    if not yes:
        if not Confirm.ask(f"[red]Permanently burn[/] [bold]{amount:,.0f}[/] tokens from {shorten(token_account)}?"):
            console.print("[dim]Aborted.[/]")
            sys.exit(0)

    with console.status("Burning tokens…"):
        try:
            sig = burn_tokens(kp, rpc_client, token_account, amount)
        except Exception as e:
            console.print(f"[red]✗ Burn failed:[/] {e}")
            sys.exit(1)

    console.print(f"[green]✓[/] Burned [bold]{amount:,.0f}[/] tokens")
    console.print(f"[dim]Signature:[/] {sig}")


# ────────────────────────────────────────────────────────────────────────────
# revoke-mint
# ────────────────────────────────────────────────────────────────────────────

@cli.command("revoke-mint")
@click.argument("mint_address")
@click.option("--keypair", "-k", default=None, help=KEY_HELP)
@click.option("--cluster", "-c", default="devnet", show_default=True)
@click.option("--rpc", default=None)
@click.option("--yes", "-y", is_flag=True)
def revoke_mint_cmd(mint_address, keypair, cluster, rpc, yes):
    """Revoke mint authority — fixes total supply permanently.

    WARNING: This action is irreversible. No more tokens can ever be minted.
    """
    if not yes:
        console.print("[bold red]⚠ WARNING: This is irreversible![/] No more tokens can ever be minted.")
        if not Confirm.ask(f"Revoke mint authority for [bold]{shorten(mint_address)}[/]?"):
            console.print("[dim]Aborted.[/]")
            sys.exit(0)

    kp = _load_keypair(keypair)
    rpc_client = _rpc(cluster, rpc)

    with console.status("Revoking mint authority…"):
        try:
            sig = revoke_mint_authority(kp, rpc_client, mint_address)
        except Exception as e:
            console.print(f"[red]✗[/] {e}")
            sys.exit(1)

    console.print(f"[green]✓[/] Mint authority revoked. Supply is now [bold]permanently fixed[/].")
    console.print(f"[dim]Signature:[/] {sig}")


# ────────────────────────────────────────────────────────────────────────────
# info
# ────────────────────────────────────────────────────────────────────────────

@cli.command("info")
@click.argument("mint_address")
@click.option("--cluster", "-c", default="devnet", show_default=True)
@click.option("--rpc", default=None)
@click.option("--holders", is_flag=True, help="Show largest token holders")
@click.option("--json", "as_json", is_flag=True)
def info_cmd(mint_address, cluster, rpc, holders, as_json):
    """Show info about an SPL token mint."""
    rpc_client = _rpc(cluster, rpc)

    with console.status("Fetching token info…"):
        try:
            info = get_token_info(rpc_client, mint_address)
        except Exception as e:
            console.print(f"[red]✗[/] {e}")
            sys.exit(1)

    if as_json:
        click.echo(json.dumps({
            "mint": info.mint,
            "decimals": info.decimals,
            "supply": info.supply,
            "mint_authority": info.mint_authority,
            "freeze_authority": info.freeze_authority,
        }, indent=2))
        return

    render_token_info(info)

    if holders:
        with console.status("Fetching largest holders…"):
            holder_list = rpc_client.get_largest_token_accounts(mint_address)
        render_largest_holders(holder_list, mint_address)


# ────────────────────────────────────────────────────────────────────────────
# accounts
# ────────────────────────────────────────────────────────────────────────────

@cli.command("accounts")
@click.argument("owner", required=False)
@click.option("--keypair", "-k", default=None, help=KEY_HELP)
@click.option("--cluster", "-c", default="devnet", show_default=True)
@click.option("--rpc", default=None)
@click.option("--json", "as_json", is_flag=True)
def accounts_cmd(owner, keypair, cluster, rpc, as_json):
    """List all SPL token accounts for a wallet."""
    rpc_client = _rpc(cluster, rpc)

    if not owner:
        kp = _load_keypair(keypair)
        owner = kp.pubkey

    with console.status(f"Fetching token accounts for {shorten(owner)}…"):
        try:
            accounts = get_token_accounts(rpc_client, owner)
        except Exception as e:
            console.print(f"[red]✗[/] {e}")
            sys.exit(1)

    if as_json:
        click.echo(json.dumps([
            {"address": a.address, "mint": a.mint, "amount": a.amount, "decimals": a.decimals}
            for a in accounts
        ], indent=2))
        return

    render_token_accounts(accounts, owner)


def main():
    cli()


if __name__ == "__main__":
    main()
