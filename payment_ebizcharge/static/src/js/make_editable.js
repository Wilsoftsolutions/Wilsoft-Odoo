odoo.define('payment_ebizcharge.make_editable', function (require) {
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
            'click .makeEditable': '_makeEditable',
        }),

        confirmUpdate: function (state, id, fields, ev) {
            return this._super.apply(this, arguments).then(() => {
                if(this.state.model === 'email.recipients'){
                    this.$el.find('tfoot tr td:last-child').after('<td></td>');
                    document.getElementById('makeEditable').remove();
                    this.$el.find('td.o_list_record_remove').before('<td id="makeEditable"><button type="button" class="btn o_icon_button makeEditable"><i class="fa fa-fw o_button_icon fa-pencil"></i></button></td>');
                }
                else if(this.state.model === 'ebiz.payment.lines.bulk'){
                    document.getElementById('makeEditable1').remove();
                    document.getElementById('makeEditable2').remove();
                    this.$el.find('tfoot tr td:last-child').after('<td></td>');
                    this.$el.find('tfoot tr td:last-child').after('<td></td>');
                    this.$el.find('td.my_editable_email_id').before('<td id="makeEditable1"><button type="button" class="btn o_icon_button makeEditable"><i class="fa fa-fw o_button_icon fa-pencil"></i></button></td>');
                    this.$el.find('td.my_editable_email_id').after('<td id="makeEditable2"><button type="button" class="btn o_icon_button makeEditable"><i class="fa fa-fw o_button_icon fa-pencil"></i></button></td>');
                }
            });
        },

        _getNumberOfCols: function () {
            var n = this.columns.length;
            if(this.state.model === 'email.recipients'){
                return n + 2;
            }
            else if(this.state.model === 'ebiz.payment.lines.bulk'){
                return n + 2;
            }
       },
       
        _renderView: function () {
            return this._super.apply(this, arguments).then(() => {
                if(this.state.model === 'email.recipients'){
                    this.$el.find('th:last-child').after('<th></th>');
                    this.$el.find('tfoot tr td:last-child').after('<td></td>');
                    this.$el.find('td.o_list_record_remove').before('<td id="makeEditable"><button type="button" class="btn o_icon_button makeEditable"><i class="fa fa-fw o_button_icon fa-pencil"></i></button></td>');
                }
                else if(this.state.model === 'ebiz.payment.lines.bulk'){
                    this.$el.find('th:last-child').before('<th></th>');
                    this.$el.find('th:last-child').after('<th></th>');
                    this.$el.find('tfoot tr td:last-child').after('<td></td>');
                    this.$el.find('tfoot tr td:last-child').after('<td></td>');
                    this.$el.find('td.my_editable_email_id').before('<td id="makeEditable1"><button type="button" class="btn o_icon_button makeEditable"><i class="fa fa-fw o_button_icon fa-pencil"></i></button></td>');
                    this.$el.find('td.my_editable_email_id').after('<td id="makeEditable2"><button type="button" class="btn o_icon_button makeEditable"><i class="fa fa-fw o_button_icon fa-pencil"></i></button></td>');
                }
            });
        },

        _makeEditable: function(ev){
            $(ev.currentTarget).parent('td').prev('.o_data_cell').append('<input class="o_field_char o_field_widget o_input" name="email" placeholder="" type="text">').trigger('click');
        }


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

    fieldRegistry.add('make_editable', FieldVideoPreview);
    return {
        'FieldVideoPreview':FieldVideoPreview,
        'CustomRenderer':CustomRenderer
    };
});