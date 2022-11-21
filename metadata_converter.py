import csv
from os import stat
import re
from traceback import print_tb
from black import out
import requests
from bs4 import BeautifulSoup
from datetime import datetime


class Metadata_converter:
    '''This class is responsible for converting metadata from Cedadocs to Zenodo


    '''
    def __init__(self, cedadocs_record):
        ''' Init method of the class
        
        Args:
            cedadocs_record (dict): JSON representation of ceda docs record
        '''

        self.cedadocs_record = cedadocs_record

        # load DOI identifiers of already uploaded records
        self.doi_map = dict()
        with open("doi_list.csv") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            for line in reader:
                self.doi_map[int(line[0])] = line[1]

        # load file with correct urls to process mapping
        self.url_map = dict()
        with open("cedadocs official url updates - Sheet1.csv") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            for line in reader:
                self.url_map[line[2]] = [line[1], line[3], line[4]]

    def convert_type(self):
        '''This method converts type of the record

        It takes 'type' attribute and any relevant sub-type such as 'monograph_type' to determine Zenodo's 'upload_type' and any necessary sub-type attributes
        
        '''

        # those records needed to be mapped by hand
        dictOfExceptions = {
            158: "publication/report",
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

            # for 'monograph', 'conference_item' or 'exhibition' additional attribute is needed to determine a type
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
            # type is saved in format 'type/subtype' before futher processing
            out_type = typeDict[record_type]


        out_type = out_type.split("/")

        result = dict()
        result["upload_type"] = out_type[0]

        # depending on the type, proper sub type is set
        if out_type[0] == "publication":
            result["publication_type"] = out_type[1]

        elif out_type[0] == "image":
            if len(out_type) > 1:
                result["image_type"] = out_type[1]
            else:
                result["image_type"] = "other"

        return result

    @staticmethod
    def add_contributor_name(first_name, surname=""):
        '''This method format name bad/or surname of person/institution
        
        It is created to avoid following commas in case of institution and to standardize way of representing missing data

        Args:
            first_name (str): First name of the contributor
            surname (str): Surname of the contributor (optional)
        '''    

        name = []

        if surname and surname != ".":
            name.append(surname)
        if first_name and first_name != ".":
            name.append(first_name)

        # if 'unknown' appers in any part of the name, 'Unknown' is returned
        if any(re.match("[Uu]nknown", x) for x in name):
            return "Unknown"

        name = ', '.join(name)

        return name

    def convert_creators(self):
        '''This method converts creators list
        
        
        '''
        if "creators" not in self.cedadocs_record:
            return {}

        creatorsListJSON = self.cedadocs_record["creators"]
        result = []
        for c in creatorsListJSON:
            creator = dict()
            c_first_name = c["name"]["given"]
            c_surname = c["name"]["family"]
            creator["name"] = self.add_contributor_name(c_first_name, c_surname)
            result.append(creator)

        return {"creators": result}

    def convert_contributors(self):
        '''This method converts creators list
        
        It looks into various attributes in cedadocs related to contributors to extract them to a single list and pass to Zenodo
        '''


        result = []

        if "contributors" in self.cedadocs_record:
            for c in self.cedadocs_record["contributors"]:
                contributor = dict()
                c_first_name = c["name"]["given"]
                c_surname = c["name"]["family"]
                contributor["name"] = self.add_contributor_name(c_first_name, c_surname)
                contributor["type"] = "Other"
                result.append(contributor)

        if "editors" in self.cedadocs_record:
            for c in self.cedadocs_record["editors"]:
                contributor = dict()
                c_first_name = c["name"]["given"]
                c_surname = c["name"]["family"]
                contributor["name"] = self.add_contributor_name(c_first_name, c_surname)
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
            i_name = self.cedadocs_record["institution"]

            if "department" in self.cedadocs_record:
                d_name = self.cedadocs_record["department"]
                contributor["name"] = f'{d_name}, {i_name}'
            else:
                contributor["name"] = i_name

            contributor["type"] = "HostingInstitution"
            result.append(contributor)

        if result:
            return {"contributors": result}
        return {}

    def convert_date(self):
        '''This method converts date

        If any part of date is missing it is filled with 1st day, or 1st month
        If even the year is missing, datestamp is returned instead
        '''

        if 'date' not in self.cedadocs_record:
            datestamp = self.cedadocs_record["datestamp"]
            return {"publication_date": datestamp[:10]}

        date = self.cedadocs_record["date"]

        if isinstance(date, int):
            date = str(date) + "-01-01"
        elif len(date) == 7:
            date += "-01"
        
        return {"publication_date": date}

    def convert_publisher(self):
        '''This method converts publisher

        It filters out missing publishers
        For some records acronyms are mapped to the full name of the institution

        '''
        if "publisher" not in self.cedadocs_record:
            return {}

        publisher = self.cedadocs_record["publisher"]
        if publisher in ["N/A", "Unknown", "unknown"]:
            return {}

        acronyms_map = {
            "ARSF-DAN": "Airborne Remote Sensing Facility Data Analysis Node (ARSF-DAN)",
            "STFC": "Science and Technology Facilities Council (STFC)",
            "STFC RAL": "Science and Technology Facilities Council; Rutherford Appleton Laboratory (STFC RAL)",
            "BAS": "British Antarctic Survey (BAS)",
            "ESRIN": "European Space Research Institute (ESRIN)",
            "British Atmospheric Data Centre": "British Atmospheric Data Centre (BADC)",
            "National Aeronautics and Space Administration": "National Aeronautics and Space Administration (NASA)",
        }
        if publisher in acronyms_map:
            return {'imprint_publisher': acronyms_map[publisher]}

        return {'imprint_publisher': publisher}

    def map_function(self, cedadocs_field, zenodo_field, alt=""):
        '''This method maps simple metadata attributes

        'Simple' means that an attribute can be mapped directly from one field to another, without any extra processing

        Args:
            cedadocs_field (str): Name of the field to get value from
            zenodo_field (str): Name of the field to map the value to
            alt (str): Alternative value if cedadocs field is not present in JSON file
        '''
        if cedadocs_field in self.cedadocs_record:
            return {zenodo_field: str(self.cedadocs_record[cedadocs_field])}
        elif alt:
            return {zenodo_field: alt}
        return {}

  
    def convert_simple_metadata(self):
        '''This method converts simple metadata attributes

        'Simple' means that an attribute can be mapped directly or with little effort
        
        '''
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

       
        result['title'] = result['title'].replace('\r\n', ' ')

        if "pages" in self.cedadocs_record:
            result["partof_pages"] = str(self.cedadocs_record["pages"])

        # if article has a number it should be displayed in the title
        if (
            self.cedadocs_record["type"] == "article"
            and "number" in self.cedadocs_record
        ):
            result["title"] += f' {self.cedadocs_record["number"]}'

        return result

    def convert_keywords(self):
        '''This method converts keywords


        '''
        record_id = self.cedadocs_record["eprintid"]
        keywords = []

        # some subjects have no corresponding url, so they are put into keywords
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

        # there's one record with 'skill_areas' instead of keywords
        if "skill_areas" in self.cedadocs_record:
            return {"keywords": ["data management", "scientific computing"]}

        if "keywords" not in self.cedadocs_record:
            return {"keywords": keywords}

        if 822 < record_id < 866 or 912 < record_id < 916:
            return {"keywords": keywords + ["Environmental Physics Group", "Institute of Physics"]}

    
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
            return {"keywords": keywords + keywordsDict[record_id]}

        ceda_keywords = self.cedadocs_record["keywords"]
        # remove full stop if there is any
        ceda_keywords = (
            ceda_keywords[:-1] if ceda_keywords[-1] == "." else ceda_keywords
        )
        # split by various separators
        ceda_keywords = re.split(r",|;|\r\n", ceda_keywords)
        ceda_keywords = [i.strip() for i in ceda_keywords if i]
        keywords += ceda_keywords

        return {"keywords": keywords}

    def get_depositing_user(self):
        '''This method get deposition user associated with record of given ID

        Deposition user is not a part of JSON representation of record, so it has to be scraped from the cedadocs separately
        '''

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
        '''This method is used as a subroutine for additional_notes method

        Depending on the field proper f-string is returned

        Args:
            text (str): Text of the note 
            field (str): Field whose value meant to be inserted into text
        '''
        if field not in self.cedadocs_record:
            return ""
       
        if field == "id_number" and self.cedadocs_record[field][:4] == "ISBN":
            return ""

        if field == "output_media" and self.cedadocs_record[field] == "Internet":
            return ""

        if field == "date_type":
            return f"{text} {self.cedadocs_record[field]} date.\n\n"

        if field == "series":
            return f"{text} {self.cedadocs_record[field]} series.\n\n"

        return f"{text} {self.cedadocs_record[field]}.\n\n"
        
    def additional_notes(self):
        '''This method produces string, to be put into 'additional notes' section 


        '''
        # most of the fields are mapped using add_note method
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

        # others are more complex
        if 'funders' in self.cedadocs_record:
            notes += 'This work was funded by: '
            if len(self.cedadocs_record['funders']) == 1:
                notes += f"{self.cedadocs_record['funders'][0]}."
            else:
                funder_list = self.cedadocs_record['funders'][-1::-1]
                while funder_list:
                    funder = funder_list.pop()
                    if not funder_list:
                        notes += f'{funder}.'
                    elif len(funder_list) == 1:
                        notes += f'{funder} and, '
                    else:
                        notes += f'{funder}; '

            notes = notes + '\n\n'

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
        '''This method converts identifiers

        
        '''
        result = []

        if "id_number" in self.cedadocs_record and self.cedadocs_record["id_number"][:4] == "ISBN":
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

    @staticmethod
    def get_base_url(url):
        '''This method returns basic url of given url

        It is used if broken URL cannot be mapped using provided CSV file
        '''
        indices_object = re.finditer(pattern="/", string=url)
        splitPoint = [i.start() for i in indices_object][2]
        return url[:splitPoint]

    def convert_url(self):
        '''This method converts url addresses

        Some urls are out of date or broken, so they need to be replaced with alternative url.
        It is done using mapping scheme from CSV file
        '''      

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
            print(f'Problem with record {i}')
            return ""

    def convert_publication(self):
        '''This method converts publication

        Title of the publication may depend on some of the sub-types, so this methods solves this issue

        '''

        if "publication" not in self.cedadocs_record:
            return {}

       
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
        
    def convert_references(self):
        '''This method converts references list

        References in cedadocs are stored as single string
        Zenodo requires list of string, so this method split references properly
        '''
        if "referencetext" not in self.cedadocs_record:
            return {}

        references = self.cedadocs_record["referencetext"]
        references = references.split("\r\n")
        return {"references": references}

    def convert_subjects(self):
        '''This method converts subjects according to mapping provided in CSV file


        '''
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
        '''This method produces Zenodo metadata by combining all other methods


        '''
        output = dict()
        output.update(self.convert_type())
        output.update(self.convert_creators())
        output.update(self.convert_contributors())
        output.update(self.convert_date())
        output.update(self.convert_simple_metadata())
        output.update(self.convert_keywords())
        output.update(self.additional_notes())
        output.update(self.convert_identifiers())
        output.update(self.convert_publication())
        output.update(self.convert_references())
        output.update(self.convert_subjects())
        output.update(self.convert_publisher())

        return {"metadata": output}
