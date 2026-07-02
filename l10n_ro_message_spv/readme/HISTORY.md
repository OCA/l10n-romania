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
