import {TicketScreen} from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    /**
     * Core's hook for localisations to complete a refund order.
     *
     * A receipt sold without a customer produces a refund without one either,
     * and the Validate button would then just sit there disabled -- core
     * blocks it on `isCustomerRequired` before its own "select the customer"
     * message can be reached. Ask for the customer here instead, while the
     * cashier still has the refund in front of them.
     */
    async addAdditionalRefundInfo(order, destinationOrder) {
        await super.addAdditionalRefundInfo(...arguments);
        if (!destinationOrder.l10nRoNeedsCustomer) {
            return;
        }
        this.env.services.notification.add(
            _t(
                "A refund is issued as a credit note and a payment disposal, both in the customer's name. Please select the customer."
            ),
            {type: "info"}
        );
        await this.pos.selectPartner(destinationOrder);
    },
});
