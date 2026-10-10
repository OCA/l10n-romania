import {ReceiptScreen} from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    /**
     * A fiscal receipt settles the sale on its own, so the POS does not
     * invoice by default. The customer who needs an invoice asks for one at
     * the counter, usually after paying -- which is the only moment this
     * button has to cover.
     */
    get canGenerateInvoice() {
        const order = this.currentOrder;
        return Boolean(
            order && order.getPartner() && !order.is_invoiced && order.isSynced
        );
    },

    async generateInvoice() {
        const order = this.currentOrder;
        if (!order || !order.isSynced) {
            return;
        }

        try {
            await this.pos.data.call("pos.order", "action_pos_order_invoice", [
                [order.id],
            ]);
            // Re-read the order: the invoice is what we are about to hand over.
            await this.pos.data.read("pos.order", [order.id]);
            if (order.raw.account_move) {
                await this.pos.env.services.account_move.downloadPdf(
                    order.raw.account_move
                );
            }
            this.notification.add(_t("Invoice generated successfully."), {
                type: "success",
            });
        } catch (error) {
            this.notification.add(
                error.data?.message || error.message || _t("Error generating invoice"),
                {type: "danger"}
            );
        }
    },
});
