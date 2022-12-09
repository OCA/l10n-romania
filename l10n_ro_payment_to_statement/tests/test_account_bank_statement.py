# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from .common import TestPaymenttoStatement


class TestPayment(TestPaymenttoStatement):
    def setUp(self):
        super(TestPayment, self).setUp()

    # Test Bank Statement name in create
    # 1 test for cash with sequence
    # 2 set l10n_ro_statement_sequence_id for one bank journal

    # Test name get
