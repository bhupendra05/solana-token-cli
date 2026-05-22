from setuptools import setup, find_packages

setup(
    name="solana-token-cli",
    version="0.1.0",
    description="Create and manage Solana SPL tokens from your terminal",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="bhupendra05",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.1",
        "rich>=13.0",
        "requests>=2.31",
        "python-dotenv>=1.0",
        "base58>=2.1",
        "cryptography>=42.0",
    ],
    entry_points={
        "console_scripts": [
            "sol-token=solana_token.cli:main",
        ]
    },
    keywords=["solana", "spl-token", "blockchain", "web3", "cli", "crypto"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries",
    ],
)
