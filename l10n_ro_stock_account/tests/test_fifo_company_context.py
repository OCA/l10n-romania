# Copyright (C) 2026 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""The per-location FIFO value must be computed in the record's own company,
not whatever company happens to be active (e.g. a multi-company batch or a
cross-company read)."""

from unittest.mock import patch


class FifoCompanyContextCases:
    def test_fifo_value_uses_the_record_company_not_the_active_one(self):
        self._receive(10, 5.0, 1)
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_fifo.id),
                ("location_id", "=", self.location.id),
            ],
            limit=1,
        )
        self.assertTrue(quant, "the receipt should have created a quant")

        # A second, non-FIFO company that the user may act under. Keep the
        # quant's own (FIFO) company in allowed_company_ids so the quant stays
        # readable, but make the other company the active one.
        other_company = self.env["res.company"].create({"name": "Non-FIFO Co"})
        self.env.user.write({"company_ids": [(4, other_company.id)]})
        quant = quant.with_context(
            allowed_company_ids=[other_company.id, quant.company_id.id]
        )
        self.assertEqual(
            quant.env.company,
            other_company,
            "the active company should be the non-FIFO one for this test",
        )

        seen = []
        Product = type(self.env["product.product"])
        original = Product._run_fifo_value

        def _spy(product, *args, **kwargs):
            seen.append(product.env.company.id)
            return original(product, *args, **kwargs)

        with patch.object(Product, "_run_fifo_value", _spy):
            quant._compute_value()

        self.assertTrue(seen, "the per-location FIFO value path was not exercised")
        self.assertTrue(
            all(company_id == quant.company_id.id for company_id in seen),
            "FIFO value must be computed in the quant's own company, not the "
            "active company",
        )
