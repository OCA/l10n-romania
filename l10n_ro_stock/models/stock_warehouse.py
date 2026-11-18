# Copyright (C) 2016 Forest and Biomass Romania
# Copyright (C) 2018 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockWarehouse(models.Model):
    _name = "stock.warehouse"
    _inherit = ["stock.warehouse", "l10n.ro.mixin"]

    l10n_ro_consume_type_id = fields.Many2one(
        "stock.picking.type", string="Romania - Consume Type"
    )
    l10n_ro_usage_type_id = fields.Many2one(
        "stock.picking.type", string="Romania - Usage Giving Type"
    )

    def _get_picking_type_update_values(self):
        res = super()._get_picking_type_update_values()
        if self.is_l10n_ro_record:
            if self.company_id.l10n_ro_consume_location_id:
                res.update({"l10n_ro_consume_type_id": {}})
            if self.company_id.l10n_ro_usage_location_id:
                res.update({"l10n_ro_usage_type_id": {}})
        return res

    def _get_picking_type_create_values(self, max_sequence):
        create_data, max_sequence = super()._get_picking_type_create_values(
            max_sequence
        )
        if self.is_l10n_ro_record:
            usage_location = self.company_id.l10n_ro_usage_location_id
            consume_location = self.company_id.l10n_ro_consume_location_id
            if consume_location:
                create_data.update(
                    {
                        "l10n_ro_consume_type_id": {
                            "name": self.env._("Consume"),
                            "code": "internal",
                            "use_create_lots": True,
                            "use_existing_lots": False,
                            "default_location_src_id": self.lot_stock_id.id,
                            "default_location_dest_id": consume_location.id,  # noqa
                            "sequence": max_sequence + 6,
                            "barcode": self.code.replace(" ", "").upper() + "-CONSUME",
                            "sequence_code": "CONS",
                            "company_id": self.company_id.id,
                        }
                    }
                )
            if usage_location:
                create_data.update(
                    {
                        "l10n_ro_usage_type_id": {
                            "name": self.env._("Usage Giving"),
                            "code": "internal",
                            "use_create_lots": True,
                            "use_existing_lots": False,
                            "default_location_src_id": self.lot_stock_id.id,
                            "default_location_dest_id": usage_location.id,  # noqa
                            "sequence": max_sequence + 7,
                            "barcode": self.code.replace(" ", "").upper() + "-USAGE",
                            "sequence_code": "USAGE",
                            "company_id": self.company_id.id,
                        },
                    }
                )
            max_sequence += 2
        return create_data, max_sequence

    def _create_or_update_sequences_and_picking_types(self):
        """Operatiile de retur ale unei firme romanesti.

        Patru drumuri inapoi, pentru cele patru pe care marfa iese din
        gestiune: receptia, livrarea, consumul si darea in folosinta. Fiecare
        are tipul lui, ca in registrul de miscari returul sa nu se amestece
        cu o livrare obisnuita sau cu o mutare intre locatii.

        Locatiile conteaza mai mult decat par: de pe destinatie citeste Odoo
        felul notei contabile. Catre un furnizor, miscarea e retur de
        achizitie si se scade din contul pe care a intrat marfa; catre un
        client, se contabilizeaza ca o livrare, pe cheltuiala cu marfa
        vanduta. Un retur catre furnizor trimis spre "Customers" iese cu nota
        unei vanzari -- si asa ies tipurile create fara locatii.

        Nimic nu se dubleaza: un tip se cauta intai dupa codul lui de
        secventa, deci acolo unde exista deja -- creat de mana sau de alt
        modul -- el este cel folosit si completat, nu unul nou langa el.
        """
        res = super()._create_or_update_sequences_and_picking_types()
        if self.is_l10n_ro_record:
            # Tipurile tocmai create nu sunt inca pe depozit: Odoo le scrie
            # pe campuri abia dupa ce metoda asta se intoarce. Pana atunci
            # ele exista doar in ce s-a intors, deci de acolo se iau.
            self._l10n_ro_build_return_types(res)
        return res

    def _l10n_ro_type_from(self, data, field):
        """Tipul de operatiune, de pe depozit sau din ce tocmai s-a creat."""
        self.ensure_one()
        return (
            self[field]
            or self.env["stock.picking.type"].browse(data.get(field)).exists()
        )

    def _l10n_ro_location_by_usage(self, usage):
        return self.env["stock.location"].search(
            [("usage", "=", usage), ("company_id", "in", [False, self.company_id.id])],
            limit=1,
        )

    def _l10n_ro_return_type_values(self, data):
        """Ce tip de retur ii trebuie fiecarei operatii, si pe ce drum.

        ``(operatia dus, cod, nume, felul miscarii, sursa, destinatia)``,
        pentru fiecare operatie prin care marfa iese din gestiune.
        """
        self.ensure_one()
        stock = self.lot_stock_id
        vendors = self._l10n_ro_location_by_usage("supplier")
        customers = self._l10n_ro_location_by_usage("customer")
        consume = self.company_id.l10n_ro_consume_location_id
        usage = self.company_id.l10n_ro_usage_location_id
        values = []
        if vendors:
            values.append(
                (
                    self._l10n_ro_type_from(data, "in_type_id"),
                    "INR",
                    self.env._("Return of purchase"),
                    "outgoing",
                    stock,
                    vendors,
                )
            )
        if customers:
            values.append(
                (
                    self._l10n_ro_type_from(data, "out_type_id"),
                    "OUTR",
                    self.env._("Return of sales"),
                    "incoming",
                    customers,
                    stock,
                )
            )
        if consume:
            values.append(
                (
                    self._l10n_ro_type_from(data, "l10n_ro_consume_type_id"),
                    "CONSR",
                    self.env._("Return of consumption"),
                    "internal",
                    consume,
                    stock,
                )
            )
        if usage:
            values.append(
                (
                    self._l10n_ro_type_from(data, "l10n_ro_usage_type_id"),
                    "USAGER",
                    self.env._("Return of usage giving"),
                    "internal",
                    usage,
                    stock,
                )
            )
        return values

    def _l10n_ro_build_return_types(self, data):
        """Gaseste sau creeaza tipurile de retur, si le imperecheaza."""
        self.ensure_one()
        PickingType = self.env["stock.picking.type"]
        for (
            forward,
            code,
            name,
            direction,
            src,
            dest,
        ) in self._l10n_ro_return_type_values(data):
            if not forward:
                continue
            backward = PickingType.search(
                [
                    ("sequence_code", "=", code),
                    ("warehouse_id", "=", self.id),
                    "|",
                    ("company_id", "=", self.company_id.id),
                    ("company_id", "=", False),
                ],
                limit=1,
            )
            if not backward:
                sequence = (
                    self.env["ir.sequence"]
                    .sudo()
                    .create(
                        {
                            "name": f"{self.name} {name}",
                            "prefix": f"{self.code}/{code}/",
                            "padding": 5,
                            "company_id": self.company_id.id,
                        }
                    )
                )
                backward = PickingType.create(
                    {
                        "name": name,
                        "code": direction,
                        "sequence_code": code,
                        "sequence_id": sequence.id,
                        "use_create_lots": False,
                        "use_existing_lots": True,
                        "company_id": self.company_id.id,
                        "warehouse_id": self.id,
                    }
                )
            backward.write(
                {
                    "default_location_src_id": src.id,
                    "default_location_dest_id": dest.id,
                }
            )
            if forward.return_picking_type_id != backward:
                forward.return_picking_type_id = backward
            if backward.return_picking_type_id != forward:
                backward.return_picking_type_id = forward

    def _get_sequence_values(self, name=False, code=False):
        sequences = super()._get_sequence_values(name=name, code=code)
        if self.is_l10n_ro_record:
            sequences.update(
                {
                    "l10n_ro_consume_type_id": {
                        "name": self.name + " " + self.env._("Sequence Consume"),
                        "prefix": self.code + "/CONS/",
                        "padding": 5,
                        "company_id": self.company_id.id,
                    },
                    "l10n_ro_usage_type_id": {
                        "name": self.name + " " + self.env._("Sequence Usage Giving"),
                        "prefix": self.code + "/USAGE/",
                        "padding": 5,
                        "company_id": self.company_id.id,
                    },
                }
            )
        return sequences

    def _update_name_and_code(self, new_name=False, new_code=False):
        res = super()._update_name_and_code(new_name, new_code)
        ro_whs = self.filtered("is_l10n_ro_record")
        for warehouse in ro_whs:
            sequence_data = warehouse._get_sequence_values()
            warehouse.l10n_ro_consume_type_id.sequence_id.sudo().write(
                sequence_data["l10n_ro_consume_type_id"]
            )
            warehouse.l10n_ro_usage_type_id.sequence_id.sudo().write(
                sequence_data["l10n_ro_usage_type_id"]
            )
        return res
