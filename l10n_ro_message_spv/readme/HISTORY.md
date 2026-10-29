**19.0.2.14.0 (2026-09-10)**

- The paginated SPV message listing no longer fails silently. A page that
  cannot be read — transport error, unparsable body (an ANAF maintenance
  page), an HTTP 200 carrying a business error, or a `401` — now stops the
  walk and is logged as an error, stating how many messages the partial
  result holds. Until now any of those left the total page count at zero
  and returned an empty or partial list without a single log line, so an
  import stopped by an ANAF error looked exactly like "no messages" and
  the cron reported success. ANAF's "no messages in the selected
  interval" note, which arrives in the same `eroare` key, is recognised
  and logged as information rather than as a failure. The import also
  logs a per-company summary of how many messages were received and how
  many records were created.
- Pages are now walked in a loop instead of recursively, with a guard at
  200 pages (100 000 messages), so an absurd `numar_total_pagini` can no
  longer drive the walk into the recursion limit.
- The requested time window is pulled inside ANAF's limits. ANAF rejects
  the whole interval when `startTime` is older than 60 days relative to
  its own clock, and the window was computed by subtracting the requested
  days from a moment already pushed 60 seconds into the past — so the
  default 60-day window sat just outside the limit.
- `l10n_ro_download_message_spv` accepts `no_days`. Without it, a cron
  that wants a window other than the one configured on the company had to
  call the private `_l10n_ro_download_message_spv` on the bare model;
  that method iterates `self`, so on an empty recordset it did nothing at
  all — no error, no log, and the cron still reported success.
- Messages whose download failed are no longer retried once they fall
  outside ANAF's 60-day retention. Their archive no longer exists, so the
  daily `error` to `draft` reset kept them in the queue forever, burning
  API calls and filling the log. A message with no date is still treated
  as recoverable.

**19.0.2.11.0 (2026-08-19)**

- The partner lookup by tax ID now accepts both spellings of the Romanian
  CIF. ANAF sends the code sometimes with and sometimes without the `RO`
  prefix, while the partner in Odoo may hold the other variant; the
  lookup used to fail in that case and a duplicate `Unknown` partner was
  created for a company already in the database. Both variants are now
  searched, and the tax ID written on a newly created partner is
  normalized without the prefix.
- Multi-company isolation on SPV messages: `Invoice`, `Partner` and
  `Attachment` are company-checked, the downloaded ZIP is stored in the
  message's company, the invoice is created explicitly in that company,
  and the partner lookup/creation is restricted to the message's company
  (or to partners shared between companies). The `Company` field is shown
  in the list, form and search views, together with a `Company` grouping,
  only for users with multi-company rights.

**19.0.2.9.1 (2026-08-13)**

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

**19.0.2.7.0 (2026-07-28)**

- The product can now be corrected on a bill line imported from SPV
  without losing the data received from the supplier: the description
  and the unit price read from the XML are kept when a different product
  is selected. Previously the description was overwritten with the
  product name as soon as the product changed on bills fetched by the
  standard `l10n_ro_edi` SPV import (those bills carry
  `l10n_ro_edi_index`, not `l10n_ro_edi_download`, so the former guard
  did not apply to them).
- The guard is now evaluated per line instead of per bill: lines added
  by hand on an SPV bill are filled in from the product as usual, while
  the imported lines keep their SPV values.
- The vendor item code received from SPV is available as an optional
  column on the bill lines, so the user can see what the supplier
  invoiced while correcting the product.

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
