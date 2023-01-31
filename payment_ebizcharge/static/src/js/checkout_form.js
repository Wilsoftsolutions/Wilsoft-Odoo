odoo.define('payment_ebizcharge.checkout_form', function (require) {
"use strict";
var checkoutForm = require('payment.checkout_form');

checkoutForm.include({
    events: _.extend({},{
        'click .o_payment_acquirer_select': '_onClickPaymentOption',
    }, checkoutForm.prototype.events),

    /**
     * @private
     */
    _showHideSecurityInput: function (checkedRadio) {
        var pm_id = parseInt(checkedRadio.value.split('-')[0]);
        var token_type = checkedRadio.value.split('-')[1];
        if(token_type === 'ebizchargeCard'){
            document.getElementById(pm_id).style.display = 'block';
            document.getElementById('security-code-heading').style.display = 'block';
            document.getElementsByName("o_payment_radio").forEach(function (element) {
                if (!element.checked){
                    if(element.value.includes('ebizchargeCard')){
                        document.getElementById(parseInt(element.value.split('-')[0])).style.display = 'none';
                    }
                }
            });
        }
        else{
            if(document.getElementById('security-code-heading')){
                document.getElementById('security-code-heading').style.display = 'none';
                document.getElementsByName("o_payment_radio").forEach(function (element) {
                    if (!element.checked){
                        if(element.value.includes('ebizchargeCard')){
                            document.getElementById(parseInt(element.value.split('-')[0])).style.display = 'none';
                        }
                    }
                })
            }
        }
    },

    _onClickPaymentOption: function (ev) {
        // Uncheck all radio buttons
        this.$('input[name="o_payment_radio"]').prop('checked', false);
        // Check radio button linked to selected payment option
        const checkedRadio = $(ev.currentTarget).find('input[name="o_payment_radio"]')[0];
        $(checkedRadio).prop('checked', true);

        if ($(checkedRadio).data('provider') === 'ebizcharge'){
            this._showHideSecurityInput(checkedRadio)
        }
        // Show the inputs in case they had been hidden
        this._showInputs();

        // Disable the submit button while building the content
        this._disableButton(false);

        // Unfold and prepare the inline form of selected payment option
        this._displayInlineForm(checkedRadio);

        // Re-enable the submit button
        this._enableButton();
    },

});
});