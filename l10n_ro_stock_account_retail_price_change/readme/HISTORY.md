## 19.0.1.4.1

- The retail price history button also works on the product variant form,
  which reuses the template's button box. The method only existed on the
  template, so validating the variant form failed -- installing a module that
  extends it (e.g. Romania - Accounting) stopped with "not a valid action on
  product.product".

