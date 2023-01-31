odoo.define('payment_ebizcharge.field_masking', function (require) {
"use strict";

var fieldRegistry = require('web.field_registry');
var basic_fields = require('web.basic_fields');

var AbstractField = {
//    template: "FieldMasking",

    _renderEdit: function () {
        var def = this._super.apply(this, arguments);
        if(this.value){
            var splittedValue = this.value.match(/.{1,8}/g);
            // var startValue = splittedValue.at(0);
            var startValue = splittedValue[0];
            // var endValue = splittedValue.at(-1);
            var endValue = splittedValue[splittedValue.length - 1];
            var finalValue = startValue.concat("***************", endValue);
            this.$input.val(finalValue);
        }
        return def;
    }

};
var FieldVideoPreview = basic_fields.FieldChar.extend(AbstractField);
fieldRegistry.add('field_masking', FieldVideoPreview);
return FieldVideoPreview;
});