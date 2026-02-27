# pooch-re3data-action

A GitHub Action that queries the [re3data](https://re3data.org) API for data repositories of a certain software type (e.g. `Dataverse`) and writes the repository URLs to a file. This is helpful for data repository implementations for [pooch-doi](https://github.com/ssciwr/pooch-doi) to keep an up-to-date list of known instances for a certain data repository type. Knowing about known instances allows us to dispatch to the correct implementation based on URL matching, as opposed to sending requests. The action automatically commits the list to the repository.

## Inputs

`pooch-re3data-action` accepts the following parameters:
- `software` (required): Value to match in re3data's data. To find out the correct value, navigate to a record on [re3data](https://re3data.org) and check whats written under Standards/Name of the repository software.
- `filename` (required): Output file path for the URL list
- `blacklist` (optional): Blacklist patterns (newline- or comma-separated). Any URL containing one of these substrings is excluded.

## Behavior

The action:

1. runs [`scrape.py`](./scrape.py),
2. writes filtered URLs to `filename`,
3. stages and commits the output file,
4. pushes to the current branch when `GITHUB_REF` is a branch ref (`refs/heads/*`).

## Usage

```yaml
name: Update Dataverse Repositories

on:
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./
        with:
          software: Dataverse
          filename: data/dataverse-urls.txt
          blacklist: |
            internal.example.org
```
