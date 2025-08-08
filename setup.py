#!/usr/bin/env python3
"""
Setup script for Stellar Wallet with Dinamo HSM Integration
"""

from setuptools import setup, find_packages
import os

# Read the README file for the long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements from requirements.txt
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="stellar-wallet-dinamo-hsm",
    version="1.0.0",
    author="Stellar HSM Wallet Team",
    author_email="contact@stellarwallet.com",
    description="A secure Stellar blockchain wallet implementation using Dinamo HSM",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/stellar-wallet-dinamo-hsm",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
    ],
    python_requires=">=3.9",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "coverage>=7.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinxcontrib-apidoc>=0.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "stellar-hsm-wallet=examples.basic_usage:main",
            "stellar-hsm-advanced=examples.advanced_features:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.txt", "*.md"],
    },
    data_files=[
        ("config", ["config.yaml", ".env.example"]),
        ("docs", ["README.md"]),
    ],
    keywords=[
        "stellar",
        "blockchain",
        "cryptocurrency",
        "hsm",
        "hardware security module",
        "dinamo",
        "pkcs11",
        "wallet",
        "cryptography",
        "fintech",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/stellar-wallet-dinamo-hsm/issues",
        "Source": "https://github.com/yourusername/stellar-wallet-dinamo-hsm",
        "Documentation": "https://stellar-wallet-dinamo-hsm.readthedocs.io/",
        "Stellar Foundation": "https://stellar.org",
        "Dinamo Networks": "https://dinamonetworks.com",
    },
    license="MIT",
    platforms=["Linux"],
    zip_safe=False,
)