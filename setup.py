"""cos-vectors-embed-cli: CLI tool for vectorizing content and storing in Tencent COS Vector Buckets."""

import os
from setuptools import setup, find_packages

# Read version from cos_vectors/__version__.py
version = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "cos_vectors", "__version__.py")) as f:
    exec(f.read(), version)

# Read README for long description
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cos-vectors-embed-cli",
    version=version["__version__"],
    author="Tencent Cloud COS Team",
    description="Standalone CLI for COS Vector operations with pluggable embeddings",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.9",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "cos-python-sdk-v5>=1.9.40",
        "click>=8.0.0",
        "rich>=12.0.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cos-vectors-embed=cos_vectors.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
