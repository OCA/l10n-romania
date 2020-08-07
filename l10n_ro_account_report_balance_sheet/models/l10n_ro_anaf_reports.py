# Copyright (C) 2020 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# to transform pdf to text
# not working from PyPDF2 import PdfFileWriter, PdfFileReader,PdfFileReader
import io
import json
import logging
from copy import deepcopy
from datetime import datetime
from io import BytesIO

import requests
from lxml import etree
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage

from odoo import api, fields, models
from odoo.doc._extensions.pyjsparser.parser import false, true
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


# works also with text=textract.process('file.pdf', method='pdfminer')
# /to read pdf


def convert_pdf_to_txt(file_like):  # path
    """Convert pdf content from a file path to text

    :path the file path
    """
    rsrcmgr = PDFResourceManager()
    codec = "utf-8"
    laparams = LAParams()

    with io.StringIO() as retstr:
        with TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams) as device:
            #            with open(path, 'rb') as fp:
            if True:
                fp = file_like
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                password = ""
                maxpages = 0
                caching = True
                pagenos = set()

                for page in PDFPage.get_pages(
                    fp,
                    pagenos,
                    maxpages=maxpages,
                    password=password,
                    caching=caching,
                    check_extractable=True,
                ):
                    interpreter.process_page(page)

                return retstr.getvalue()


