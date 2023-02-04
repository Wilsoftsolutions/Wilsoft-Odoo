odoo.define('pos_orders_all.DeliveryDate', function(require) {
	"use strict";

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const { useListener } = require('web.custom_hooks');
	const Registries = require('point_of_sale.Registries');

	class DeliveryDate extends PosComponent {
		constructor() {
			super(...arguments);
			useListener('click', this.onClick);
//			useListener('click-delivery-date', this.do_update_delivery_date);
		}

		async onClick() {
            let self = this;
			let order = self.env.pos.get_order();
            let pos_lines =  order.get_orderlines();


            self.showPopup('DateDeliveryPop', {
                'order': order,
                'orderlines': pos_lines,

            });
//            this.do_update_delivery_date()
        }

	      do_update_deliverdat() {
			var self = this;


			var delivery_date = $('.delivery-date').val();

			this.rpc({
				model: 'pos.order',
				method: 'create_deliver_date',
				args: [1, delivery_date,partner_id],
			})
		}
	}
	DeliveryDate.template = 'DeliveryDate';

	ProductScreen.addControlButton({
		component: DeliveryDate,
		condition: function() {
			return true;
		},
	});

	Registries.Component.add(DeliveryDate);

	return DeliveryDate;
});


//odoo.define('pos_orders_all.DeliveryDate', function(require) {
//	"use strict";
//
//	var models = require('point_of_sale.models');
//	var core = require('web.core');
//	var rpc = require('web.rpc');
//	var _t = core._t;
//
//	models.load_models({
//		model: 'sale.order',
//		fields: ['id','delivery_date'],
//        domain: null,
//        loaded: function(self, delivery_date){
//			self.delivery_date = delivery_date;
//		},
//	});
//
//
//});
