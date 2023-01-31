odoo.define('payment_ebizcharge.batch_processing', function (require) {
    "use strict";
    var core = require('web.core');
    var WidgetViewer = require('payment_ebizcharge.checkbox_many2many_field');
    var relational_fields = require('web.relational_fields');
    var KanbanRenderer = require('web.KanbanRenderer');
    var fieldRegistry = require('web.field_registry');
    var utils = require('web.utils');
    var QWeb = core.qweb;

    var CustomRendererTwo = WidgetViewer['CustomRenderer'].extend({
        events: _.extend({}, WidgetViewer['CustomRenderer'].prototype.events, {
            'click .paymentMethods': '_PaymentMethods',
        }),

        _PaymentMethods: function(ev){
            var self = this;
            var hash = window.location.hash.substring(1);
            var params = $.deparam(hash);
            this._rpc({
                model: 'sync.batch.processing',
                method: 'viewPaymentMethods',
                args: [parseInt(params['id'])],
                kwargs: {"values":parseInt(ev.target.id)},
            }).then(function (action) {
                self.do_action(action).then(function (){
                    $("a:contains(Credit Cards)").click()
                });
            });

        },

        confirmUpdate: function (state, id, fields, ev) {
            return this._super.apply(this, arguments).then(() => {
                if(this.state.model === 'sync.batch.processing'){
                    console.log("render");
                    document.getElementById('paymentMethods').remove();
                    this.$el.find('td span.after_it').parent().after('<td id="paymentMethods"><span class="btn btn-link paymentMethods">View Payment Methods</span></td>');
                }
            });
        },

        _getNumberOfCols: function () {
            var n = this.columns.length;
            if(this.state.model === 'sync.batch.processing'){
                return n + 2;
            }
       },

        _renderView: function () {
            return this._super.apply(this, arguments).then(() => {
                if(this.state.model === 'sync.batch.processing'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Process Invoices</button>'
                    this.$el.find('th:last-child').before('<th>Payment Methods<span class="o_resize"></span></th>');
                    this.$el.find('tfoot tr td:last-child').before('<td></td>');
                    this.$el.find('td span.after_it').parent().each(function() {
                        var customerId = parseInt($(this).prev('td').prev('td').prev('td').text());
                        var newTD = '<td style="vertical-align:top" id="paymentMethods"><span id="' + customerId + '" class="btn-link paymentMethods">View Payment Methods</span></td>';
                        $(this).after(newTD);
                    });

//                    this.$el.find('td span.after_it').parent().after('<td style="vertical-align:top" id="paymentMethods"><span class="btn-link paymentMethods">View Payment Methods</span></td>');
                }
                else if(this.state.model === 'sync.batch.processed'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Clear Logs</button>'
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
            if(this.state.model === 'sync.batch.processing'){
                this._rpc({
                model: 'batch.processing',
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
            else if(this.state.model === 'sync.batch.processed'){
                this._rpc({
                model: 'batch.processing',
                method: 'clear_logs',
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

    fieldRegistry.add('batch_processing', FieldVideoPreview);
    return FieldVideoPreview;
});