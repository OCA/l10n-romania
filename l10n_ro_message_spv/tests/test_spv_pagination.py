# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
from datetime import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_ro_message_spv.models.ciusro_document import (
    SPV_MAX_PAGES,
    SPV_MESSAGES_RETENTION_DAYS,
)

from .common import TestMessageSPV

CIF = "30834857"
LOGGER = "odoo.addons.l10n_ro_message_spv.models.ciusro_document"


def _message(index):
    """Un mesaj ANAF minimal, dar cu toate cheile pe care le citeste importul."""
    return {
        "data_creare": "202609010940",
        "cif": CIF,
        "id_solicitare": f"500000{index}",
        "detalii": (
            f"Factura cu id_incarcare=500000{index} emisa de cif_emitent=8486152 "
            f"pentru cif_beneficiar={CIF}"
        ),
        "tip": "FACTURA PRIMITA",
        "id": f"300000{index}",
    }


def _page(messages, numar_total_pagini):
    payload = {
        "mesaje": messages,
        "serial": "1234AA456",
        "cui": CIF,
        "titlu": "Lista Mesaje disponibile",
        "numar_total_pagini": numar_total_pagini,
    }
    return {"content": json.dumps(payload).encode("utf-8")}


@tagged("post_install", "-at_install")
class TestSpvPagination(TestMessageSPV):
    """Paginarea listei de mesaje din SPV.

    ANAF refuza cu totul intervalele de peste 500 de mesaje pe endpointul
    nepaginat, iar la clientii mari o singura zi depaseste pragul, deci importul
    depinde de parcurgerea corecta a paginilor si de raportarea eșecurilor.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.document = cls.env["l10n_ro_edi.document"]

    def _fetch(self, responses, **kwargs):
        """Ruleaza importul cu `responses` servite pe rand, si intoarce
        (mesaje, parametrii fiecarui apel)."""
        calls = []

        def fake_request(session, company, endpoint, params, data=None):
            calls.append(params)
            return responses[min(len(calls) - 1, len(responses) - 1)]

        with patch(f"{LOGGER}.make_efactura_request", side_effect=fake_request):
            messages = self.document._request_ciusro_download_messages_spv(
                self.env.company, **kwargs
            )
        return messages, calls

    def test_walks_every_page(self):
        """Toate paginile sunt parcurse, iar mesajele se acumuleaza in ordine."""
        responses = [
            _page([_message(1), _message(2)], 3),
            _page([_message(3)], 3),
            _page([_message(4)], 3),
        ]
        messages, calls = self._fetch(responses)

        self.assertEqual(
            [m["id"] for m in messages], ["3000001", "3000002", "3000003", "3000004"]
        )
        self.assertEqual([p["pagina"] for p in calls], [1, 2, 3])

    def test_single_page_does_not_ask_for_a_second(self):
        """O singura pagina nu declanseaza un apel in plus."""
        messages, calls = self._fetch([_page([_message(1)], 1)])

        self.assertEqual(len(messages), 1)
        self.assertEqual(len(calls), 1)

    def test_error_on_middle_page_keeps_pages_already_read(self):
        """Eroarea pe o pagina din mijloc nu pierde paginile citite, dar e logata.

        Fara logare, rezultatul partial ar fi indistingibil de un import complet.
        """
        responses = [
            _page([_message(1)], 3),
            {"error": "Timeout while sending to SPV."},
        ]

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            messages, calls = self._fetch(responses)

        self.assertEqual([m["id"] for m in messages], ["3000001"])
        self.assertEqual([p["pagina"] for p in calls], [1, 2])
        self.assertIn("Rezultat partial: 1 mesaje", "\n".join(logs.output))

    def test_business_error_is_logged_and_stops(self):
        """O eroare de business a ANAF (HTTP 200 cu `eroare`) e logata ca eroare."""
        payload = {"eroare": "Nu aveti drept in SPV pentru CIF=30834857"}
        response = {"content": json.dumps(payload).encode("utf-8")}

        with self.assertLogs(LOGGER, level="ERROR") as logs:
            messages, calls = self._fetch([response])

        self.assertEqual(messages, [])
        self.assertEqual(len(calls), 1)
        self.assertIn("Nu aveti drept in SPV", "\n".join(logs.output))

    def test_no_results_note_is_not_an_error(self):
        """„Nu exista mesaje" vine tot pe cheia `eroare`, dar nu e o eroare."""
        payload = {"eroare": "Nu exista mesaje in intervalul selectat"}
        response = {"content": json.dumps(payload).encode("utf-8")}

        with self.assertLogs(LOGGER, level="INFO") as logs:
            messages, _calls = self._fetch([response])

        self.assertEqual(messages, [])
        self.assertFalse([line for line in logs.output if line.startswith("ERROR")])

    def test_unparsable_body_is_logged_and_stops(self):
        """Un corp neparsabil (pagina HTML de mentenanta) nu ridica excepție."""
        with self.assertLogs(LOGGER, level="ERROR") as logs:
            messages, calls = self._fetch([{"content": b"<html>mentenanta</html>"}])

        self.assertEqual(messages, [])
        self.assertEqual(len(calls), 1)
        self.assertIn("neparsabil", "\n".join(logs.output))

    def test_absurd_total_pages_is_capped(self):
        """Un `numar_total_pagini` absurd nu ne trimite intr-o bucla lunga."""
        with self.assertLogs(LOGGER, level="ERROR") as logs:
            messages, calls = self._fetch([_page([_message(1)], 10**6)])

        self.assertEqual(len(calls), SPV_MAX_PAGES)
        self.assertEqual(len(messages), SPV_MAX_PAGES)
        self.assertIn("garda de", "\n".join(logs.output))

    def test_messages_of_other_cifs_are_dropped(self):
        """Mesajele altor CIF-uri nu intra in lista companiei."""
        other = dict(_message(9), cif="99999999")
        messages, _calls = self._fetch([_page([_message(1), other], 1)])

        self.assertEqual([m["id"] for m in messages], ["3000001"])

    def test_window_start_is_pulled_inside_the_retention_limit(self):
        """Fereastra de 60 de zile — implicitul de pe companie — nu se cere pe limita.

        ANAF respinge intervalul daca `startTime` e mai vechi de 60 de zile fata de
        momentul requestului, iar codul scadea zilele dintr-un `now` deja retras cu
        60 de secunde, deci cadea mereu cu o secunda in afara.
        """
        _messages, calls = self._fetch(
            [_page([], 1)], no_days=SPV_MESSAGES_RETENTION_DAYS
        )

        start = datetime.fromtimestamp(int(calls[0]["startTime"]) / 1000)
        limit = datetime.now() - relativedelta(days=SPV_MESSAGES_RETENTION_DAYS)
        self.assertGreater(start, limit)


