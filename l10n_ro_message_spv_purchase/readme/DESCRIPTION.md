This addon extends the Romanian SPV message model (`l10n.ro.message.spv`)
to help procure-to-pay flows by linking SPV messages with purchase orders
and keeping the purchase order chatter and attachments in sync.

## Key features

- New fields on the SPV message:
  - `Purchase Reference` (`purchase_ref`) — extracted automatically from the
    invoice XML (`OrderReference/ID`) when available.
  - `Purchase Order` (`purchase_order_id`) — the linked purchase order, if any.
- Two dedicated actions on the SPV message form:
  - **Find Purchase**: searches purchase orders by reference (using
    `purchase_ref` with fallback to `ref`) across `partner_ref`, `origin` or
    `name`, narrowed by partner/company when available.
  - **Create Purchase**: performs the same search; when none is found and a
    partner is set, creates a draft purchase order and links it.
- When a purchase order is found or created, a note is posted in its chatter
  with the SPV XML attached.
- The SPV XML is copied on the purchase order (not just referenced); when the
  message is not yet linked to an invoice, the XML is derived on the fly from
  the signed ZIP downloaded from ANAF.
- Duplicate attachments on the purchase order are prevented, based on
  checksum (with fallback to name and mimetype).
