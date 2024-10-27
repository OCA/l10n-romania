odoo.define("l10n_ro_pos.PaymentScreenStatus", function (require) {
    "use strict";

    const PaymentScreenStatus = require("point_of_sale.PaymentScreenStatus");

    const Registries = require("point_of_sale.Registries");

    const RomPaymentScreenStatus = (PaymentScreenStatus) =>
        class extends PaymentScreenStatus {
            get warningMessage() {
                var message = false;
                var value = 0;
                var order = this.currentOrder;
                var paymentlines = order.get_paymentlines();

                for (var i = 0; i < paymentlines.length; i++) {
                    var line = paymentlines[i];
                    if (line.payment_method.is_cash_count) {
                        value += line.amount;
                    }
                }
                if (value >= 5000) {
                    message = "L5000";
                }
                if (value >= 10000) {
                    message = "L10000";
                }
                return message;
            }
        };

    Registries.Component.extend(PaymentScreenStatus, RomPaymentScreenStatus);
});
