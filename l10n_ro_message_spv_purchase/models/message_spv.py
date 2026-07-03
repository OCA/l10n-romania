# Copyright (C) 2025 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MessageSPV(models.Model):
    _inherit = "l10n.ro.message.spv"

    purchase_ref = fields.Char(string="Purchase Reference")
    purchase_order_id = fields.Many2one("purchase.order")

    def process_xml(self, xml_tree):
        values = super().process_xml(xml_tree)
        order_reference = xml_tree.findtext("./{*}OrderReference/{*}ID")

        if order_reference:
            values["purchase_ref"] = order_reference

        return values

    def _get_purchase_ref(self):
        self.ensure_one()
        return self.purchase_ref or self.ref

    def _post_spv_xml_on_purchase(self, purchase):
        """Post a note in the purchase order chatter with the SPV XML attached.

        The XML attachment is copied on the purchase order (deduplicated by
        checksum); when no XML can be obtained, only the note is posted.
        """
        self.ensure_one()

        po_xml_attachment = self._clone_xml_attachment_for_purchase(purchase)

        ref_to_use = self._get_purchase_ref() or "-"
        body = _(
            "Linked from SPV message %(msg)s (Ref: %(ref)s).",
            msg=self.name or "-",
            ref=ref_to_use,
        )

        post_kwargs = {
            "body": body,
            "subtype_xmlid": "mail.mt_note",
        }
        if po_xml_attachment:
            post_kwargs["attachment_ids"] = [po_xml_attachment.id]

        purchase.message_post(**post_kwargs)

    def _clone_xml_attachment_for_purchase(self, purchase):
        """Create a copy of the SPV XML attachment on the purchase order.

        The XML is taken from the invoice attachment when the message is
        already linked to an invoice; otherwise it is derived on the fly
        from the stored signed ZIP.
        Deduplicates by checksum (or name) on the order.
        Returns the attachment on the purchase order (existing or newly
        created) or False when no XML is available.
        """
        self.ensure_one()
        checksum = False
        xml_att = self.attachment_xml_id.sudo()
        if xml_att and xml_att.datas:
            name = xml_att.name or "spv.xml"
            datas = xml_att.datas
            checksum = xml_att.checksum
        else:
            file_name, xml_bytes = self._get_xml_bytes()
            if not xml_bytes:
                return False
            name = file_name or f"{self.name}.xml"
            datas = base64.b64encode(xml_bytes)

        attachment_obj = self.env["ir.attachment"].sudo()

        # Look for an existing copy on this order, by checksum (preferred)
        # or by name and mimetype.
        domain = [
            ("res_model", "=", "purchase.order"),
            ("res_id", "=", purchase.id),
        ]
        existing = False
        if checksum:
            existing = attachment_obj.search(
                domain + [("checksum", "=", checksum)], limit=1
            )
        if not existing:
            existing = attachment_obj.search(
                domain + [("name", "=", name), ("mimetype", "=", "application/xml")],
                limit=1,
            )

        if existing:
            return existing

        return attachment_obj.create(
            {
                "name": name,
                "datas": datas,
                "mimetype": "application/xml",
                "res_model": "purchase.order",
                "res_id": purchase.id,
                "company_id": purchase.company_id.id or self.env.company.id,
                "description": _(
                    "XML copy from SPV message %(msg)s (Ref: %(ref)s)",
                    msg=self.name or "-",
                    ref=self._get_purchase_ref() or "-",
                ),
            }
        )

    def _action_open_purchase_list(self, domain):
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": domain,
            "target": "current",
        }

    @api.model
    def _purchase_search_domain_from_ref(
        self, ref_to_use, partner_id=False, company_id=False
    ):
        # Build a FLAT domain (no nested lists): prefix AND conditions,
        # then the OR group matching the reference fields.
        domain = [
            "|",
            "|",
            ("partner_ref", "=", ref_to_use),
            ("origin", "=", ref_to_use),
            ("name", "=", ref_to_use),
        ]

        if partner_id:
            domain = ["&", ("partner_id", "=", partner_id)] + domain
        if company_id:
            domain = ["&", ("company_id", "=", company_id)] + domain

        return domain

    def action_find_purchase(self):
        """Find and link a purchase order by reference, without creating one.

        - Exactly one match: link it, post the note and open its form.
        - Several matches: open the list filtered by the search domain.
        - No match: raise an informative error (nothing is created).
        """
        self.ensure_one()
        ref_to_use = self._get_purchase_ref()
        if not ref_to_use:
            raise UserError(
                _(
                    "There is no reference to search the purchase order by. "
                    "Fill in the Reference or Purchase Reference field."
                )
            )

        purchase_order_obj = self.env["purchase.order"]
        domain = self._purchase_search_domain_from_ref(
            ref_to_use,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )

        found = purchase_order_obj.search(domain, limit=2)

        if len(found) == 1:
            self.purchase_order_id = found.id
            self._post_spv_xml_on_purchase(found)
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "res_id": found.id,
                "view_mode": "form",
                "target": "current",
            }

        if len(found) > 1:
            return self._action_open_purchase_list(domain)

        raise UserError(
            _(
                "No purchase order was found for reference '%s'.",
                ref_to_use,
            )
        )

    def action_create_purchase(self):
        """Search for the purchase order by reference; create one if not found.

        - One match: link it, post the note with the XML and open it.
        - Several matches: open the list to choose from (nothing is created).
        - No match: create a draft purchase order for the message partner,
          link it and open it. Raise an error when the partner is missing.
        """
        self.ensure_one()
        ref_to_use = self._get_purchase_ref()
        if not ref_to_use:
            raise UserError(
                _(
                    "There is no reference to search or create the purchase "
                    "order by. Fill in the Reference or Purchase Reference "
                    "field."
                )
            )

        purchase_order_obj = self.env["purchase.order"]
        domain = self._purchase_search_domain_from_ref(
            ref_to_use,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )

        found = purchase_order_obj.search(domain, limit=2)

        if len(found) == 1:
            self.purchase_order_id = found.id
            self._post_spv_xml_on_purchase(found)
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "res_id": found.id,
                "view_mode": "form",
                "target": "current",
            }

        if len(found) > 1:
            return self._action_open_purchase_list(domain)

        if not self.partner_id:
            raise UserError(
                _(
                    "There is no partner set on the message. Set the partner "
                    "before creating the purchase order."
                )
            )

        purchase = purchase_order_obj.create(
            {
                "partner_id": self.partner_id.id,
                "partner_ref": ref_to_use,
                "origin": self.name or ref_to_use,
                "company_id": self.company_id.id,
            }
        )
        self.purchase_order_id = purchase.id
        self._post_spv_xml_on_purchase(purchase)
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "res_id": purchase.id,
            "view_mode": "form",
            "target": "current",
        }
