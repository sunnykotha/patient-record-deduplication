# Patient Record Deduplication

A Python Master Patient Index (MPI) project for detecting duplicate patient records.

## Requirements
- Python 3.13 or newer
- Git for cloning

## Installation

Clone the repository:

    git clone REPOSITORY_URL
    cd patient-record-deduplication

Create and activate a virtual environment:

    py -3.13 -m venv .venv
    .\.venv\Scripts\Activate.ps1

Install dependencies:

    python -m pip install -e ".[dev]"

## Run tests

    python -m pytest -v

Or run without activating the environment:

    & ".\.venv\Scripts\python.exe" -m pytest -v

## Features
- Blocking by birth year and Soundex last name
- Demographic comparison and weighted match scoring
- Safety checks and manual-review decisions
- Golden-record survivorship
- Reversible merges and audit history
