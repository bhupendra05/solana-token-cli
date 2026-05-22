"""Rich terminal display for token data."""
from __future__ import annotations

from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from solana_token.token import TokenAccount, TokenInfo

console = Console()
LAMPORTS = 1_000_000_000


def shorten(s: str, n: int = 8) -> str:
    if len(s) <= n * 2 + 3:
        return s
    return f"{s[:n]}…{s[-n:]}"


def sol(lamports: int) -> str:
    return f"{lamports / LAMPORTS:.6f} SOL"


def render_token_info(info: TokenInfo) -> None:
    has_mint_auth = bool(info.mint_authority)
    has_freeze_auth = bool(info.freeze_authority)
    console.print(
        Panel(
            f"[bold yellow]{info.supply:,.{info.decimals}f}[/] total supply\n"
            f"[dim]Decimals:[/] {info.decimals}\n"
            f"[dim]Mint authority:[/] {'[green]' + shorten(info.mint_authority) + '[/]' if has_mint_auth else '[red]Revoked (fixed supply)[/]'}\n"
            f"[dim]Freeze authority:[/] {'[yellow]' + shorten(info.freeze_authority) + '[/]' if has_freeze_auth else '[dim]None[/]'}\n"
            f"[dim]Status:[/] {'[green]Initialized[/]' if info.is_initialized else '[red]Not initialized[/]'}",
            title=f"[bold cyan]Mint[/] [dim]{shorten(info.mint)}[/]",
            border_style="cyan",
        )
    )


def render_token_accounts(accounts: List[TokenAccount], owner: str) -> None:
    if not accounts:
        console.print("[dim]No SPL token accounts found.[/]")
        return

    table = Table(
        title=f"Token Accounts for {shorten(owner)}",
        box=box.ROUNDED, show_lines=True, expand=True,
    )
    table.add_column("Mint", style="cyan")
    table.add_column("Account", style="dim")
    table.add_column("Balance", justify="right")
    table.add_column("Decimals", justify="right")

    for acct in sorted(accounts, key=lambda a: -a.amount):
        table.add_row(
            shorten(acct.mint),
            shorten(acct.address),
            f"[bold]{acct.amount:,.{acct.decimals}f}[/]",
            str(acct.decimals),
        )
    console.print(table)


def render_largest_holders(holders: list[dict], mint: str) -> None:
    table = Table(title=f"Largest Holders — {shorten(mint)}", box=box.ROUNDED)
    table.add_column("Rank", justify="right", style="dim")
    table.add_column("Account")
    table.add_column("Balance", justify="right")
    table.add_column("% Supply", justify="right")

    # Compute total for percentages
    amounts = [float(h.get("uiAmount") or 0) for h in holders]
    total = sum(amounts) or 1

    for i, h in enumerate(holders, 1):
        amt = float(h.get("uiAmount") or 0)
        pct = amt / total * 100
        table.add_row(
            str(i),
            shorten(h.get("address", ""), 10),
            f"{amt:,.4f}",
            f"{pct:.1f}%",
        )
    console.print(table)
