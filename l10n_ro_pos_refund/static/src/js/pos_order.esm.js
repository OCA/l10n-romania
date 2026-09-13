import {PosOrder} from "@point_of_sale/app/models/pos_order";
import {patch} from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    /**
     * A refund of a Romanian company: it always leaves the shop as a credit
     * note, whatever the cashier picked in the UI.
     */
    get l10nRoIsRefund() {
        return Boolean(this.isRefund && this.company?.l10n_ro_accounting);
    },

    /**
     * The credit note and the payment disposal are both issued in the
     * customer's name, so there is no refund to validate without one.
     */
    get l10nRoNeedsCustomer() {
        return this.l10nRoIsRefund && !this.getPartner();
    },

    isToInvoice() {
        if (this.l10nRoIsRefund) {
            return true;
        }
        return super.isToInvoice(...arguments);
    },
});