class l10n_ro_anaf_reports(models.Model):
    _name = "l10n.ro.anaf.reports"
    _description = (
        "Model to keep the requested report format - structure, fields, formulas..."
    )
    _inherit = ["mail.thread"]

    name = fields.Char(required=1, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer("sequence at choose; smallest one first ")
    required = fields.Boolean("is a mandatory report")
    valid_form_date = fields.Date()
    valid_till_date = fields.Date()

    company_type = fields.Selection(
        selection=[
            ("BL", "S1002 BL Societati Mari Mijloci"),
            ("BS", "S1003 BS Societati Mici"),
            ("SL", "S1004 SL IFRS Societati mari mijloci"),
            ("UL", "S1005 UL Microintreprinedri"),
        ],
        default="BL",
        required=True,
        help="Type of romanian company by accounting low",
        tracking=True,
    )

    report_final_pdf_anaf_link = fields.Char(
        help="link to pdf that is the required anaf report",
        tracking=True,
        default="https://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/bilant_SC_1219_XML_240220.pdf",
    )
    report_final_pdf_local_link = fields.Char(
        default="202005_bilant_SC_1219_XML_240220",
        tracking=True,
        help="local link to pdf that is the required anaf report",
    )

    report_law_anaf_link = fields.Char(
        default="https://static.anaf.ro/static/10/Anaf/legislatie/OMFP_3781_2019.pdf",
        help="link to law of report",
        tracking=True,
    )
    report_law_local_link = fields.Char(
        default="static/202005_OMFP_3781_2019.pdf",
        help="local link to law of report",
        tracking=True,
    )
    report_law_text = fields.Text(
        help="Text version of pdf with page numbers.\n From this you must take the start_line and end_line for report.\n You can see the button to create this field if this field is empty",
        tracking=True,
    )

    report_start_line_nr = fields.Integer(
        help="The report in law is started at page",
        default=1,
        required=1,
        tracking=True,
    )
    report_end_line_nr = fields.Integer(
        help="The report in law is started at page",
        default=2,
        required=1,
        tracking=True,
    )
    report_text = fields.Text(
        help="Text trimmed text from report_law_text. You can see the button to create this field if this field in empty",
        tracking=True,
    )

    tags_xml_format = fields.Char(
        help="The tags for exported xml fields", required=1, tracking=True,
    )
    header = fields.Text()
    footer = fields.Text()
    table_to_parse = fields.Text()

    dictionary_no_rowspan_txt = fields.Text(help="formated dictionary")

    dictionary_with_rowspan_json = fields.Text(help="dictionary as JSON dump")
    dictionary_with_rowspan_txt = fields.Text(help="formated dictionary text")

    html_original_table = fields.Html(
        help="html table from dictionary_with_rowspan_json ( first key is row than column with attributes"
    )

    report_xsd_anaf_link = fields.Char(
        default="https://static.anaf.ro/static/10/Anaf/Declaratii_R/AplicatiiDec/s1002_20200203.xsd",
        help="link to xsd of report",
        tracking=True,
    )
    report_xsd_local_link = fields.Char(
        default="static/s1002_20200203_mari_mijloci.xsd",
        help="local link to xsd of report",
        tracking=True,
    )

    fill_data_py = fields.Text(
        help="must be a python code that receives date_from, date_to, company_id, **arguments and has the default model dictionary self.dictionary_with_rowspan_json. the result must be the dictionary with data in it"
    )
    transform_to_xml = fields.Text(
        help="from the populated dictionary named filled_dictionary the eval of this will  transform it to anaf xml. result must be a text containing xml in it",
        tracking=True,
    )

    resulted_test_html = fields.Html(help="html from model tranformed by fill_data_py")
    final_dictionary_json = fields.Text(help="dictionary as JSON dump")
    resulted_test_xml = fields.Text(
        help="xml from model tranformed by fill_data_py and transform_to_xml"
    )

    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            {"name": "copied_reportr",}
        )
        return super().copy(default)

    def button_anaf_link_pdf_to_text(self):
        return self.button_pdf_to_text(anaf_link=True)

    def button_pdf_to_text(self, anaf_link=False):
        """ Is parsing the pdf from line "report_form_line_nr" and is expecting to find a facsimil form
        as a result will modify the
        qweb_report_format
        fields_dictionary_report
        required_fields_dictionary_report
        """
        self.ensure_one()
        if anaf_link:
            source = self.report_law_anaf_link
        else:
            source = self.report_law_local_link
        if not source:
            raise ValidationError("No report_law_local_link or report_law_anaf_link")

        if anaf_link:
            r = requests.get(source,)  # stream=True,#allow_redirects=True
            file_like = BytesIO(r.content)
            text = convert_pdf_to_txt(file_like)
            del r
            del file_like
        else:
            pdf_path = get_module_resource(
                "l10n_ro_account_balance",
                "static/doc_romania_legislation/",
                self.report_law_local_link,
            )
            with open(pdf_path, "rb") as file_like:
                text = convert_pdf_to_txt(file_like)
        if not text:
            raise ValidationError(f"No text extracted with pdfminer from {pdf_path}.")
        text_with_line_before = ""
        line_nr = 0
        #        print(f"originaltext:{text}")
        text2 = text.replace("\xa0", " ")
        #        print(f"text2={text2}")
        text3 = text2.replace("\x0c", "")
        #        print(f"text3={text3}")
        for line in text3.split("\n"):
            #             if 780<line_nr>=746:
            #                 print(line)
            text_with_line_before += f"L{line_nr:04}:" + line + "\n"
            line_nr += 1
        #        print(f"text3=\n{text3}")
        #        print(f"text_with_line_before:\n{text_with_line_before}")

        self.report_law_text = text_with_line_before

    def extract_text_from_line_to_line(self):
        self.ensure_one()
        if not self.report_law_text:
            raise ValidationError("You must have a text to parse in report_law_text")
        lines = self.report_law_text.split("\n")
        len_lines = len(lines)
        line_nr = self.report_start_line_nr
        report_text = ""
        while line_nr < len_lines and line_nr < self.report_end_line_nr:
            line = lines[line_nr]
            if (
                len(line) >= 6 and line[0] == "L" and line[5] == ":"
            ):  # line can begin with Lnnnn: or without
                line = line[6:]
            report_text += line + "\n"
            #            print(line)
            line_nr += 1
        self.report_text = report_text

    def header_table_footer_from_report_text(self):
        """ Is parsing the report_text and gives header, table and footer
        """
        self.ensure_one()
        if not self.report_text:
            raise ValidationError("You must have a text to parse in report_law_text")

        header = footer = table = ""
        table_was_stated = False
        table_was_ended = False
        for line in self.report_text.split("\n"):
            if not table_was_stated:
                if (
                    "____________________________________________________________________________"
                    in line
                ):
                    table_was_stated = True
                else:
                    header += line + "\n"
            else:
                if not table_was_ended:
                    if line and line[0] == "|":
                        table += line + "\n"
                    else:
                        if line:
                            table_was_ended = True
                            footer += line + "\n"
                else:
                    footer += line + "\n"
        self.header = header
        self.footer = footer
        self.table_to_parse = table

    def dictionary_to_html(
        self, dict_for_html, line_column_dictionary_template={}, show_formulas=False
    ):
        " create the html table"
        timestamp = f"{fields.Date.today()}u{self._uid}"
        html_original_table = f"<table class='table table-striped table-bordered table-sm {timestamp}'><tbody>\n"
        formulas_header = ""
        if show_formulas:
            formulas_header = "    <td>Formulas<td>\n"
        if line_column_dictionary_template:
            html_original_table += (
                "    <tr><th/>\n"
                + formulas_header
                + "".join(
                    f"    <th>{k1}</th>\n" for k1 in line_column_dictionary_template
                )
                + "</tr>\n"
            )

        for k, v in dict_for_html.items():
            html_original_table += f"  <tr class='{k}'>\n"
            if line_column_dictionary_template:
                html_original_table += f"    <th>{k}</th>\n"
            if show_formulas:
                html_original_table += "<td>"
                for key in v.keys():
                    if "_formula" in key:
                        html_original_table += (
                            f'"{key}:"' + str(dict_for_html[k][key]) + "\n"
                        )
                html_original_table += "</td>"

            for k1, v1 in v.items():  # columns
                if k1[0] != "C":
                    continue
                #                print(f"line={k}\n column={k1}\n cell_value={v1}\n")
                original_line = (
                    ("orig" + v1["original_line"])
                    if v1.get("original_line", "")
                    else ""
                )
                colspan = (
                    (f'colspan="' + str(v1["colspan"]) + '"')
                    if int(v1.get("colspan", 1)) > 1
                    else ""
                )
                rowspan = (
                    (f'rowspan="' + str(v1["rowspan"]) + '"')
                    if int(v1.get("rowspan", 1)) > 1
                    else ""
                )
                value = v1.get("value", "")
                html_original_table += f"    <td class='{k} {k1} {original_line}' {colspan} {rowspan}>{value}</td>\n"
            html_original_table += "  </tr>\n"
        html_original_table += "</tbody></table>"
        return html_original_table

    def dictionary_from_text(self):
        """ Is extracting a dictionary:
        L0:{C1:C1_value,C2:C2_value..},L2:{C1:...    where L1 are the lines and  C0.. are the table columns
        """
        self.ensure_one()
        if not self.table_to_parse:
            raise ValidationError("To obtain the dictionary you need table_to_parse")
        d = {}
        table_split_in_lines = self.table_to_parse.split("\n")
        # find the max nr of columns
        ln = 0  # line number
        max_columns = 0  # based on nr of |
        line_column_dictionary_template = {}
        for line in table_split_in_lines:
            line_columns = line.count("|")
            if line_columns > max_columns:
                max_columns = line_columns
                cn = 0
                column_len = 0
                for character_index in range(1, len(line)):
                    if line[character_index] != "|":
                        column_len += 1
                    else:
                        line_column_dictionary_template[f"C{cn}"] = {
                            "len": column_len,
                            "colspan": 1,
                            "rowspan": 0,
                            "value": "",
                        }
                        cn += 1
                        column_len = 0
            ln += 1
        # find the max nr of columns

        ln = 0  # line number
        for line in table_split_in_lines:
            if not line or (line[0] != "|" and line[-1] != "|"):
                _logger.warning(
                    f"\nline is not null, or starts and ends with | \nline={line}"
                )
                continue
            d[f"L{ln}"] = deepcopy(line_column_dictionary_template)
            cn = 0  # column number
            value = ""
            for character_index in range(1, len(line)):
                if line[character_index] != "|":
                    value += line[character_index]
                else:
                    d[f"L{ln}"][f"C{cn}"]["value"] = value
                    if len(value) > line_column_dictionary_template[f"C{cn}"]["len"]:
                        original_cn = cn
                        colums_len = (
                            line_column_dictionary_template[f"C{cn}"]["len"] + 1
                        )
                        colspan = 1
                        while colums_len <= len(value):
                            cn += 1
                            colspan += 1
                            colums_len += (
                                line_column_dictionary_template[f"C{cn}"]["len"] + 1
                            )
                        d[f"L{ln}"][f"C{original_cn}"]["colspan"] = colspan
                    cn += 1
                    value = ""
            ln += 1

        #        print(d)
        def dictionary_as_table(line_column_dictionary_template, d):
            "just to show the dictionary as a arranged text/table"
            col_temp = deepcopy(line_column_dictionary_template)
            if not d:
                return
            txt = ""
            txt += f"{txt:>7}|"
            for k, v in col_temp.items():
                txt += f"{k:{v['len']}}|"
            txt += "\n"
            for k, v in d.items():
                txt += f"{k:>7}|"
                for k1, v1 in v.items():
                    if (
                        v1["value"] == ""
                    ):  # is nothing because was a colspan before otherwise was at least a space
                        continue
                    txt += f"{v1['value']}|"
                txt += "\n"
            return txt

        self.dictionary_no_rowspan_txt = dictionary_as_table(
            line_column_dictionary_template, d
        )
        #        print(self.dictionary_no_rowspan_txt)

        #   parse the dictionary to find the the rowspan
        # initial rowspan=0; here we compute the rowspan and if>=1 means that this cell is ok for html table
        d_rowsapn = deepcopy(d)
        for col_key in d_rowsapn["L0"]:  # the column
            row_lines = 0
            value = ""
            line_nr = 0
            for line_key, line in d_rowsapn.items():
                if not line[col_key]["value"]:
                    line_nr += 1
                    continue  # is a colspan

                if "_" in line[col_key]["value"]:  # is a vertical end of a cell

                    nr_of_sub_rows_on_other_columns = 0
                    if (
                        row_lines > 1
                    ):  # can be split in more than one row (otherwise is just a longer text on more rows and will be rowspan=1)
                        for col_key2 in d_rowsapn["L0"]:
                            if col_key2 == col_key:
                                continue
                            else:
                                row_separators_nr = 0
                                for line_nr2 in range(line_nr - row_lines, line_nr - 1):
                                    if (
                                        "_"
                                        in d_rowsapn[f"L{line_nr2}"][col_key2]["value"]
                                    ):
                                        row_separators_nr += 1
                                nr_of_sub_rows_on_other_columns = max(
                                    nr_of_sub_rows_on_other_columns, row_separators_nr
                                )

                    d_rowsapn[f"L{line_nr - row_lines}"][col_key]["rowspan"] = (
                        1 + nr_of_sub_rows_on_other_columns
                    )
                    d_rowsapn[f"L{line_nr - row_lines}"][col_key][
                        "value"
                    ] = value.strip()
                    row_lines = 0
                    value = ""
                else:
                    row_lines += 1
                    value += line[col_key]["value"]
                line_nr += 1

        #        print(d_rowsapn)

        # we are taiking out cells that have rowspan=0
        ln = 0
        dict_for_html = {}
        for k, v in d_rowsapn.items():
            line = {}
            for k1, v1 in v.items():  # columns
                if d_rowsapn[k][k1]["rowspan"]:
                    line[k1] = d_rowsapn[k][k1]
                    line[k1]["original_line"] = k
            if line:
                dict_for_html[f"L{ln}"] = line
                ln += 1
        #        print(dict_for_html)
        self.dictionary_with_rowspan_json = json.dumps(dict_for_html)

        self.html_original_table = self.dictionary_to_html(
            dict_for_html, line_column_dictionary_template
        )

    def function_fill_data(
        self, test=False, date_from=False, date_to=False, company_id=False, arguments={}
    ):
        """ Is putting the values in law model self.dictionary_with_rowspan_json that looks like
        L0:{C1:C1_value,C2:C2_value..},L2:{C1:...    where L1 are the lines and  C0.. are the table columns
        and in Cx_value we have colspan, rowspan, & value

        will return the modified dictionary
        """
        self.ensure_one()
        if not self.dictionary_with_rowspan_json:
            return f"{fields.Datetime.now()} Error, you do not have self.dictionary_with_rowspan_json. First you must have a dictionary with the model table and with data. To do this with parsing the law press the buttons from  pages from left to right"
        if not self.fill_data_py:
            print("no self.fill_data_py")
        #            return f'{fields.Datetime.now()} Error, you do not have self.fill_data_py. So the dictionary and table will be the same as in previous page'
        if not date_from or not date_to:
            date_from = fields.Date.today().replace(month=1, day=1)
            date_to = fields.Date.today().replace(month=12, day=31)
        if not company_id:
            company_id = self.env.user.company_id

        def find_formula_in_text(text_to_parse, start_of_formula):
            resulted_list = []
            paranteses_start_index = 0
            for x in start_of_formula:
                if x in text_to_parse:
                    paranteses_start_index = text_to_parse.find(x) + len(x)
                    break
            if paranteses_start_index:
                paranteses_start = text_to_parse[paranteses_start_index:]
                in_paranteses = paranteses_start[: paranteses_start.find(")")]
                resulted_list = parse_text_in_paranteses(in_paranteses)
            return resulted_list

        def parse_text_in_paranteses(in_paranteses):
            res = []
            nr, star, sign = "", "", "+"  # possible plus, minus, plus/minus
            index = 0
            while index < len(in_paranteses):
                character = in_paranteses[index]
                if character.isnumeric():
                    nr += character
                elif character in ["+", "/", "-"]:
                    if nr:
                        res += [{"nr": int(nr), "star": star, "sign": sign}]
                        nr, star, sign = "", "", "+"
                    if character == "+":
                        sign = "+"
                    elif character == "/":
                        sign = "+/-"
                    elif character == "-":
                        if sign != "+/-":
                            sign = "-"
                elif character == "*":
                    star += "*"
                # series from till row
                elif character == "l" and in_paranteses[index + 1] == "a":
                    end = False
                    index += 2
                    to_nr = ""
                    while not end:
                        # print(f"index={index} in_paranteses={in_paranteses}")
                        if index < len(in_paranteses) and (
                            in_paranteses[index].isnumeric()
                            or in_paranteses[index] == " "
                        ):
                            to_nr += in_paranteses[index]
                            index += 1
                        else:
                            for x in range(int(nr), int(to_nr) + 1):
                                res += [{"nr": int(x), "star": star, "sign": sign}]
                            nr, star, sign = "", "", "+"
                            end = True
                # series from till row
                else:
                    if character != " ":
                        _logger.warning(
                            f'in_paranteses="{in_paranteses}" we have the unknown character={character}'
                        )
                index += 1
            if nr:  # is the end of text but not saved
                res += [{"nr": int(nr), "star": star, "sign": sign}]
            return res

        d = json.loads(self.dictionary_with_rowspan_json)
        d["L1"]["C4"]["value"] = str(date_from)
        d["L1"]["C5"]["value"] = str(date_to)
        rd_resulted = {}
        for k, v in d.items():
            if (
                (v.get("C1", {}) and v["C1"]["value"])
                or (v.get("C2", {}) and v["C2"]["value"])
            ) and (v.get("C3", {}) and v.get("C3")["value"]):
                nr_rd = int(v.get("C3")["value"])
                if 1 <= nr_rd <= 104:
                    only = False
                    d[k]["nr_rd"] = nr_rd
                    # only for lines that have only credit or only debit
                    if v.get("C2", {}) and v["C2"]["value"]:
                        if v["C2"]["value"] == "SOLD C":
                            only = "credit"
                        elif v["C2"]["value"] == "SOLD D":
                            only = "debit"
                            date_from_value, date_to_value = 0, 0
                            for (
                                account
                            ) in (
                                resulted_list
                            ):  # will take the formula from above row because is rowspan; and resulted_list must exist from
                                date_from_value += self.get_account_at_date(
                                    date_from, account["nr"], account["sign"], only
                                )
                                date_to_value += self.get_account_at_date(
                                    date_to, account["nr"], account["sign"], only
                                )
                            date_from_value += self.get_account_at_date(
                                date_from, account["nr"], account["sign"], only
                            )
                            date_to_value += self.get_account_at_date(
                                date_to, account["nr"], account["sign"], only
                            )
                            d[k]["C4"]["value"] = date_from_value
                            d[k]["C5"]["value"] = date_from_value
                            d[k]["account_formula"] = resulted_list
                            continue
                    # / only for lines that have only credit or only debit
                    text_to_parse = v.get("C1")["value"]
                    resulted_list = find_formula_in_text(
                        text_to_parse, ["(ct.", "(din ct."]
                    )
                    if resulted_list:
                        d[k]["account_formula"] = resulted_list
                    resulted_list = find_formula_in_text(text_to_parse, ["(rd."])
                    if resulted_list:
                        d[k]["row_formula"] = resulted_list

                        #                    if not '(rd.' in text_to_parse or not '(ct.' in text_to_parse:
                        #                         _logger.error(f'line={k} value={v}\n no "(ct." or "(rd." in parateses so we do not know how to parse')

                        date_from_value, date_to_value = 0, 0
                        for account in resulted_list:
                            date_from_value += self.get_account_at_date(
                                date_from, account["nr"], account["sign"], only
                            )
                            date_to_value += self.get_account_at_date(
                                date_to, account["nr"], account["sign"], only
                            )
                        d[k]["C4"]["value"] = date_from_value
                        d[k]["C5"]["value"] = date_from_value

        # here we have the formulas in dictionary
        # get the sums - result of result for accounts
        for k, v in d.items():
            date_from_value, date_to_value = 0, 0
            if d[k].get("account_formula", {}):
                for account in d[k]["account_formula"]:
                    date_from_value += self.get_account_at_date(
                        date_from, account["nr"], account["sign"], only
                    )
                    date_to_value += self.get_account_at_date(
                        date_to, account["nr"], account["sign"], only
                    )
                d[k]["C4"]["value"] = date_from_value
                d[k]["C5"]["value"] = date_to_value
        # get the sums - result row sum of other values from dictionary
        for k, v in d.items():
            date_from_value, date_to_value = 0, 0
            if d[k].get("row_formula", {}):
                for row in d[k]["row_formula"]:
                    d_key_for_nr_rd = ""
                    for k1, v1 in d.items():
                        if v1.get("nr_rd", 0) == row["nr"]:
                            d_key_for_nr_rd = k1
                    if d_key_for_nr_rd:
                        date_from_value += d[d_key_for_nr_rd]["C4"]["value"] * (
                            -1 if row["sign"] == "-" else 1
                        )
                        date_to_value += d[d_key_for_nr_rd]["C5"]["value"] * (
                            -1 if row["sign"] == "-" else 1
                        )
                d[k]["C4"]["value"] = date_from_value
                d[k]["C5"]["value"] = date_to_value

        return d

    def report_html(
        self,
        test=True,
        date_from=False,
        date_to=False,
        company_id=False,
        show_formulas=False,
        arguments={},
    ):
        """ returns a html from given dictionary and filled with data with fill_data_py
        """
        self.ensure_one()
        filled_dictionary = self.function_fill_data(
            test, date_from, date_to, company_id, **arguments
        )
        if type(filled_dictionary) is not dict:
            return filled_dictionary
        self.final_dictionary_json = json.dumps(filled_dictionary)
        return self.dictionary_to_html(filled_dictionary, show_formulas=show_formulas)

    def test_report_html(
        self, test=True, date_from=False, date_to=False, company_id=False, arguments={}
    ):
        self.resulted_test_html = self.report_html(
            True, date_from, date_to, company_id, show_formulas=False, **arguments
        )

    def test_report_html_show_formulas(
        self, test=True, date_from=False, date_to=False, company_id=False, arguments={}
    ):
        self.resulted_test_html = self.report_html(
            True, date_from, date_to, company_id, show_formulas=True, **arguments
        )

    def report_xml(
        self, test=True, date_from=False, date_to=False, company_id=False, arguments={}
    ):
        """ returns a html from given dictionary and filled with data with fill_data_py
        """
        #         self.ensure_one()
        #         if not self.transform_to_xml:
        #             return f"<span>{fields.Datetime.now()} error you not have value in self.transform_to_xml :( </span>"
        #         self.filled_dictionary = self.function_fill_data(test,date_from,date_to,company_id,**arguments)
        #         res = eval(self.transform_to_xml)
        res = ""
        if not self.final_dictionary_json:
            raise ValidationError("Not a filled dictionary json, first make the html ")
        res += "  <F10Type>\n"
        for k, v in json.loads(self.final_dictionary_json).items():
            if v.get("C3", {}) and v["C3"]["value"] and v["C3"]["value"].isnumeric():
                nr_rd = int(v["C3"]["value"])
                if 1 <= nr_rd <= 104:
                    res += f"    <F10_{nr_rd:03}1>{v['C4']['value']}</F10_{nr_rd:03}1>"
                    res += (
                        f"    <F10_{nr_rd:03}2>{v['C4']['value']}</F10_{nr_rd:03}2>\n"
                    )
        res += "  </F10Type>\n"

        return res

    def test_report_xml(
        self, test=True, date_from=False, date_to=False, company_id=False, arguments={}
    ):
        self.resulted_test_xml = self.report_xml(
            True, date_from, date_to, company_id, **arguments
        )

    def verify_xml_with_local_xsd(self):
        parser = etree.XMLParser(dtd_validation=True)

        schema_root = etree.XML(self.report_xsd_local_link)  # must load it
        schema = etree.XMLSchema(schema_root)

        parser = etree.XMLParser(schema=schema)
        try:
            root = etree.fromstring(self.resulted_test_xml, parser)
            print("Finished validating good xml")
        except etree.XMLSyntaxError as err:
            print(err)

    def get_account_at_date(self, date, account_nr, account_sign, only=False):
        "just a function to return some values"
        sign = 1
        if account_sign == "-":
            sign = -1
        change = 1
        if date.day == 31:
            change = 10
        return account_nr * sign * change
