odoo.define('pos_orders_all.DeliveryDatePopup', function(require) {
	'use strict';

	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
	const Registries = require('point_of_sale.Registries');
	const { useListener } = require('web.custom_hooks');
	const rpc = require('web.rpc');
	let core = require('web.core');
	let _t = core._t;
	class DeliveryDatePopupWidget extends AbstractAwaitablePopup {

		constructor() {
			super(...arguments);
		}
		 create_date() {
			var self = this;
			let rpc_result = false;
			rpc_result = rpc.query({
				model: 'sale.order',
				method: 'create_customer_payment',
				args: [],
			}).then(function(output) {
				alert('date has been Registered for this Customer !!!!');
				self.trigger('close-popup');
			});
		}
	}

	DeliveryDatePopupWidget.template = 'DeliveryDatePopupWidget';
	DeliveryDatePopupWidget.defaultProps = {
		confirmText: 'Create Transfer',
		cancelText: 'Close',
		title: 'Delivery date sale order',
		body: '',
	};

	Registries.Component.add(DeliveryDatePopupWidget);

	return DeliveryDatePopupWidget;
});

