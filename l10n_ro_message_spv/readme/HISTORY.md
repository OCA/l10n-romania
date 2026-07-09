**19.0.2.1.2 (2026-07-09)**

- Fixed duplicate vendor bills when a bill already exists in Odoo (e.g.
  created from a purchase order) and is still in draft when the matching
  invoice is later downloaded from SPV: the deduplication search used to
  only match `posted` invoices, so a draft bill with the same reference
  and vendor was never found, and a second draft bill was created for the
  same document. The search now matches any non-cancelled invoice.

**19.0.2.1.1 (2026-07-05)**

- Clicking "Download embedded PDF" when the invoice XML has no embedded
  PDF now raises a user-friendly error instead of navigating to a raw
  404 page.
- The form view no longer shows the derived attachment fields (ZIP, XML,
  ANAF PDF, embedded PDF) with their file names, since those are only
  materialized on demand and often have no name to display. The four
  download actions are now buttons with suggestive icons in the form
  header instead.

**19.0.2.0.0 (2026-07-02)**

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
