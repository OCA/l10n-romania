## 18.0.2.4.1 (2026-08-13)

- Matching an SPV message to an invoice no longer leaves the invoice in
  the `invoice_sent` E-Factura state. The EDI document created at match
  time is now `invoice_validated`, a terminal state: the document is
  already in the SPV (the message proves it) and this instance never
  uploaded it, so there is nothing to fetch a status for. With
  `invoice_sent`, the fetch-status cron queried ANAF with an empty
  `l10n_ro_edi_index`, failed on every run, logged the failure in the
  chatter and re-triggered itself every 2 minutes for as long as such an
  invoice existed — an endless loop. This shows up on self-billed
  invoices a customer issues in the supplier's name, which can only be
  matched by hand. Re-sending to the SPV stays blocked, as before.
- Invoices this instance did upload are unaffected: they already carry an
  EDI document with the upload index, so their normal
  `invoice_sent` -> `invoice_validated` flow and signature retrieval are
  untouched.

## 18.0.2.1.1 (2026-07-05)

- Clicking "Download embedded PDF" when the invoice XML has no embedded
  PDF now raises a user-friendly error instead of navigating to a raw
  404 page.
- The form view no longer shows the derived attachment fields (ZIP, XML,
  ANAF PDF, embedded PDF) with their file names, since those are only
  materialized on demand and often have no name to display. The four
  download actions are now buttons with suggestive icons in the form
  header instead.

## 18.0.2.0.0 (2026-07-02)

Storage optimization: the signed ANAF ZIP is now the only file stored per
SPV message.

- The XML extracted from the ZIP is no longer stored as a separate
  attachment at download time; the message metadata (reference, amount,
  invoice date, currency) is parsed in memory.
- `attachment_xml_id`, `attachment_anaf_pdf_id` and
  `attachment_embedded_pdf_id` became non-stored computed fields that
  expose the files materialized on the linked invoice.
- The XML is created once, directly on the vendor bill, when the invoice
  is created from the message; the PDF embedded in the XML is attached
  once on the bill as its preview (main attachment).
- The ANAF PDF and the embedded PDF are no longer persisted per message:
  the download buttons stream them on the fly, derived from the ZIP, via
  the new `/l10n_ro/message_spv/<id>/{xml,anaf_pdf,embedded_pdf}` routes.
- Migration: derived attachments of messages linked to an invoice are
  relinked to the invoice; those of messages without an invoice are
  deleted (they can be re-extracted from the ZIP), reclaiming the
  duplicated filestore space.
