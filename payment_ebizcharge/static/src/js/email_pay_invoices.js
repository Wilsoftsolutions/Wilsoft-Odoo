odoo.define('payment_ebizcharge.email_pay_invoices', function (require) {
    "use strict";
    var core = require('web.core');
    var WidgetViewer = require('payment_ebizcharge.checkbox_many2many_field');
    var relational_fields = require('web.relational_fields');
    var KanbanRenderer = require('web.KanbanRenderer');
    var fieldRegistry = require('web.field_registry');
    var utils = require('web.utils');
    var QWeb = core.qweb;

    var CustomRendererTwo = WidgetViewer['CustomRenderer'].extend({
        _renderView: function () {
            return this._super.apply(this, arguments).then(() => {
                if(this.state.model === 'sync.request.payments.bulk'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Send Email Pay Request</button></div>'
                }
                else if(this.state.model === 'sync.request.payments.bulk.pending'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Resend</button><button type="button" class="ml-2 btn btn-primary button-remove">Remove From List</button></div>'
                }
                else if(this.state.model === 'sync.request.payments.bulk.received'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Apply</button><button type="button" class="ml-2 btn btn-primary button-remove">Remove From List</button></div>'
                }
                var $cell = $(buttonName);
                this.$el.prepend($cell)
            });
        },

        _onCustomButtonClicked: function (ev) {
            var self = this;
            var res_ids = [];
            var hash = window.location.hash.substring(1);
            var params = $.deparam(hash);
            utils.traverse_records(this.state, function (record) {
                if (_.contains(self.selection, record.id)) {
                    res_ids.push(record['data']);
                }
            });
            if(this.state.model === 'sync.request.payments.bulk'){
                this._rpc({
                model: 'payment.request.bulk.email',
                method: 'process_invoices',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }
            else if(this.state.model === 'sync.request.payments.bulk.pending'){
                this._rpc({
                model: 'payment.request.bulk.email',
                method: 'resend_email',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }
            else if(this.state.model === 'sync.request.payments.bulk.received'){
                this._rpc({
                model: 'payment.request.bulk.email',
                method: 'mark_applied',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }
        },

        _onCustomRemoveButtonClicked: function (ev) {
            var self = this;
            var res_ids = [];
            var hash = window.location.hash.substring(1);
            var params = $.deparam(hash);
            utils.traverse_records(this.state, function (record) {
                if (_.contains(self.selection, record.id)) {
                    res_ids.push(record['data']);
                }
            });
            if(this.state.model === 'sync.request.payments.bulk.pending'){
                this._rpc({
                model: 'payment.request.bulk.email',
                method: 'delete_invoice',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }
            else if(this.state.model === 'sync.request.payments.bulk.received'){
                this._rpc({
                model: 'payment.request.bulk.email',
                method: 'delete_invoice_2',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }
        },
    });

    var FieldVideoPreview = WidgetViewer['FieldVideoPreview'].extend({

        _getRenderer: function () {
            console.log("In Renderer")
            if (this.view.arch.tag === 'tree') {
                return CustomRendererTwo;
            }
            if (this.view.arch.tag === 'kanban') {
                return KanbanRenderer;
            }
        },


    });

    fieldRegistry.add('email_pay_invoices', FieldVideoPreview);
    return FieldVideoPreview;
});