odoo.define('de_pos_fbr_connector.screens', function(require) {
    "use strict";
   
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var PopupWidget = require('point_of_sale.popups');
    var rpc = require('web.rpc');
    var ActionManager = require('web.ActionManager');
    var Session = require('web.session');
    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var DB = require('point_of_sale.DB');
    
    
    models.load_fields("pos.order", ['invoice_number','post_data_fbr','fbr_json']);
    
    
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
    	initialize: function(attributes, options) {
            _super_order.initialize.apply(this, arguments);
            this.invoice_number = false
            this.post_data_fbr = false
            this.fbr_json = false
        },
        set_invoice_number: function(invoice_number) {
        	this.invoice_number = invoice_number || null;
        },
        get_invoice_number: function() {
            return this.invoice_number
        },
        set_fbr_json: function(post_data_fbr) {
        	this.fbr_json = post_data_fbr || null;
        },
        get_fbr_json: function() {
            return this.fbr_json
        },
        
        set_post_data_fbr: function(post_data_fbr) {
        	this.post_data_fbr = post_data_fbr || null;
        },
        get_post_data_fbr: function() {
            return this.post_data_fbr
        },
        export_as_JSON: function() {
        	
            var vals = _super_order.export_as_JSON.apply(this, arguments);
            vals['invoice_number'] = this.get_invoice_number();
            vals['post_data_fbr'] = this.get_post_data_fbr();
            vals['fbr_json'] = this.get_fbr_json();
            return vals
        },
    });
    screens.PaymentScreenWidget.include({
    	validate_order: function(force_validation) {
    		var self = this;
                var pos_order = this.pos.get_order();
                if (this.pos.config.enable_fbr){
                	rpc.query({
                        model: 'pos.order',
                        method: 'post_fbr_order',
                        args: [[pos_order.uid],[pos_order.export_as_JSON()]],
                    })
                    .then(function(data){
                    	if(data && data[0]){
                    		pos_order.set_invoice_number(data[0]);
                        	pos_order.set_post_data_fbr(true)
                    	}
                    	self.finalize_validation();
                    });
                }else{

                	self.finalize_validation();
                }

        },
    });
    
    screens.ReceiptScreenWidget.include({
            get_receipt_render_env: function() {
                var order = this.pos.get_order();
                return {
                    widget: this,
                    pos: this.pos,
                    order: order,
                    invoicenumber :order.get_invoice_number(),
                    receipt: order.export_for_printing(),
                    orderlines: order.get_orderlines(),
                    paymentlines: order.get_paymentlines(),
                };
            },
    });
 
    
    
});
