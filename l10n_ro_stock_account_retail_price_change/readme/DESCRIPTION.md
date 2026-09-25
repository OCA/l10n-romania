# Romania - Retail Price Change (Proces Verbal de Schimbare Pret)

Adds the price change document to the retail merchandise accounting of
`l10n_ro_stock_account_retail`.

`l10n.ro.retail.price.change` is a persistent document numbered
`PVSP/YYYY/00000` out of a sequence of its own company. It captures the
warehouse, the date, the products on hand and the old versus new shelf
price (PVA, VAT included) per line, with the markup (378) and deferred
VAT (4428) split.

The old side is what the stock carries — cost, markup and deferred VAT
per unit, read from the markup ledger — and it is read again when the
document is posted, so the delta always measures the gap that exists at
the moment the entry is made. A posted document is final: it is revoked
by posting another one, never reset, cancelled or deleted.

There are three flows:

1. **Manual** - create a draft, load the products on hand, edit the new
   prices, then post. Posting writes the new prices on the warehouse
   retail pricelist, books the revaluation and records it in the markup
   ledger, so the next sale releases the new markup and not the old one.
2. **Automatic** - a draft document is raised for each affected retail
   warehouse whenever a shelf price moves, and the user reviews it and
   posts it. What decided the price does not matter: a fixed rule, a rule
   over a category or the whole shop, any term of a formula, a change on
   another pricelist the shop derives from, or the product's own sale
   price. The price before and the price after are compared per product
   and per shop, so a rule that names a whole range raises a document
   holding the labels that actually moved.

   A shop has at most one open automatic document, topped up as prices
   keep moving, so it always quotes the price that is on the label.

   Posting writes a fixed rule back on the pricelist only where the
   pricelist does not already answer with the price decided, which is
   what keeps a shop priced by formula priced by formula.

3. **Reconciled** - a daily cron, *Retail: Reconcile Shelf Prices*,
   compares what the markup ledger says each unit on the shelf carries
   with what the pricelist says the label reads, and raises a draft
   wherever the two have parted company. That catches the prices which
   move with nobody writing anything: the day a dated promotion opens, a
   shelf price computed over a cost that a reception has moved, a change
   of VAT rate. Stock the ledger does not yet account for is left to the
   opening balance wizard.

## Report

The document prints as *Proces-verbal privind modificarea pretului de
vanzare cu amanuntul*, listing quantity, old and new price, old and new
value and the difference per product, with the markup and VAT split
shown separately.

## Price history

Every posted document is a dated record of the shelf price of the
products it covers. The *Price History* button on a product shows the
lines that concern it, oldest first, so the sequence of shelf prices and
the document that decided each of them are visible in one place.
