## 19.0.1.5.2 (2026-11-07)

- The reception "before lines" comment (its heading and commission introduction) is no longer printed on a goods receipt note (NIR), which carries its own single title, so the slip no longer shows a double title. The committee and signature block below is unchanged.

## 19.0.1.5.1 (2026-11-07)

- The committee and signature blocks print reliably: the report now searches the matching comment templates by domain at render time, instead of the stored ``comment_template_ids`` which recomputed to empty on read and dropped the blocks from the printed voucher.

