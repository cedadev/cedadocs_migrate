import csv
import re
from traceback import print_tb
from black import out
import requests


class Metadata_converter:
    def __init__(self, cedadocs_record):
        self.cedadocs_record = cedadocs_record

        self.doi_map = dict()

        with open("doi_list.csv") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            for line in reader:
                self.doi_map[int(line[0])] = line[1]

        self.url_map = dict()

        with open("cedadocs official url updates - Sheet1.csv") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            for line in reader:
                self.url_map[line[2]] = [line[1], line[3], line[4]]

    def convert_type(self):

        dictOfExceptions = {
            158: "publication/report",  ####
            1295: "other",
            53: "image/photo",
            55: "image/photo",
            56: "image/photo",
            150: "image/photo",
            65: "image/figure",
            91: "image/figure",
            1287: "image/diagram",
            1474: "image/diagram",
            194: "presentation",
            333: "poster",
        }

        if self.cedadocs_record["eprintid"] in dictOfExceptions:
            out_type = dictOfExceptions[self.cedadocs_record["eprintid"]]

        else:
            record_type = self.cedadocs_record["type"]
            if record_type == "monograph":
                record_type += f"/{self.cedadocs_record['monograph_type']}"

            elif record_type in ["conference_item", "exhibition"]:
                if "pres_type" in self.cedadocs_record:
                    record_type += f"/{self.cedadocs_record['pres_type']}"

            typeDict = {
                "article": "publication/article",
                "book": "publication/book",
                "book_section": "publication/section",
                "conference_item": "other",
                "conference_item/keynote": "presentation",
                "conference_item/speech": "presentation",
                "conference_item/lecture": "publication/conferencepaper",
                "conference_item/paper": "publication/conferencepaper",
                "conference_item/other": "publication/other",
                "conference_item/poster": "poster",
                "exhibition": "other",
                "exhibition/speech": "presentation",
                "image": "image",
                "other": "other",
                "teaching_resource": "lesson",
                "video": "video",
                "audio": "video",
                "dataset": "dataset",
                "monograph/working_paper": "publication/workingpaper",
                "monograph/other": "other",
                "monograph/structured_metadata": "other",
                "monograph/discussion_paper": "publication/workingpaper",
                "monograph/documentation": "other",
                "monograph/manual": "publication/technicalnote",
                "monograph/minutes": "publication/report",
                "monograph/annual_report": "publication/report",
                "monograph/project_report": "publication/report",
                "monograph/technical_report": "publication/technicalnote",
            }
            out_type = typeDict[record_type]

        out_type = out_type.split("/")

        result = dict()
        result["upload_type"] = out_type[0]
        if out_type[0] == "publication":
            result["publication_type"] = out_type[1]

        elif out_type[0] == "image":
            if len(out_type) > 1:
                result["image_type"] = out_type[1]
            else:
                result["image_type"] = "other"

        return result

    def convert_creators(self):
        if "creators" not in self.cedadocs_record:
            return {}
        creatorsListJSON = self.cedadocs_record["creators"]
        result = []
        for c in creatorsListJSON:
            creator = dict()
            creator["name"] = f"{c['name']['family']}, {c['name']['given']}"
            result.append(creator)
        return {"creators": result}

    def convert_contributors(self):
        result = []

        if "contributors" in self.cedadocs_record:

            for c in self.cedadocs_record["contributors"]:
                contributor = dict()
                contributor["name"] = f"{c['name']['family']}, {c['name']['given']}"
                contributor["type"] = "Other"
                result.append(contributor)

        if "editors" in self.cedadocs_record:

            for c in self.cedadocs_record["editors"]:
                contributor = dict()
                contributor["name"] = f"{c['name']['family']}, {c['name']['given']}"
                contributor["type"] = "Editor"
                result.append(contributor)

        if "institution" in self.cedadocs_record:
            contributor = dict()
            contributor["name"] = self.cedadocs_record["institution"]
            if "department" in self.cedadocs_record:
                contributor[
                    "name"
                ] = f'{self.cedadocs_record["department"]}, {contributor["name"]}'
            contributor["type"] = "HostingInstitution"
            result.append(contributor)

        if result:
            return {"contributors": result}
        return {}

    def convert_date(self):
        if "date" in self.cedadocs_record:
            if isinstance(self.cedadocs_record["date"], int):
                return {
                    "publication_date": str(self.cedadocs_record["date"]) + "-01-01"
                }
            elif len(self.cedadocs_record["date"]) == 7:
                return {"publication_date": self.cedadocs_record["date"] + "-01"}
            else:
                return {"publication_date": self.cedadocs_record["date"]}

        return {"publication_date": self.cedadocs_record["datestamp"][:10]}

    def map_function(self, eprintName, zenodoName, alt=""):
        if eprintName in self.cedadocs_record:
            return {zenodoName: str(self.cedadocs_record[eprintName])}
        elif alt:
            return {zenodoName: alt}
        return {}

    def convert_basic_metadata(self):
        result = dict()

        result.update(self.map_function("title", "title"))
        result.update(self.map_function("abstract", "description", result["title"]))
        result.update(self.map_function("isbn", "imprint_isbn"))
        result.update(self.map_function("event_dates", "conference_dates"))
        result.update(self.map_function("event_location", "conference_place"))
        result.update(self.map_function("event_title", "conference_title"))
        result.update(self.map_function("book_title", "partof_title"))
        result.update(self.map_function("number", "journal_issue"))
        result.update(self.map_function("volume", "journal_volume"))
        result.update(self.map_function("pagerange", "partof_pages"))
        result.update(self.map_function("publisher", "imprint_publisher"))
        result.update(self.map_function("publisher", "imprint_publisher"))

        if "pages" in self.cedadocs_record:
            result["partof_pages"] = str(self.cedadocs_record["pages"])

        if (
            self.cedadocs_record["type"] == "article"
            and "number" in self.cedadocs_record
        ):
            result["title"] += f' {self.cedadocs_record["number"]}'

        return result

    def convert_keywords(self):
        record_id = self.cedadocs_record["eprintid"]

        if "keywords" not in self.cedadocs_record:
            return {}

        if 822 < record_id < 866 or 912 < record_id < 916:
            return {"keywords": ["Environmental Physics Group", "Institute of Physics"]}

        elif record_id in [150, 274, 341, 764, 785, 810, 899, 1313, 1382]:
            keywordsDict = {
                150: ["radiosonde", "weather", "balloon", "clouds"],
                274: [
                    "data quality",
                    "European Space Agency",
                    "ESA",
                ],  # 'Data quality European Space Agency ESA'
                341: [
                    "Doppler",
                    "LiDAR",
                    "Atmospheric Physics Turbulence",
                ],  # 'Doppler lidar Atmospheric Physics Turbulence'
                764: ["FAAM Website",  "Airborne Measurements"],
                785: [
                    "LiDAR",
                    "Volcanic Ash",
                    "EZlidar",
                    "UKMO",
                    "Technical Note",
                    "OBR",
                ],  # 'LiDAR Volcanic Ash EZlidar UKMO Technical Note OBR'
                810: [
                    "data holdings",
                    "NERC",
                    "SIS",
                    "dataset",
                    "CEDA",
                    "NEODC",
                    "BADC",
                    "UKSSDC",
                    "services",
                ],  # data holdings NERC SIS dataset CEDA NEODC BADC UKSSDC services
                899: ["metadata", "tools", "climate modelling"],
                1313: ["MIPAS", "Cloud Retrieval Algorithm"],
                1382: ["CMIP", "ESGF", "CF"],
            }
            return {"keywords": keywordsDict[record_id]}

        keywords = self.cedadocs_record["keywords"]
        keywords = keywords[:-1] if keywords[-1] == "." else keywords
        keywords = re.split(r",|;|\r\n", keywords)
        keywords = [i.strip() for i in keywords if i]

        return {"keywords": keywords}

    def add_note(self, text, field):
        if field in self.cedadocs_record:
            if field == "id_number" and self.cedadocs_record["id_number"][:4] == "ISBN":
                return ""
            if (
                field == "output_media"
                and self.cedadocs_record["output_media"] == "Internet"
            ):
                return ""
            if field == "date_type":
                return f"{text} {self.cedadocs_record[field]} date\n\n"
            return f"{text} {self.cedadocs_record[field]}\n\n"
        return ""

    def additional_notes(self):
        notes = ""
        notes += self.add_note("Previously curated at:", "uri")
        notes += self.add_note("Contact for resource:", "contact_email")
        notes += self.add_note("Event type:", "event_type")
        notes += self.add_note("Related identifier for this resource:", "id_number")
        notes += self.add_note("This work was part of a", "pedagogic_type")
        notes += self.add_note(
            "The publish date on this item was its original", "date_type"
        )
        notes += self.add_note(
            "This item was previously associated with content (as an official url) at:", "official_url"
        )
        notes += self.add_note("Originally provided via", "output_media")

        notes = notes[:-2]

        return {"notes": notes}

    def convert_identifiers(self):
        result = []

        if (
            "id_number" in self.cedadocs_record
            and self.cedadocs_record["id_number"][:4] == "ISBN"
        ):
            identifier = dict()
            identifier["identifier"] = self.cedadocs_record["id_number"][5:]
            identifier["relation"] = "isAlternateIdentifier"
            result.append(identifier)

        if "issn" in self.cedadocs_record:
            identifier = dict()
            identifier["identifier"] = self.cedadocs_record["issn"]
            identifier["relation"] = "isAlternateIdentifier"
            result.append(identifier)

        if "official_url" in self.cedadocs_record:
            identifier = dict()
            identifier["identifier"] = self.convert_url()
            identifier["relation"] = "isSupplementedBy"
            result.append(identifier)

        if (
            "succeeds" in self.cedadocs_record
            and self.cedadocs_record["succeeds"] in self.doi_map
        ):
            identifier = dict()
            identifier["identifier"] = self.doi_map[self.cedadocs_record["succeeds"]]
            identifier["relation"] = "isNewVersionOf"
            result.append(identifier)

        if result:
            return {"related_identifiers": result}
        return {}

    def get_base_url(url):
        indices_object = re.finditer(pattern="/", string=url)
        splitPoint = [i.start() for i in indices_object][2]
        return url[:splitPoint]

    def convert_url(self):

        url = self.cedadocs_record["official_url"]
        i = self.cedadocs_record["eprintid"]
        status, redirectedUrl, suggestedUrl = self.url_map[url]

        if status == "Correct":
            return url

        elif suggestedUrl:
            return suggestedUrl

        elif redirectedUrl:
            return redirectedUrl

        elif (
            requests.get(self.get_base_url(url), verify=False, timeout=5).status_code
            == 200
        ):
            return self.get_base_url(url)

        else:
            print(f'Problem with record {self.cedadocs_record["eprintid"]}')
            return ""

    def convert_publication(self):
        if "publication" in self.cedadocs_record:
            if self.cedadocs_record["type"] == "article":
                return {"journal_title": self.cedadocs_record["publication"]}

            elif self.cedadocs_record["type"] == "book":
                return {"journal_title": self.cedadocs_record["publication"] + " book"}

            elif self.cedadocs_record["monograph_type"] == "documentation":
                return {
                    "journal_title": self.cedadocs_record["publication"]
                    + " documentation"
                }

            elif self.cedadocs_record["monograph_type"] == "technical_report":
                return {
                    "journal_title": self.cedadocs_record["publication"]
                    + " technical report"
                }

            else:
                return {"journal_title": self.cedadocs_record["publication"]}
        return {}

    def get_metadata(self):
        output = dict()
        output.update(self.convert_type())
        output.update(self.convert_creators())
        output.update(self.convert_contributors())
        output.update(self.convert_date())
        output.update(self.convert_basic_metadata())
        output.update(self.convert_keywords())
        output.update(self.additional_notes())
        output.update(self.convert_identifiers())
        output.update(self.convert_publication())

        # print('metadata -------------------------------')
        # for k,v in output.items():
        #     print(f'{k}: {v}')

        return {"metadata": output}
