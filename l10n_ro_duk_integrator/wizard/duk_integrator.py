# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details
import base64
import logging
import os
import resource
import subprocess
import tempfile
from contextlib import closing

from odoo import fields, models
from odoo.tools.misc import find_in_path

_logger = logging.getLogger(__name__)


def _get_java_bin():
    return find_in_path("java")


MAX_VIRTUAL_MEMORY = 5024 * 1024 * 1024


def limit_virtual_memory():
    # The tuple below is of the form (soft limit, hard limit). Limit only
    # the soft part so that the limit can be increased later (setting also
    # the hard limit would prevent that).
    # When the limit cannot be changed, setrlimit() raises ValueError.
    resource.setrlimit(resource.RLIMIT_AS, (MAX_VIRTUAL_MEMORY, resource.RLIM_INFINITY))


class DUKIntegrator(models.TransientModel):
    _name = "duk.integrator"
    _description = "DUK Integrator"

    state = fields.Selection(
        [("choose", "choose"), ("get", "get")], default="choose"
    )  # choose period  # get the file
    xml_file_id = fields.Many2one(
        "ir.attachment", string="XML File", domain=[("name", "=ilike", "%.xml")]
    )

    file_name = fields.Char()
    data_file = fields.Binary()
    file_type = fields.Selection(
        [("D394", "D394"), ("FACT1", "Factura UBL"), ("FCII", "Factura CII")],
        default="D394",
    )

    error = fields.Text()
    output = fields.Text()

    def do_check_xml(self):

        try:
            subprocess.Popen(
                [_get_java_bin(), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError:
            _logger.info("You need DUKIntegrator.")
        else:
            _logger.info("Will use the Java binary at %s" % _get_java_bin())

        xml_content = self.xml_file_id.raw or base64.b64decode(self.data_file)

        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            duk_jar = os.path.join(module_path, "duk_integrator", "DUKIntegrator.jar")

            xml_file_fd, xml_file_path = tempfile.mkstemp(
                suffix=".xml", prefix="duk.tmp."
            )
            with closing(os.fdopen(xml_file_fd, "wb")) as xml_file:
                xml_file.write(xml_content)

            command_args = [
                "-v",  # validare declaratie
                self.file_type,
                xml_file_path,
            ]
            duk_integrator = (
                [_get_java_bin()]
                + ["-Xmx2048m", "-Xms2048m", "-jar", duk_jar]
                + command_args
            )
            process = subprocess.Popen(
                duk_integrator,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=limit_virtual_memory,
            )
            out, err = process.communicate()
            os.unlink(xml_file_path)
            error_file_name = xml_file_path + ".err.txt"
            if os.path.exists(error_file_name):
                with open(error_file_name, "r") as f:
                    err = f.read()
                os.unlink(error_file_name)

        except Exception as e:
            _logger.error("DUKIntegrator: %s" % str(e))
            raise

        self.write({"state": "get", "error": err, "output": out})

        return {
            "type": "ir.actions.act_window",
            "res_model": "duk.integrator",
            "view_mode": "form",
            "view_type": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }
