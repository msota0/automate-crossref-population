import os
import re
import pandas as pd
import logging
from datetime import datetime
from utils import setup_logging  # Absolute import

class XMLGenerator:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.journal_file = ''
        self.article_file = ''
        self.journal_data = None
        self.article_data = None
        self.journal_xml = ''
        self.article_xml = ''
        self.base_filename = ''

        try:
            # Discover files first so we have base_filename for logging
            self.journal_file = self.find_journal_file()
            self.base_filename = self.extract_base_filename()

            # Set up logging now that we have a sensible name
            self.logger = setup_logging(self.base_filename)
            self.logger.info(f"Initialized XMLGenerator with folder path: {folder_path}")

            self.initialize_article_file()
        except Exception as e:
            # Fallback logger in case setup_logging depends on base_filename
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"Error during initialization: {e}")
            raise

    # ----------------- helpers -----------------
    def _safe(self, v):
        if pd.isna(v):
            return ''
        return str(v).strip()

    def _fmt_issn(self, value):
        """Return ISSN in ####-#### if possible; else '' to avoid schema failure."""
        s = self._safe(value).replace('-', '')
        if re.fullmatch(r'\d{8}', s):
            return f"{s[:4]}-{s[4:]}"
        if re.fullmatch(r'\d{4}-\d{3}[\dX]', self._safe(value)):
            return self._safe(value)
        return ''

    def _ymd(self, value):
        """Return (Y, M, D) strings; empty strings if not parseable."""
        dt = pd.to_datetime(value, errors='coerce')
        if pd.isna(dt):
            return ('', '', '')
        return (dt.strftime('%Y'), dt.strftime('%m'), dt.strftime('%d'))

    def _url_or_empty(self, v):
        v = self._safe(v)
        return v if v and re.match(r'^(https?|ftp)://', v) else ''

    # ----------------- file discovery -----------------
    def find_journal_file(self):
        for filename in os.listdir(self.folder_path):
            if filename.endswith('_journal.xlsx'):
                return os.path.join(self.folder_path, filename)
        raise FileNotFoundError("No journal file found in the specified folder.")

    def extract_base_filename(self):
        base_name = os.path.basename(self.journal_file)
        return base_name.split('_')[0]

    def initialize_article_file(self):
        self.article_file = os.path.join(self.folder_path, f"{self.base_filename}_articles.xlsx")

    # ----------------- IO -----------------
    def read_excel_data(self):
        self.logger.info("Reading journal data...")
        try:
            if not os.path.exists(self.journal_file):
                raise FileNotFoundError(f"{self.journal_file} not found.")
            self.journal_data = pd.read_excel(self.journal_file)
            self.logger.info("Journal data read successfully.")

            self.initialize_article_file()
            self.logger.info("Reading article data...")
            if not os.path.exists(self.article_file):
                raise FileNotFoundError(f"{self.article_file} not found.")
            self.article_data = pd.read_excel(self.article_file)
            self.logger.info("Article data read successfully.")
        except Exception as e:
            self.logger.error(f"Error reading Excel files: {e}")
            raise

    # ----------------- XML builders -----------------
    def create_journal_xml(self):
        """Build <journal_metadata> + <journal_issue>"""
        self.logger.info("Creating journal XML...")
        try:
            journal = self.journal_data.iloc[0]

            # Dates
            y_p, m_p, d_p = self._ymd(journal.get('Pub_Date_Print'))
            y_o, m_o, d_o = self._ymd(journal.get('Pub_Date_Online'))

            # ISSNs
            p_issn = self._fmt_issn(journal.get('Print_ISSN'))
            e_issn = self._fmt_issn(journal.get('Electronic_ISSN'))

            # Strings
            jtitle = self._safe(journal.get('Journal Title'))
            jabbrev = self._safe(journal.get('Abbrev'))
            jdoi = self._safe(journal.get('Journal_DOI'))
            jurl = self._url_or_empty(journal.get('Journal_URL'))
            volume = self._safe(journal.get('Volume'))
            issue = self._safe(journal.get('Issue'))
            issue_doi = self._safe(journal.get('Issue_DOI'))
            issue_url = self._url_or_empty(journal.get('Issue_URL'))

            parts = []
            parts.append("<journal_metadata>")
            parts.append(f"    <full_title>{jtitle}</full_title>")
            if jabbrev:
                parts.append(f"    <abbrev_title>{jabbrev}</abbrev_title>")
            if p_issn:
                parts.append(f"    <issn media_type='print'>{p_issn}</issn>")
            if e_issn:
                parts.append(f"    <issn media_type='electronic'>{e_issn}</issn>")
            if jdoi or jurl:
                parts.append("    <doi_data>")
                if jdoi:
                    parts.append(f"        <doi>{jdoi}</doi>")
                if jurl:
                    parts.append(f"        <resource>{jurl}</resource>")
                parts.append("    </doi_data>")
            parts.append("</journal_metadata>")

            parts.append("<journal_issue>")
            if y_p and m_p and d_p:
                parts.append("    <publication_date media_type='print'>")
                parts.append(f"        <month>{m_p}</month>")
                parts.append(f"        <day>{d_p}</day>")
                parts.append(f"        <year>{y_p}</year>")
                parts.append("    </publication_date>")
            if y_o and m_o and d_o:
                parts.append("    <publication_date media_type='online'>")
                parts.append(f"        <month>{m_o}</month>")
                parts.append(f"        <day>{d_o}</day>")
                parts.append(f"        <year>{y_o}</year>")
                parts.append("    </publication_date>")
            if volume:
                parts.append("    <journal_volume>")
                parts.append(f"        <volume>{volume}</volume>")
                parts.append("    </journal_volume>")
            if issue:
                parts.append(f"    <issue>{issue}</issue>")
            if issue_doi or issue_url:
                parts.append("    <doi_data>")
                if issue_doi:
                    parts.append(f"        <doi>{issue_doi}</doi>")
                if issue_url:
                    parts.append(f"        <resource>{issue_url}</resource>")
                parts.append("    </doi_data>")
            parts.append("</journal_issue>")

            self.journal_xml = "\n".join(parts)
            self.logger.info("Journal XML created successfully.")
            return self.journal_xml
        except Exception as e:
            self.logger.error(f"Error creating journal XML: {e}")
            raise

    def create_article_xml(self):
        """Build multiple <journal_article> blocks in required order"""
        self.logger.info("Creating article XML...")
        article_xml_list = []

        try:
            for _, article in self.article_data.iterrows():
                title = self._safe(article.get('title'))
                doi = self._safe(article.get('doi'))
                resource = self._url_or_empty(article.get('fulltext_url'))

                # Enforce resource so <doi_data> is valid
                if not resource:
                    self.logger.error(f"Missing/invalid resource URL for DOI '{doi}' and title '{title}'. Resource is required by Crossref.")
                    raise ValueError(f"Missing resource URL for article: {title or '(untitled)'}")

                y, m, d = self._ymd(article.get('publication_date'))

                parts = []
                parts.append('    <journal_article publication_type="full_text">')

                # TITLES FIRST (per schema)
                parts.append("        <titles>")
                parts.append(f"            <title>{title}</title>")
                parts.append("        </titles>")

                # CONTRIBUTORS NEXT
                parts.append("        <contributors>")
                first_written = False
                for i in range(1, 6):
                    fname = self._safe(article.get(f'author{i}_fname'))
                    mname = self._safe(article.get(f'author{i}_mname'))
                    lname = self._safe(article.get(f'author{i}_lname'))
                    inst = self._safe(article.get(f'author{i}_inst'))

                    if fname:
                        sequence = 'first' if not first_written else 'additional'
                        first_written = True
                        given = " ".join([v for v in [fname, mname] if v]).strip()
                        parts.append(f"            <person_name contributor_role='author' sequence='{sequence}'>")
                        parts.append(f"                <given_name>{given}</given_name>")
                        if lname:
                            parts.append(f"                <surname>{lname}</surname>")
                        if inst:
                            parts.append(f"                <affiliation>{inst}</affiliation>")
                        parts.append("            </person_name>")
                parts.append("        </contributors>")

                # optional per-article date
                if y and m and d:
                    parts.append("        <publication_date media_type='online'>")
                    parts.append(f"            <month>{m}</month>")
                    parts.append(f"            <day>{d}</day>")
                    parts.append(f"            <year>{y}</year>")
                    parts.append("        </publication_date>")

                # DOI DATA (must include resource)
                parts.append("        <doi_data>")
                if doi:
                    parts.append(f"            <doi>{doi}</doi>")
                parts.append(f"            <resource>{resource}</resource>")
                parts.append("        </doi_data>")

                parts.append("    </journal_article>")

                article_xml_list.append("\n".join(parts))

            self.article_xml = "\n".join(article_xml_list)
            self.logger.info("Article XML created successfully.")
            return self.article_xml

        except Exception as e:
            self.logger.error(f"Error creating article XML: {e}")
            raise

    def combine_xml(self):
        """Wrap everything into <doi_batch> with <journal> body"""
        self.logger.info("Combining journal and article XML into a single XML document...")
        try:
            batch_id = self._safe(self.journal_data.iloc[0].get('Journal_DOI')) or self.base_filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

            combined_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<doi_batch xmlns="http://www.crossref.org/schema/4.4.2"
           version="4.4.2"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:schemaLocation="http://www.crossref.org/schema/4.4.2 http://www.crossref.org/schemas/crossref4.4.2.xsd">
    <head>
        <doi_batch_id>{batch_id}</doi_batch_id>
        <timestamp>{timestamp}</timestamp>
        <depositor>
            <depositor_name>MSSL</depositor_name>
            <email_address>memanuel@olemiss.edu</email_address>
        </depositor>
        <registrant>University of Mississippi</registrant>
    </head>
    <body>
        <journal>
{self.journal_xml}
{self.article_xml}
        </journal>
    </body>
</doi_batch>
"""
            self.logger.info("XML combined successfully.")
            return combined_xml
        except Exception as e:
            self.logger.error(f"Error combining XML: {e}")
            raise

    def write_to_xml_file(self, xml_string, filename):
        self.logger.info(f"Writing combined XML to {filename}...")
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(xml_string)
            self.logger.info(f"XML written to {filename} successfully.")
        except Exception as e:
            self.logger.error(f"Error writing to XML file {filename}: {e}")
            raise

    def generate_xml(self):
        self.logger.info("Starting XML generation process...")
        try:
            self.read_excel_data()
            self.create_journal_xml()
            self.create_article_xml()
            combined_xml = self.combine_xml()
            output_file = f'../output/{self.base_filename}.xml'
            self.write_to_xml_file(combined_xml, output_file)
            self.logger.info(f"XML generation complete. Output file: {output_file}")
        except Exception as e:
            self.logger.error(f"Error during XML generation: {e}")
            raise

# Usage Example
if __name__ == "__main__":
    folder_path = '../data'
    try:
        xml_generator = XMLGenerator(folder_path)
        xml_generator.generate_xml()
    except Exception as e:
        print(f"An error occurred: {e}")
