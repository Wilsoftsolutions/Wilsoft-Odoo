odoo.define('pos_orders_all.DeliveryDatePopup', function(require) {
	'use strict';

	const { useExternalListener } = owl.hooks;
	const PosComponent = require('point_of_sale.PosComponent');
	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
	const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { useState } = owl.hooks;

	class DeliveryDatePopup extends AbstractAwaitablePopup {
		constructor() {
			super(...arguments);			
		}

		do_update_delivery_date(){

			selectedOrder.set_client(client);
			self.props.resolve({ confirmed: true, payload: null });
			self.trigger('close-popup');
			self.trigger('close-temp-screen');
			
		}
	}
	
	DeliveryDatePopup.template = 'DeliveryDatePopup';
	Registries.Component.add(DeliveryDatePopup);
	return DeliveryDatePopup;
});