@tagged("post_install", "-at_install")
class TestSpvCronEntryPoints(TestMessageSPV):
    """Punctele de intrare folosite din codul cronurilor."""

    def test_public_entry_point_accepts_no_days(self):
        """Wrapperul public accepta `no_days` si isi rezolva singur companiile.

        Fara parametru, un cron care vrea alta fereastra decat cea de pe companie
        e nevoit sa cheme metoda privata pe modelul gol (`model._l10n_ro_...`), care
        itereaza `self` si deci nu face nimic — fara eroare si fara log.
        """
        with patch(
            f"{LOGGER}.make_efactura_request", return_value=_page([_message(1)], 1)
        ):
            self.env["res.company"].l10n_ro_download_message_spv(no_days=7)

        message = self.env["l10n.ro.message.spv"].search([("name", "=", "3000001")])
        self.assertEqual(len(message), 1)
        self.assertEqual(message.company_id, self.env.company)

    def test_expired_error_messages_are_not_retried(self):
        """Mesajele in eroare ieșite din fereastra ANAF nu se mai reincearca.

        Arhiva lor nu mai exista, deci resetarea zilnica la draft le-ar tine
        perpetuu in coada, consumand apeluri fara nicio sansa de reusita.
        """
        yesterday = fields.Date.today() - relativedelta(days=1)
        common = {
            "company_id": self.env.company.id,
            "message_type": "in_invoice",
            "state": "error",
            "download_attempts": 3,
            "last_download_date": yesterday,
        }
        expired = self.env["l10n.ro.message.spv"].create(
            dict(
                common,
                name="EXPIRAT",
                date=fields.Datetime.now()
                - relativedelta(days=SPV_MESSAGES_RETENTION_DAYS + 10),
            )
        )
        recent = self.env["l10n.ro.message.spv"].create(
            dict(
                common,
                name="RECENT",
                date=fields.Datetime.now() - relativedelta(days=5),
            )
        )
        undated = self.env["l10n.ro.message.spv"].create(dict(common, name="FARA_DATA"))

        # limit=0 ca sa testam doar resetul, fara nicio descarcare efectiva
        self.env.company.l10n_ro_download_zip_message_spv(limit=0)

        self.assertEqual(expired.state, "error", "un mesaj expirat nu se reincearca")
        self.assertEqual(expired.download_attempts, 3)
        self.assertEqual(recent.state, "draft", "un mesaj recent revine in coada")
        self.assertEqual(recent.download_attempts, 0)
        self.assertEqual(
            undated.state, "draft", "lipsa datei nu e dovada ca arhiva a expirat"
        )
