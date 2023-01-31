odoo.define('payment_ebizcharge.download_invoice_credit_notes', function (require) {
    "use strict";
    var core = require('web.core');
    var WidgetViewer = require('payment_ebizcharge.checkbox_many2many_field');
    var relational_fields = require('web.relational_fields');
    var KanbanRenderer = require('web.KanbanRenderer');
    var fieldRegistry = require('web.field_registry');
    var utils = require('web.utils');
    var QWeb = core.qweb;

    var CustomRendererTwo = WidgetViewer['CustomRenderer'].extend({
        events: _.extend({},{
        'click .button-applied': '_onCustomExportButtonClickedApplied',
        }, WidgetViewer['CustomRenderer'].prototype.events),
        _renderView: function () {
            return this._super.apply(this, arguments).then(() => {
                if(this.state.model === 'ebiz.payment.lines'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-applied">Import Into Odoo</button></div>'
                }
                else if(this.state.model === 'sync.logs'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-applied">Clear Logs</button>'
                }
                var $cell = $(buttonName);
                this.$el.prepend($cell)
            });
        },

        _onCustomExportButtonClickedApplied: function (ev) {
            var self = this;
            var res_ids = [];
            var hash = window.location.hash.substring(1);
            var params = $.deparam(hash);
            utils.traverse_records(this.state, function (record) {
                if (_.contains(self.selection, record.id)) {
                    res_ids.push(record['data']);
                }
            });
            if(this.state.model === 'ebiz.payment.lines'){
                this._rpc({
                model: 'ebiz.download.payments',
                method: 'js_mark_as_applied',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }
            else if(this.state.model === 'sync.logs'){
                this._rpc({
                model: 'ebiz.download.payments',
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

    fieldRegistry.add('download_invoice_credit_notes', FieldVideoPreview);
    return FieldVideoPreview;
});