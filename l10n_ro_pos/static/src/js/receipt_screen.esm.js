import {PartnerList} from "@point_of_sale/app/screens/partner_list/partner_list";
import {ReceiptScreen} from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import {_t} from "@web/core/l10n/translation";
import {makeAwaitable} from "@point_of_sale/app/utils/make_awaitable_dialog";
import {patch} from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    /**
     * A fiscal receipt settles the sale on its own, so the POS does not
     * invoice by default. The customer who needs an invoice asks for one at
     * the counter, usually after paying -- which is the only moment this
     * button has to cover. The customer is often picked only then, so the
     * button does not wait for one: it asks.
     */
    get canGenerateInvoice() {
        const order = this.currentOrder;
        return Boolean(
            order &&
                !order.is_invoiced &&
                !order.raw.account_move &&
                order.isSynced &&
                !order.isRefund
        );
    },

    async generateInvoice() {
        const order = this.currentOrder;
        if (!order || !order.isSynced) {
            return;
        }

        try {
            // The order is paid and synced: the customer is written on the
            // server, where the invoice is made, and only then on the till.
            let partner = order.getPartner();
            if (!partner) {
                partner = await makeAwaitable(this.dialog, PartnerList);
                if (!partner) {
                    return;
                }
                await this.pos.data.ormWrite("pos.order", [order.id], {
                    partner_id: partner.id,
                });
            }
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
