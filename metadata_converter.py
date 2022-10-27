import csv
import re
from traceback import print_tb
from black import out
import requests
from bs4 import BeautifulSoup
from datetime import datetime


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

    def add_contributor_name(self, first_name, surname=""):
        name = []

        if surname and surname != ".":
            name.append(surname)
        if first_name and first_name != ".":
            name.append(first_name)

        if any(re.match("[Uu]nknown", x) for x in name):
            return "Unknown"

        return ", ".join(name)

    def convert_creators(self):
        if "creators" not in self.cedadocs_record:
            return {}
        creatorsListJSON = self.cedadocs_record["creators"]
        result = []
        for c in creatorsListJSON:
            creator = dict()
            creator["name"] = self.add_contributor_name(
                c["name"]["given"], c["name"]["family"]
            )
            result.append(creator)
        return {"creators": result}

    def convert_contributors(self):
        result = []

        if "contributors" in self.cedadocs_record:

            for c in self.cedadocs_record["contributors"]:
                contributor = dict()
                contributor["name"] = self.add_contributor_name(
                    c["name"]["given"], c["name"]["family"]
                )
                contributor["type"] = "Other"
                result.append(contributor)

        if "editors" in self.cedadocs_record:
            for c in self.cedadocs_record["editors"]:
                contributor = dict()
                contributor["name"] = self.add_contributor_name(
                    c["name"]["given"], c["name"]["family"]
                )
                contributor["type"] = "Editor"
                result.append(contributor)

        if "corp_creators" in self.cedadocs_record:
            for c in self.cedadocs_record["corp_creators"]:
                contributor = dict()
                contributor["name"] = c
                contributor["type"] = "Other"
                result.append(contributor)

        if "copyright_holders" in self.cedadocs_record:
            for c in self.cedadocs_record["copyright_holders"]:
                contributor = dict()
                contributor["name"] = c
                contributor["type"] = "RightsHolder"
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
        result.update(self.map_function("place_of_pub", "imprint_place"))
        result.update(self.map_function("number", "journal_issue"))
        result.update(self.map_function("volume", "journal_volume"))
        result.update(self.map_function("pagerange", "partof_pages"))
        result.update({"language": "eng"})

        if "publisher" in self.cedadocs_record:
            publisher = self.cedadocs_record["publisher"]
            acronyms_map = {
                "ARSF-DAN": "Airborne Remote Sensing Facility Data Analysis Node (ARSF-DAN)",
                "STFC": "Science and Technology Facilities Council (STFC)",
                "STFC RAL": "Science and Technology Facilities Council; Rutherford Appleton Laboratory (STFC RAL)",
                "BAS": "British Antarctic Survey (BAS)",
                "ESRIN": "European Space Research Institute (ESRIN)",
                "British Atmospheric Data Centre": "British Atmospheric Data Centre (BADC)",
                "National Aeronautics and Space Administration": "National Aeronautics and Space Administration (NASA)",
            }
            if publisher in ["N/A", "Unknown", "unknown"]:
                print("nope")
                pass
            elif publisher in acronyms_map:
                result["imprint_publisher"] = acronyms_map[publisher]
            else:
                result["imprint_publisher"] = publisher

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

        keywords = []

        if "subjects" in self.cedadocs_record:
            subjects_map = {
                "biology_and_microbiology": "biology and microbiology",
                "computer_science": "computer science",
                "data_and_information": "data and information",
                "ecology_and_environment": "ecology and environment",
                "hist_of_science": "history of science",
                "science_policy": "science policy",
            }
            for s in self.cedadocs_record["subjects"]:
                if s in subjects_map:
                    keywords.append(subjects_map[s])

        if "skill_areas" in self.cedadocs_record:
            return {"keywords": ["data management", "scientific computing"]}

        if "keywords" not in self.cedadocs_record:
            return {"keywords": keywords}

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
                764: ["FAAM Website", "Airborne Measurements"],
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

        ceda_keywords = self.cedadocs_record["keywords"]
        ceda_keywords = (
            ceda_keywords[:-1] if ceda_keywords[-1] == "." else ceda_keywords
        )
        ceda_keywords = re.split(r",|;|\r\n", ceda_keywords)
        ceda_keywords = [i.strip() for i in ceda_keywords if i]
        keywords += ceda_keywords

        return {"keywords": keywords}

    def get_depositing_user(self):
        rec_id = self.cedadocs_record["eprintid"]
        base_url = "http://cedadocs.ceda.ac.uk/"
        url = f"{base_url}{rec_id}"
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        dep_usr = soup.find_all("span", {"class": "ep_name_citation"})
        if dep_usr:
            return dep_usr[0].span.text
        return ""

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
            if field == "series":
                return f"{text} {self.cedadocs_record[field]} series.\n\n"
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
            "This item was previously associated with content (as an official url) at:",
            "official_url",
        )
        notes += self.add_note("Originally provided via", "output_media")
        notes += self.add_note("This item was part of the", "series")

        if "refereed" in self.cedadocs_record:
            notes += f'This item was {"not " if self.cedadocs_record["refereed"] else ""}refereed before the publication\n\n'

        if "projects" in self.cedadocs_record:
            notes += "Associated projects:\n"
            for p in self.cedadocs_record["projects"]:
                notes += f"{p}\n"
            notes += "\n"

        notes += "Main files in this record:\n"
        for doc in self.cedadocs_record["documents"]:
            notes += doc["main"] + "\n"
        notes += "\n"

        dep_usr = self.get_depositing_user()
        if dep_usr:
            now = datetime.now()
            now = now.strftime("%d/%m/%Y")
            notes += f"Item originally deposited with Centre for Environmental Data Analysis (CEDA) document repository by {dep_usr}. Transferred to CEDA document repository community on Zenodo on {now}"

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

    def convert_references(self):
        if "referencetext" not in self.cedadocs_record:
            return {}

        references = self.cedadocs_record["referencetext"]
        references = references.split("\r\n")
        return {"references": references}

    def convert_subjects(self):
        if "subjects" not in self.cedadocs_record:
            return {}

        base_url = "https://id.loc.gov/authorities/subjects/"
        subjects_map = {
            "archaeology": ["Archaeology", "sh85006507.html"],
            "atmospheric_sciences": ["Atmospheric Sciences", "sh2018002590.html"],
            "chemistry": ["Chemistry", "sh85022986.html"],
            "earth_sciences": ["Earth Sciences", "sh85040468.html"],
            "economics": ["Economics", "sh85040850.html"],
            "education": ["Education", "sh85040989.html"],
            "electronics": ["Electronics", "sh85042383.html"],
            "glaciology": ["Glaciology", "sh85055077.html"],
            "health": ["Health", "sh85059518.html"],
            "hydrology": ["Hydrology", "sh85063458.html"],
            "law": ["Law", "sh85075119.html"],
            "management": ["Management", "sh85080336.html"],
            "marine_sciences": ["Marine Sciences", "sh85081263.html"],
            "mathematics": ["Mathematics", "sh85082139.html"],
            "meteorology": ["Meteorology", "sh85084334.html"],
            "physics": ["Physics", "sh85101653.html"],
            "space_science": ["Space Science", "sh85125953.html"],
        }
        subjects = []
        for s in self.cedadocs_record["subjects"]:
            if s in subjects_map:
                subject = dict()
                subject["term"] = subjects_map[s][0]
                subject["identifier"] = base_url + subjects_map[s][1]
                subjects_map["scheme"] = "url"
                subjects.append(subject)

        return {"subjects": subjects}

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
        output.update(self.convert_references())
        output.update(self.convert_subjects())

        # print('metadata -------------------------------')
        # for k,v in output.items():
        #     print(f'{k}: {v}')

        return {"metadata": output}
