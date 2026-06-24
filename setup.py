#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="chatxz",
    version="0.3.73",
    description="Decentralized chat over Reticulum Network Stack",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "rns>=1.3.0",
        "aiohttp>=3.9.0",
    ],
    entry_points={
        "console_scripts": [
            "chatxz=chatxz.cli:main",
        ],
    },
    package_data={
        "chatxz": ["web/static/*", "web/static/**/*"],
    },
    include_package_data=True,
)
