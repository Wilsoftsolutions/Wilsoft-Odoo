odoo.define('payment_ebizcharge.upload_credit_notes', function (require) {
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
        'click .button-export': '_onCustomExportButtonClicked',
        }, WidgetViewer['CustomRenderer'].prototype.events),
        _renderView: function () {
            return this._super.apply(this, arguments).then(() => {
                if(this.state.model === 'list.credit.notes'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Upload</button><button type="button" class="ml-2 btn btn-primary button-export">Export</button></div>'
                }

                else if(this.state.model === 'logs.credit.notes'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Clear Logs</button><button type="button" class="ml-2 btn btn-primary button-export">Export</button></div>'
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
                    res_ids.push(record.res_id);
                }
            });
            if(this.state.model === 'list.credit.notes'){
                this._rpc({
                model: 'upload.credit.notes',
                method: 'upload_invoice',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }

            else if(this.state.model === 'logs.credit.notes'){
                this._rpc({
                model: 'upload.credit.notes',
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

        _onCustomExportButtonClicked: function (ev) {
            var self = this;
            var res_ids = [];
            var hash = window.location.hash.substring(1);
            var params = $.deparam(hash);
            utils.traverse_records(this.state, function (record) {
                if (_.contains(self.selection, record.id)) {
                    res_ids.push(record.res_id);
                }
            });

            if(this.state.model === 'list.credit.notes'){
                this._rpc({
                model: 'upload.credit.notes',
                method: 'export_orders',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }

            else if(this.state.model === 'logs.credit.notes'){
                this._rpc({
                model: 'upload.credit.notes',
                method: 'export_logs',
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

    fieldRegistry.add('upload_credit_notes', FieldVideoPreview);
    return FieldVideoPreview;
});