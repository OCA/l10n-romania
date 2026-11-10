## 19.0.0.5.0 (2026-11-07)

- A Romanian company's incoming transfer now prints as a goods receipt note (NIR) inside the shared delivery slip: a single clean title, the company/supplier/number/date/source-document header, and a reception table with the columns Position, Code, Description, UoM, Quantity, Unit Price, Purchase Value, Packages, Additional Charges, Subtotal, VAT and Total, a TOTAL NIR row, the net weight and the excise value where the data exists. The delivery-style order/date/operator block and the duplicate reception title are suppressed for it, while the committee and signature blocks are kept. A NIR number is assigned from a dedicated sequence on validation. The deliveries, internal transfers and consume vouchers keep their previous layout.

## 19.0.0.4.0 (2026-11-07)

- The delivery slip of a Romanian company is now printed in Romanian whatever the partner's language is, so a receipt from a foreign vendor, or a partnerless internal transfer or consume voucher, no longer comes out in English. Other reports and non-RO companies keep the partner's language.
- The plain valued money columns now yield to a more specific layout (the retail reception note), so the two no longer print side by side. A `_l10n_ro_show_valued_columns` hook on the picking decides.
- The Romanian translation file was corrupted (diacritics replaced with `??`, so the slip printed `Pre??` instead of `Preț`); it has been restored.

## 19.0.0.3.1 (2026-11-07)

- A packed line no longer breaks the valued delivery slip (the lines outside packages are aggregated, as the slip asks), and the unit price of a product split over several lines is the price of the whole, not the sum of the lines.

