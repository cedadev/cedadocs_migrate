from cmath import log
from logging import error
from time import sleep
import requests
import json
from metadata_converter import Metadata_converter
from datetime import datetime 


class Transfer_to_zenodo:
    def __init__(self, record_id):
        list_of_valid_ids = []
        with open("all_ids.txt") as f:
            list_of_valid_ids = list(f)
            list_of_valid_ids = [int(i) for i in list_of_valid_ids]

        if record_id not in list_of_valid_ids and record_id != -2137:
            error(f"Id {record_id} is invalid!")
            exit(1)

        self.record_id = record_id
        self.ACCESS_TOKEN = (
            "z9FKfVJg1gHzqeV7r74XCMqY2Af6kdHScMFyftdcCN39alQEjb8R9HH5ol9g"
        )
        self.params = {"access_token": self.ACCESS_TOKEN}

    def get_record(self):
        r = requests.get(
            f"http://cedadocs.ceda.ac.uk/cgi/export/eprint/{self.record_id}/JSON/ceda-eprint-{self.record_id}.js"
        )
        self.cedadocs_record = r.json()

    def upload_to_zenodo(self):
        
        now = datetime.now()
        log_variables = [str(self.record_id), now.strftime('"%d/%m/%Y %H:%M:%S"'), '','','','']

        metadata_converter = Metadata_converter(self.cedadocs_record)
        metadata = metadata_converter.get_metadata()

        print(f'Uploading record {self.cedadocs_record["eprintid"]}')

        # create deposition folder
        creation_response = requests.post(
            "https://sandbox.zenodo.org/api/deposit/depositions",
            params=self.params,
            json={},
        )
        print(
            f"Creation of new record finished with status code {creation_response.status_code}"
        )

        log_variables[2] = str(creation_response.status_code)

        if creation_response.status_code >= 300:
            self.save_logs(log_variables)
            return -1

        dep_id = creation_response.json()["id"]
        bucket_url = creation_response.json()["links"]["bucket"]

        # set metadata
        metadata_response = requests.put(
            f"https://sandbox.zenodo.org/api/deposit/depositions/{dep_id}",
            params=self.params,
            data=json.dumps(metadata),
            headers={"Content-Type": "application/json"},
        )

        print(
            f"Uploading metadata finished with status code {metadata_response.status_code}"
        )

        log_variables[3] = str(metadata_response.status_code)

        if metadata_response.status_code >= 300:
            requests.delete(
                f"https://sandbox.zenodo.org/api/deposit/depositions/{dep_id}",
                params=self.params,
            )
            print("Deposition will be removed from Zenodo")
            self.save_logs(log_variables)
            return -2

        # upload files
        counter = 0
        for doc in self.cedadocs_record["documents"]:
            for file in doc["files"]:
                if counter == 40:
                    sleep(3)
                    counter = 0
                filename = file["filename"]
                filepath = file["uri"]
                counter += 1
                file_response = requests.put(
                    f"{bucket_url}/{filename}",
                    data=requests.get(filepath).content,
                    params=self.params,
                )

                if file_response.status_code >= 300:
                    print(
                        f"Unexpected status code {file_response.status_code} on file {filename}"
                    )
                    requests.delete(
                        f"https://sandbox.zenodo.org/api/deposit/depositions/{dep_id}",
                        params=self.params,
                    )
                    print("Deposition will be removed from Zenodo")

                    log_variables[4] = str(file_response.status_code)
                    log_variables[5] = filename
                    self.save_logs(log_variables)
                    return -1

                print(f"File {filename} uploaded")

        print("\nEnd of record. Success!\n")
        self.deposition_id = dep_id
        self.save_logs(log_variables)
        return 0

    def post_record(self):
        r = requests.post(
            f"https://sandbox.zenodo.org/api/deposit/depositions/{self.deposition_id}/actions/publish",
            params=self.params,
        )
        print(f"Record posted with status code {r.status_code}")
        sleep(3)

        r = requests.get(
            f"https://sandbox.zenodo.org/api/deposit/depositions/{self.deposition_id}",
            params=self.params,
        )

        doi = r.json()["doi"]

        with open("doi_list.csv", "a") as f:
            f.write(f"{self.record_id},{doi}\n")

    def delete_records(self):
        r = requests.get(
            "https://sandbox.zenodo.org/api/deposit/depositions", params=self.params
        )

        while r.json()[:-4]:
            for d in r.json():
                print(d["id"])
                r1 = requests.delete(
                    f'https://sandbox.zenodo.org/api/deposit/depositions/{d["id"]}',
                    params=self.params,
                )
                print(r1)
            r = requests.get(
                "https://sandbox.zenodo.org/api/deposit/depositions", params=self.params
            )

    def save_logs(self, log_variables):
        with open('errors.csv', 'a') as f:
            f.write(','.join(log_variables) + '\n')