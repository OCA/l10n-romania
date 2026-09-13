import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    /**
     * The customer signs for the cash they are handed back, so the payment
     * disposal has to come out of the printer at the till, right behind the
     * credit note core already downloads.
     */
    async finalizeValidation() {
        const validated = await super.finalizeValidation(...arguments);
        if (validated !== false) {
            await this.l10nRoPrintPaymentDisposal();
        }
        return validated;
    },

    async l10nRoPrintPaymentDisposal() {
        if (
            !this.order.l10nRoIsRefund ||
            !this.order.raw?.l10n_ro_payment_disposal_id
        ) {
            return;
        }
        try {
            const action = await this.pos.data.call(
                "pos.order",
                "l10n_ro_get_payment_disposal_report",
                [this.order.id]
            );
            if (action) {
                await this.pos.action.doAction(action);
            }
        } catch {
            // The refund itself went through; only the printout failed.
            this.pos.env.services.notification.add(
                _t(
                    "The payment disposal could not be printed. Print it from the refund order before the customer leaves."
                ),
                {type: "warning"}
            );
        }
    },
});
