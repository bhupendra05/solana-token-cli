# solana-token-cli

> Create, mint, transfer, and manage Solana SPL tokens from your terminal. No browser, no wallet UI — just your keypair and a command.

![Python](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Solana](https://img.shields.io/badge/chain-Solana-9945FF)

```
$ sol-token create --decimals 9 --name "MyToken" --symbol MTK --cluster devnet

✓ Token created!
Mint address:  7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
Decimals:      9
Cluster:       devnet
Explorer:      https://explorer.solana.com/address/7xKXtg2C...?cluster=devnet

Next steps:
  Create token account: sol-token create-account 7xKXtg2C...
  Mint tokens:          sol-token mint 7xKXtg2C... 1000000
  View info:            sol-token info 7xKXtg2C...
```

## Features

- **Create SPL tokens** — set decimals, freeze authority, mint authority
- **Mint tokens** — mint to your wallet or any recipient
- **Transfer tokens** — send to any Solana wallet address
- **Burn tokens** — permanently remove tokens from supply
- **Revoke mint authority** — permanently fix total supply
- **Token info** — supply, authorities, decimals, largest holders
- **List accounts** — all SPL token accounts for any wallet
- **Airdrop SOL** — request devnet/testnet SOL for testing
- **Keygen** — generate a new Solana keypair
- **Works on devnet, testnet, and mainnet**

## Prerequisites

The `create`, `mint`, `transfer`, `burn`, and `revoke-mint` commands use the [spl-token CLI](https://spl.solana.com/token) for transaction building. Install it with:

```bash
# Install Solana CLI (includes spl-token)
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"
```

Read-only commands (`info`, `accounts`) work with no external tools.

## Installation

```bash
git clone https://github.com/bhupendra05/solana-token-cli.git
cd solana-token-cli
pip install -e .
```

## Setup

### Option A — Use existing Solana CLI keypair

If you already have `~/.config/solana/id.json` from the Solana CLI, it's picked up automatically.

### Option B — Generate a new keypair

```bash
sol-token keygen --output my-wallet.json
```

### Option C — Environment variable

```bash
export SOLANA_PRIVATE_KEY="[12,34,56,...]"   # JSON array from keypair file
```

### Fund your wallet on devnet

```bash
sol-token airdrop --cluster devnet       # 1 SOL
sol-token airdrop --amount 2 --cluster devnet
```

---

## Usage

### Create a token

```bash
# Devnet (for development)
sol-token create --decimals 9 --cluster devnet

# With name and symbol (informational)
sol-token create --decimals 6 --name "USD Coin" --symbol USDC --cluster devnet

# Mainnet
sol-token create --decimals 9 --cluster mainnet

# Custom RPC (Helius, QuickNode, etc.)
sol-token create --rpc https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
```

### Create a token account

```bash
sol-token create-account <MINT_ADDRESS> --cluster devnet
```

### Mint tokens

```bash
# Mint to your own wallet
sol-token mint <MINT_ADDRESS> 1000000 --cluster devnet

# Mint to a specific recipient
sol-token mint <MINT_ADDRESS> 500 --recipient <WALLET_ADDRESS>
```

### Transfer tokens

```bash
sol-token transfer <MINT_ADDRESS> 100 <RECIPIENT_WALLET> --cluster devnet
```

### Burn tokens

```bash
sol-token burn <TOKEN_ACCOUNT_ADDRESS> 50 --cluster devnet
```

### Revoke mint authority (fix supply permanently)

```bash
# WARNING: irreversible
sol-token revoke-mint <MINT_ADDRESS> --cluster devnet
```

### View token info

```bash
# Basic info
sol-token info <MINT_ADDRESS> --cluster devnet

# With largest holders
sol-token info <MINT_ADDRESS> --holders

# JSON output
sol-token info <MINT_ADDRESS> --json | jq '.supply'
```

### List token accounts

```bash
# Your own accounts
sol-token accounts --cluster devnet

# Any wallet
sol-token accounts <WALLET_ADDRESS> --cluster mainnet
```

---

## Full Workflow Example (Devnet)

```bash
# 1. Generate keypair
sol-token keygen --output dev-wallet.json

# 2. Get devnet SOL
sol-token airdrop --keypair dev-wallet.json

# 3. Create token
sol-token create --decimals 9 --keypair dev-wallet.json --cluster devnet
# → Mint: AbcD...xyz

# 4. Mint 1,000,000 tokens
sol-token mint AbcD...xyz 1000000 --keypair dev-wallet.json --cluster devnet

# 5. Check info
sol-token info AbcD...xyz --holders --cluster devnet

# 6. Transfer some to another wallet
sol-token transfer AbcD...xyz 1000 <RECIPIENT> --keypair dev-wallet.json

# 7. Fix supply permanently
sol-token revoke-mint AbcD...xyz --keypair dev-wallet.json
```

## Keypair Security

- **Never** commit keypair files to git — the `.gitignore` blocks `*.json` keypair files
- For production, use `SOLANA_PRIVATE_KEY` env var (not a file on disk)
- On mainnet, use a hardware wallet via Ledger + Solana CLI: `--keypair usb://ledger`

## Project Structure

```
solana-token-cli/
├── solana_token/
│   ├── cli.py        # Click CLI — all commands
│   ├── token.py      # SPL token operations (wraps spl-token CLI)
│   ├── rpc.py        # Pure JSON-RPC client
│   ├── keypair.py    # Keypair load/generate/sign
│   ├── metadata.py   # Metaplex token metadata helpers
│   └── display.py    # Rich terminal output
├── requirements.txt
└── setup.py
```

## License

MIT © bhupendra05
