odoo.define("sh_pos_receipt_extend.pos", function (require) {
    "use strict";

    var models = require("point_of_sale.models");
    var core = require("web.core");
    var rpc = require("web.rpc");
    var Session = require("web.session");
    const Chrome = require("point_of_sale.Chrome");
    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const OrderManagementScreen = require("point_of_sale.OrderManagementScreen");

    var qweb = core.qweb;
    var _t = core._t;

    const Registries = require("point_of_sale.Registries");
    const OrderReceipt = require("point_of_sale.OrderReceipt");
    const ReceiptScreen = require("point_of_sale.ReceiptScreen");
    const AbstractReceiptScreen = require("point_of_sale.AbstractReceiptScreen");

    const ShAbstractReceiptScreen = (AbstractReceiptScreen) =>
        class extends AbstractReceiptScreen {
            constructor() {
                super(...arguments);
            }
            async _printWeb() {
                try {
                    setTimeout(() => {
                        window.print();
                    }, 1000);
                    return true;
                } catch (err) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Printing is not supported on some browsers'),
                        body: this.env._t(
                            'Printing is not supported on some browsers due to no default printing protocol ' +
                            'is available. It is possible to print your tickets by making use of an IoT Box.'
                        ),
                    });
                    return false;
                }
            }
        }

    Registries.Component.extend(AbstractReceiptScreen, ShAbstractReceiptScreen);


    const PosOrderManagementScreen = (OrderManagementScreen) =>
        class extends OrderManagementScreen {
            _onClickOrder({ detail: clickedOrder }) {
                super._onClickOrder({ detail: clickedOrder });
                if (!clickedOrder || clickedOrder.locked) {
                    var order = clickedOrder
                    var self = this;
                    this.orderManagementContext.selectedOrder.name = clickedOrder.name
                    if (order.name && (self.env.pos.config.sh_pos_order_number || self.env.pos.config.sh_pos_receipt_invoice)) {
                        rpc.query({
                            model: 'pos.order',
                            method: 'search_read',
                            domain: [['pos_reference', '=', order.name]],
                            fields: ['name', 'account_move']
                        }).then(function (callback) {
                            if (callback && callback.length > 0) {
                                if (callback[0] && callback[0]['name'] && self.env.pos.config.sh_pos_order_number) {
                                    order['pos_recept_name'] = callback[0]['name']
                                }
                                if (callback[0] && callback[0]['account_move'] && self.env.pos.config.sh_pos_receipt_invoice) {
                                    var invoice_number = callback[0]["account_move"][1].split(" ")[0];
                                    order["invoice_number"] = invoice_number;
                                }
                            }
                        })
                    }
                } else {
                    this._setOrder(clickedOrder);
                }
            }
        };
    Registries.Component.extend(OrderManagementScreen, PosOrderManagementScreen);

    const PosReturnPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            async _finalizeValidation() {
                var self = this;
                var order = self.env.pos.get_order();
                if (order.name && self.env.pos.config.sh_pos_order_number) {
                    rpc.query({
                        model: 'pos.order',
                        method: 'search_read',
                        domain: [['pos_reference', '=', order.name]],
                        fields: ['name']
                    }).then(function (callback) {
                        if (callback && callback.length > 0) {
                            order['pos_recept_name'] = callback[0]['name']
                        }
                    })
                }
                super._finalizeValidation()
            }
        };

    Registries.Component.extend(PaymentScreen, PosReturnPaymentScreen);

    const PosResOrderReceipt = (OrderReceipt) =>
        class extends OrderReceipt {
            constructor() {
                super(...arguments);
                var self = this;
                var order = self.env.pos.get_order();
                var order_barcode = order.name.split(" ")
                if (order_barcode &&  [1]) {
                    order_barcode = order_barcode[1].split("-");
                    order.barcode = "";
                    _.each(order_barcode, function (splited_barcode) {
                        order.barcode = order.barcode + splited_barcode;
                    });
                }

                var image_path = $("img.barcode_class").attr("src");
                $.ajax({
                    url: image_path,
                    type: "HEAD",
                    error: function () {
                        self.env.pos.get_order()["is_barcode_exit"] = false;
                    },
                    success: function () {
                        self.env.pos.get_order()["is_barcode_exit"] = true;
                    },
                });
                var image_path = $("img.qr_class").attr("src");
                $.ajax({
                    url: image_path,
                    type: "HEAD",
                    error: function () {
                        self.env.pos.get_order()["is_qr_exit"] = false;
                    },
                    success: function () {
                        self.env.pos.get_order()["is_qr_exit"] = true;
                    },
                });
                if (order.is_to_invoice() && self.env.pos.config.sh_pos_receipt_invoice) {
                    rpc.query({
                        model: "pos.order",
                        method: "search_read",
                        domain: [["pos_reference", "=", order["name"]]],
                        fields: ["account_move"],
                    }).then(function (orders) {
                        if (orders.length > 0 && orders[0]["account_move"] && orders[0]["account_move"][1]) {
                            var invoice_number = orders[0]["account_move"][1].split(" ")[0];
                            order["invoice_number"] = invoice_number;
                        }
                        self.render();
                    });
                }
                rpc.query({
                    model: 'pos.order',
                    method: 'search_read',
                    domain: [['pos_reference', '=', order.name]],
                    fields: ['name','invoice_number']
                }).then(function (callback) {
                    if (callback && callback.length > 0) {
                        order['pos_recept_name'] = callback[0]['name'];
                        order['fbr_invoice_number'] = callback[0]['invoice_number']

                        //barcode and qrcode starts here
                        if ($("#barcode") && $("#barcode").length > 0) {
	                    JsBarcode("#barcode")
	                        .options({ font: "OCR-B", displayValue: false }) // Will affect all barcodes
	                        .CODE128(order['fbr_invoice_number'], { fontSize: 18, textMargin: 0, height: 50 })
	                        .blank(0) // Create space between the barcodes
	                        .render();
		                }
		                if ($('#qr_code') && $('#qr_code').length > 0) {
		                    // $('#qr_code').qrcode({ text: self.env.pos.get_order().barcode, width: 50, height: 50 });
		                    var div = document.createElement('div')
		                    $(div).qrcode({ text: order['fbr_invoice_number'], width: 50, height: 50 });
		                    // new QRCode(div, { text: self.env.pos.get_order().barcode });

		                    var can = $(div).find('canvas')[0]
		                    var img = new Image();
		                    img.src = can.toDataURL();

		                    $(img).css({ 'height': '50px', 'width': '50px' })

		                    $('#qr_code').append(img)
		                }
                        //barcode and qrcode ends here

                    }
                    self.render();
                })
            }
            /*mounted() {
                super.mounted()

                var self = this;
                if ($("#barcode") && $("#barcode").length > 0) {
                    JsBarcode("#barcode")
                        .options({ font: "OCR-B", displayValue: false }) // Will affect all barcodes
                        .CODE128(self.env.pos.get_order().barcode, { fontSize: 18, textMargin: 0, height: 50 })
                        .blank(0) // Create space between the barcodes
                        .render();
                }
                if ($('#qr_code') && $('#qr_code').length > 0) {
                    // $('#qr_code').qrcode({ text: self.env.pos.get_order().barcode, width: 50, height: 50 });
                    var div = document.createElement('div')
                    $(div).qrcode({ text: self.env.pos.get_order().barcode, width: 50, height: 50 });
                    // new QRCode(div, { text: self.env.pos.get_order().barcode });

                    var can = $(div).find('canvas')[0]
                    var img = new Image();
                    img.src = can.toDataURL();

                    $(img).css({ 'height': '50px', 'width': '50px' })

                    $('#qr_code').append(img)
                }
                //            	jquery('#qrcode').qrcode("this plugin is great");
            }*/
        };
    Registries.Component.extend(OrderReceipt, PosResOrderReceipt);
});
