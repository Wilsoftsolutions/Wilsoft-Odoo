odoo.define("sh_pos_fbr_connector.PaymentScreen", function (require) {
    "use strict";

    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require("point_of_sale.Registries");
    const { useBarcodeReader } = require("point_of_sale.custom_hooks");
    const { useListener } = require("web.custom_hooks");
    const ReceiptScreen = require("point_of_sale.ReceiptScreen");
    const PosComponent = require("point_of_sale.PosComponent");
    var rpc = require("web.rpc");

    const FBRReceiptScreen = (ReceiptScreen) =>
        class extends ReceiptScreen {
            constructor() {
                super(...arguments);
                var order = this.env.pos.get_order();
                var self = this;
                if (self.env.pos.config.sh_enable_fbr_connector_feature) {
                    setTimeout(function () {
                        rpc.query({
                            model: "pos.order",
                            method: "search_read",
                            domain: [["pos_reference", "=", order["name"]]],
                            fields: ["name", "account_move"],
                        }).then(function (callback) {
                            if (callback && callback.length > 0) {
                                if (callback[0]["account_move"]) {
                                    self.env.pos.get_order()["invoice_number"] = callback[0]["account_move"][1].split(" ")[0];
                                } else if (callback[0]["name"]) {
                                    self.env.pos.get_order()["fbr_invoice_number"] = callback[0]["name"];
                                }
                                self.render();
                            }
                        });
                    }, 2000);
                }
            }
        };

    Registries.Component.extend(ReceiptScreen, FBRReceiptScreen);

    class FbrOrderReceipt extends PosComponent {
        constructor() {
            super(...arguments);
            this._receiptEnv = this.props.order.getOrderReceiptEnv();
        }
        get receipt() {
            return this._receiptEnv.receipt;
        }
    }
    FbrOrderReceipt.template = "FbrOrderReceipt";
    Registries.Component.add(FbrOrderReceipt);

    const FBRPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
            }
            async validateOrder(isForceValidate) {
                var self = this;
                $(".next").prop("disabled", true);
                $(".next").css("pointer-events", "None");
                $(".next").css("cursor", "None");

                var pos_order = this.env.pos.get_order();
                if (await this._isOrderValid(isForceValidate)) {
                    for (let line of this.paymentLines) {
                        if (!line.is_done()) this.currentOrder.remove_paymentline(line);
                    }
                    if (self.env.pos.config.sh_enable_fbr_connector_feature) {

                        this.rpc({
                            model: "pos.order",
                            method: "post_data_fbi",
                            args: [[pos_order.uid], [pos_order.export_as_JSON()]],
                        }).then(function (data) {
                            if (data && data[0] && data[0] == 1 && data[1]) {
                                pos_order.set_invoice_number(data[1]);
                                pos_order.set_post_data_fbr(true)
                                pos_order.set_fbr_request(data[2])
                                pos_order.set_fbr_respone(data[3])
                            } else if (data && data[0] && data[0] == 2) {
                                pos_order.set_fbr_request(data[1])
                                pos_order.set_fbr_respone(data[2])

                            }
                            self._finalizeValidation();
                        });
                    } else {
                        super.validateOrder(isForceValidate);
                    }
                } else {
                    $(".next").prop("disabled", false);
                    $(".next").css("pointer-events", "revert");
                    $(".next").css("cursor", "revert");
                }
            }
        };

    Registries.Component.extend(PaymentScreen, FBRPaymentScreen);

    return { PaymentScreen, FbrOrderReceipt };
});
odoo.define("sh_pos_fbr_connector.screens", function (require) {
    "use strict";

    var models = require("point_of_sale.models");
    var DB = require("point_of_sale.DB");

    models.load_fields("pos.order", ['invoice_number', 'post_data_fbr', 'fbr_request', 'fbr_respone']);
    models.load_fields("res.company", ['strn_or_ntn']);
    models.load_fields("res.partner", ['cnic', 'ntn']);
    models.load_fields("pos.order.line", ['tax_ids_after_fiscal_position']);
    models.load_fields("pos.payment.method", ['payment_mode']);

    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        export_for_printing: function () {
            var vals = _super_orderline.export_for_printing.apply(this);
            vals['taxes'] = this.get_taxes();
            return vals;
        },
    });


    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            _super_order.initialize.apply(this, arguments);
            this.invoice_number = false;
            this.post_data_fbr = false;
            this.fbr_respone = false;
            this.fbr_request = false;
        },
        set_invoice_number: function (invoice_number) {
            this.invoice_number = invoice_number || null;
        },
        get_invoice_number: function () {
            return this.invoice_number;
        },
        set_post_data_fbr: function (post_data_fbr) {
            this.post_data_fbr = post_data_fbr || null;
        },
        get_post_data_fbr: function () {
            return this.post_data_fbr;
        },
        get_receipt_logo: function (config) {
            return window.location.origin + "/web/image?model=pos.config&field=sh_receipt_logo&id=" + config;
        },
        set_fbr_respone: function (fbr_respone) {
            this.fbr_respone = fbr_respone || null;
        },
        get_fbr_respone: function () {
            return this.fbr_respone
        },
        set_fbr_request: function (fbr_request) {
            this.fbr_request = fbr_request || null;
        },
        get_fbr_request: function () {
            return this.fbr_request
        },


        export_as_JSON: function () {
            var vals = _super_order.export_as_JSON.apply(this, arguments);
            vals["invoice_number"] = this.get_invoice_number();
            vals["post_data_fbr"] = this.get_post_data_fbr();
            vals['fbr_request'] = this.get_fbr_request();
            vals['fbr_respone'] = this.get_fbr_respone();
            vals['total_discount'] = this.get_total_discount();
            if (this.pos.config.sh_enable_fbr_connector_feature && this.pos.config.sh_enable_include_service) {
                vals['sh_include_service_fee'] = true
                vals['sh_service_fee'] = this.pos.config.sh_service_fee;
            } else {
                vals['sh_include_service_fee'] = false
            }

            return vals;
        },
        export_for_printing: function () {
            var vals = _super_order.export_for_printing.apply(this, arguments);
            var order = this.pos.get_order();
            vals["invoicenumber"] = order.get_invoice_number();

            var sr_no = 1;
            if (vals["orderlines"] && vals["orderlines"].length > 0) {
                _.each(vals["orderlines"], function (each_orderline) {
                    each_orderline["sr_no"] = sr_no;
                    sr_no = sr_no + 1;
                });
            }
            vals['total_change'] = order.get_change()
            return vals;
        },
        getOrderReceiptEnv: function () {
            var res = _super_order.getOrderReceiptEnv.apply(this, arguments);
            res["invoicenumber"] = this.get_invoice_number();
            return res;
        },
    });


});
