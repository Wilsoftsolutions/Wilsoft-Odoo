odoo.define('payment_ebizcharge.checkbox_many2many_field', function (require) {
    "use strict";
    var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');
    var relational_fields = require('web.relational_fields');
    var KanbanRenderer = require('web.KanbanRenderer');
    var fieldRegistry = require('web.field_registry');
    var dom = require('web.dom');
    var utils = require('web.utils');

    var QWeb = core.qweb;

    var CustomRenderer = ListRenderer.extend({
        events: _.extend({}, ListRenderer.prototype.events, {
            'click .button-abc': '_onCustomButtonClicked',
            'click .button-remove': '_onCustomRemoveButtonClicked',
        }),
        init: function (parent, state, params) {
            params.hasSelectors = true;
            params.addCreateLine = false;
            params.addTrashIcon = false;
            this._super.apply(this, arguments);
        },
        /**
         * @override
         * @private
         */
        _renderSelector: function (tag, disableInput) {
            var $content = dom.renderCheckbox();
            return $('<' + tag + '>')
                .addClass('o_list_record_selector')
                .append($content);
        },

        /**
         * @override
         * @private
         * @returns {Promise} this promise is resolved immediately
         */
        _renderView: function () {
            return this._super.apply(this, arguments).then(() => {
                if(this.state.model === 'list.ebiz.customers'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Send Request</button></div>'
                }
                else if(this.state.model === 'list.pending.payments.methods'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-abc">Resend Request</button><button type="button" class="ml-2 btn btn-primary button-remove">Remove From List</button></div>'
                }
                else if(this.state.model === 'list.received.payments.methods'){
                    var buttonName = '<div class="float-right my-3"><button type="button" class="btn btn-primary button-remove">Remove From List</button></div>'
                }
                var $cell = $(buttonName);
                this.$el.prepend($cell)
            });
        },

        /**
         * When the user clicks on the row selection checkbox in the header, we
         * need to update the checkbox of the row selection checkboxes in the body.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onToggleSelection: function (ev) {
            var checked = $(ev.currentTarget).prop('checked') || false;
            this.$('tbody .o_list_record_selector input:not(":disabled")').prop('checked', checked);
            this._updateSelection();
        },

        /**
         * Whenever we change the state of the selected rows, we need to call this
         * method to keep the this.selection variable in sync, and also to recompute
         * the aggregates.
         *
         * @private
         */
        _updateSelection: function () {
            const previousSelection = JSON.stringify(this.selection);
            this.selection = [];
            var self = this;
            var $inputs = this.$('tbody .o_list_record_selector input:visible:not(:disabled)');
            var allChecked = $inputs.length > 0;
            $inputs.each(function (index, input) {
                if (input.checked) {
                    self.selection.push($(input).closest('tr').data('id'));
                } else {
                    allChecked = false;
                }
            });
            this.$('thead .o_list_record_selector input').prop('checked', allChecked);
            if (JSON.stringify(this.selection) !== previousSelection) {
                this.trigger_up('selection_changed', {allChecked, selection: this.selection});
            }
            this._updateFooter();
        },
        /**
         * When the user clicks on the whole record selector cell, we want to toggle
         * the checkbox, to make record selection smooth.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onToggleCheckbox: function (ev) {
             console.log('in _onToggleCheckbox')
            const $recordSelector = $(ev.target).find('input[type=checkbox]:not(":disabled")');
            $recordSelector.prop('checked', !$recordSelector.prop("checked"));
            $recordSelector.change(); // s.t. th and td checkbox cases are handled by their own handler
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
            if(this.state.model === 'list.ebiz.customers'){
                this._rpc({
                model: 'payment.method.ui',
                method: 'send_request_payment',
                args: [parseInt(params['id'])],
                kwargs: {"values":res_ids},
                }).then(function (action) {
                self.do_action(action, {
                on_close: function () {
                    self.trigger_up('reload');
                }});
                });
            }
            else if(this.state.model === 'list.pending.payments.methods'){
                this._rpc({
                model: 'payment.method.ui',
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

            if(this.state.model === 'list.pending.payments.methods'){
                this._rpc({
                model: 'payment.method.ui',
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
            else if(this.state.model === 'list.received.payments.methods'){
                this._rpc({
                model: 'payment.method.ui',
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

    var FieldVideoPreview = relational_fields.FieldMany2Many.extend({

        _getRenderer: function () {
            if (this.view.arch.tag === 'tree') {
                return CustomRenderer;
            }
            if (this.view.arch.tag === 'kanban') {
                return KanbanRenderer;
            }
        },

    });

    fieldRegistry.add('checkbox_many2many', FieldVideoPreview);
    return {
        'FieldVideoPreview':FieldVideoPreview,
        'CustomRenderer':CustomRenderer
    };
});