Nothing to configure beyond what `l10n_ro_stock_account_retail` already
asks for. What that module needs, this one relies on:

1. **Retail warehouse.** Tick *Retail Warehouse* on the shop and give it
   its *Retail Pricelist*. That pricelist holds the shelf price (PVA),
   VAT included, and is the one this document writes back to.
2. **Accounts.** 371, 378 and 4428 must resolve for every product the
   shop holds — on the location, the product, its category or the
   company, mapped through the warehouse fiscal position if it has one.
   Posting refuses rather than guessing.
3. **Stock journal.** The entry is posted in the company's stock
   journal; the document also lets you pick another one per document.

Two things are worth doing once, before the first price change:

- **Settle the opening balance.** Stock that was on the shelf before
  `l10n_ro_stock_account_retail` was installed is in the quants and not
  in the markup ledger. Run *Retail Opening Balance* until it finds
  nothing. A price change document refuses to post while the ledger does
  not account for the same quantity it revalues, because the rate it
  applies is derived from the ledger.
- **Numbering.** Each company gets its own `PVSP/YYYY/00000` sequence,
  created on install and whenever a company is added. Change the prefix
  or padding per company under *Settings → Technical → Sequences* if the
  shop's own numbering differs.
