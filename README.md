Files in this repository:


all_ids.txt 
Contains all valid IDs of CEDA Docs records. It has been produced by using an external script.

cedadocs official url updates - Sheet1.csv
Contains list of IDs, URLs and alternative URLs (if needed) and is used for mapping field called `official_url` to one of `alternative_identifiers` on Zenodo.

doi_list.csv
Contains list of IDs and DOIs. Each record transferred to the Zenodo successfully has been added to this list.

errors.csv
Contains list of IDs, datetime of upload and status code of each of main 3 steps (creating empty Zenodo record, uploading metadata, uploading files)

main.py
Main Python file which is used to run the program.
Usage:

1. `python main.py id` where `id` is a valid ID of CEDA Docs record.
    It transfers record of given `id` to the Zenodo

2. `python main id1 id2` where `id1` and `id1` are valid IDs of CEDA Docs records.
    It tranfers all records with `id` which pass the condition `id1 <= id < id2`

3. `python main -2137`
    It removes every unpublished record from the Zenodo account (until it reaches status code `429`)


metadata_converter.py
It is responsible for converting metadata from `json` file representation of CEDA Docs record to Zenodo format.

transfer_to_zenodo.py
It is responsible for communication between program and Zenodo API. Can be used to upload, publish or remove Zenodo record.

Zenodo.ipynb
Beta version of the program written in the Notebook form.