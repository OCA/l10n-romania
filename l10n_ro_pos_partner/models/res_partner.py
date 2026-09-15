# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import re

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _l10n_ro_pos_vat_to_cui(self, vat_number):
        """Return the bare CUI behind what the cashier typed in the search.

        The till is not the place to be picky about the shape: spaces and the
        ``RO`` prefix are what people actually type, and neither of them is
        part of the code ANAF is asked about.
        """
        vat = re.sub(r"\s+", "", vat_number or "").upper()
        if vat.startswith("RO"):
            vat = vat[2:]
        if not vat.isdigit():
            raise UserError(self.env._("Invalid CUI: %(vat)s", vat=vat_number))
        return vat

    @api.model
    def _l10n_ro_pos_partner_from_anaf(self, cui):
        """Create the partner ANAF holds under ``cui``."""
        anaf_error, result = self._get_Anaf(cui)
        if anaf_error:
            raise UserError(anaf_error)

        vals = self._Anaf_to_Odoo(result)
        if not vals:
            # No name back means ANAF knows nothing about this code; creating
            # a customer named after the CUI would only put a placeholder on
            # the receipt.
            raise UserError(
                self.env._("ANAF has no company registered under CUI %(cui)s.", cui=cui)
            )

        ro_country = self.env.ref("base.ro", raise_if_not_found=False)
        if ro_country:
            vals["country_id"] = ro_country.id
        # `_Anaf_to_Odoo` writes for an onchange, where a many2one may be the
        # record itself; `create` only takes its id.
        vals = {
            name: value.id if isinstance(value, models.BaseModel) else value
            for name, value in vals.items()
        }
        partner = self.create(vals)

        # Same ANAF history the backend keeps when the VAT is filled in on the
        # partner form, so it does not matter where the customer came from.
        history = partner._update_l10n_ro_anaf_status({}, result)
        history = partner._update_l10n_ro_anaf_scptva(history, result)
        if history:
            partner.write(history)

        _logger.info("POS: created partner %s (CUI %s) from ANAF", partner.name, cui)
        return partner

    @api.model
    def l10n_ro_pos_create_partner_from_vat(self, config_id, vat_number):
        """Return the customer holding ``vat_number``, fetching it if needed.

        Called from the customer search of the POS when nothing local matches
        the CUI. An already known customer is returned as it is -- the cashier
        searched by VAT, not by name, so a partner loaded under a name they
        did not think of is still the right one.
        """
        config = self.env["pos.config"].browse(config_id)
        cui = self._l10n_ro_pos_vat_to_cui(vat_number)

        partner = self.search(
            ["|", ("vat", "=ilike", cui), ("vat", "=ilike", "RO" + cui)],
            limit=1,
        )
        if not partner:
            partner = self._l10n_ro_pos_partner_from_anaf(cui)

        return {
            "res.partner": self._load_pos_data_read(partner, config),
            "account.fiscal.position": self.env[
                "account.fiscal.position"
            ]._load_pos_data_read(partner.fiscal_position_id, config),
        }
