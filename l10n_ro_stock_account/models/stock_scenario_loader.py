# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import os

import odoo.modules
from odoo import api, models

from ..scenario import StockScenario

_logger = logging.getLogger(__name__)


class DemoScenario(StockScenario):
    """Runs the scenarios of a CSV against records loaded from XML.

    The tests resolve the names in a CSV against what they built in
    ``setUpClass``; demo data has external identifiers instead, so the host
    carries the map from one to the other.
    """

    # The scenarios reach for these by attribute rather than through the CSV,
    # so a demo names them in the same alias map and they are resolved here.
    _RECORD_OPTIONS = (
        "landed_cost",
        "advance_product",
        "transit_loc",
        "transit_route",
    )

    def __init__(self, env, aliases, options=None):
        self.env = env
        self._aliases = aliases or {}
        for key, value in (options or {}).items():
            setattr(self, key, value)
        for name in self._RECORD_OPTIONS:
            if name in self._aliases:
                setattr(self, name, self._resolve(name))

    def _resolve(self, name):
        """Look the name up in the alias map, then by external identifier.

        A name the map does not know is returned as nothing rather than
        raising: the scenarios read several optional columns, and a lot or a
        second location that a demo does not use has to stay empty.

        A product is returned as its variant, because that is what the
        scenarios move, while demo data names the template.
        """
        xmlid = self._aliases.get(name, name)
        if "." not in xmlid:
            return getattr(self, name, None)
        record = self.env.ref(xmlid, raise_if_not_found=False)
        if record and record._name == "product.template":
            return record.product_variant_id
        return record


class StockScenarioLoader(models.AbstractModel):
    _name = "l10n.ro.stock.scenario.loader"
    _description = "Loads the Romanian stock scenarios as demo data"

    @api.model
    def _load_cases(self, module, filename, aliases, options=None, only=None):
        """Build the documents of ``filename`` as demo data.

        ``aliases`` maps the names used in the CSV to external identifiers,
        ``only`` keeps the cases whose ``case_no`` it lists, so one file can
        serve both a full test run and a handful of demo scenarios.
        """
        module_dir = os.path.join(odoo.modules.module.get_module_path(module))
        host = DemoScenario(self.env, aliases, options)
        cases = host.read_test_cases_from_csv_file(
            filename, module_dir=module_dir, subdir="demo/cases"
        )
        wanted = set(only or [])
        for code, case in cases.items():
            if wanted and code not in wanted:
                continue
            _logger.info("Demo scenario %s: %s", code, case.get("name"))
            host.run_test_case(case)
        return True
