import {PosOrder} from "@point_of_sale/app/models/pos_order";
import {patch} from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    /**
     * Picking a company as the customer does not turn the receipt into an
     * invoice.
     *
     * In Romania the fiscal receipt is what the till issues, and it settles
     * the sale on its own -- the invoice is asked for, not assumed, and
     * issuing one against a receipt already printed is a separate document.
     * Core flips the order to invoiced as soon as the customer is a company,
     * which here would invoice every company walking in with a CUI.
     */
    setPartner(partner) {
        this.assertEditable();
        this.partner_id = partner;
        this.updatePricelistAndFiscalPosition(partner);
    },
});
