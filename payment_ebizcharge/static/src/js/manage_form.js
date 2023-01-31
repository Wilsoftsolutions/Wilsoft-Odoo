odoo.define('payment_ebizcharge.manage_form', function (require) {
"use strict";
var manageForm = require('payment.manage_form');

manageForm.include({
    events: _.extend({},{
        'click button[name="update_pm"]': '_updatePmEvent',
        'click #o_payment_cancel_button': '_cancelButton',
        'click .nav-link': '_showHideDetails',
    }, manageForm.prototype.events),

    /**
     * @private
     */
    getAcquirerIdFromRadio: function (element) {
        return $(element).data('payment-option-id');
    },

    /**
     * @private
     */
    _updatePmEvent: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        $('input[data-provider="ebizcharge"][data-payment-option-type="acquirer"]').click()
        $('.update_pm').prop('disabled', true);
        $('.delete_pm').prop('disabled', true);
        var self = this;
        var pm_id = parseInt(ev.currentTarget.value);
        self.currently_updating = ev.target.parentElement
        self._rpc({
            route: '/payment/ebizcharge/get/token',
            params: { 'pm_id': pm_id},
        }).then(function (result) {
            self.populateUpdateFields(result, pm_id)
        }, function () {
            self.displayError(
                _t('Server Error'),
                _t("We are not able to delete your payment method at the moment.")
            );
        });

    },

    /**
     * @private
     */
    populateUpdateFields: function (result, pm_id) {
        var self = this
        if(result.token_type === 'credit'){
            self.$el.find("input[name='card_number']").attr('readonly',1)
            self.$el.find("input[name='card_number']").val(result.card_number)
            self.$el.find("input[name='account_holder_name']").val(result.account_holder_name)
            self.$el.find("input[name='avs_street']").val(result.avs_street)
            self.$el.find("input[name='avs_zip']").val(result.avs_zip)
            self.$el.find("input[name='card_expiration']").val(`${result.card_exp_month} / ${result.card_exp_year.slice(2,4)}`)
            self.$el.find("input[name='card_code']").val("")
            self.$el.find("input[name='partner_id']").val(result.partner_id[0])
            self.$el.find("input[name='update_pm_id']").val(pm_id)
            self.$el.find("input[name='default_card_method']").prop("checked", result.is_default)
            self.$el.find("input[name='default_card_method']").val(result.is_default)
            self.$el.find("input[name='card_type']").val(result.card_type)
            $("#card-tab").click();
        }
        else{
            self.$el.find("input[name='bank_account_holder_name']").val(result.account_holder_name)
            self.$el.find("select").val(result.account_type)
            self.$el.find("input[name='bank_account_type']").attr('readonly',1)
            self.$el.find("input[name='account_number']").val(result.account_number)
            self.$el.find("input[name='account_number']").attr('readonly',1)
            self.$el.find("input[name='routing_number']").val(result.routing)
            self.$el.find("input[name='routing_number']").attr('readonly',1)
            self.$el.find("input[name='update_pm_id']").val(pm_id)
            self.$el.find("input[name='default_account_method']").prop("checked", result.is_default)
            self.$el.find("input[name='default_account_method']").val(result.is_default)
            self.$el.find("input[name='card_type']").val(result.card_type)
            $("#account-tab").click();
        }
        $('button[name="o_payment_submit_button"]').html('<i class="fa fa-plus-circle"/> Update');
        self.$el.find("#o_payment_cancel_button")[0].style = 'display: inline;'
    },

    /**
     * @private
     */
    _cancelButton: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        $('.update_pm').prop('disabled', false);
        $('.delete_pm').prop('disabled', false);
        var checked_radio = this.$('input[type="radio"]:checked');
        var acquirer_id = this.getAcquirerIdFromRadio(checked_radio);
        var acquirer_form = this.$('#o_payment_acquirer_inline_form_' + acquirer_id);
        var inputs_form = $('input', acquirer_form);
        for (var i=0; i<inputs_form.length; i++) {
            if (inputs_form[i].id){
                if (inputs_form[i].id != 'addCardBank1' && inputs_form[i].id != 'addCardBank2'){
                    inputs_form[i].value = ''
                    inputs_form[i].removeAttribute('readonly')
                }
            }
        }

        var tab = $('.nav-link.active');
        if(tab[0].id === 'card-tab'){
            $('button[name="o_payment_submit_button"]').html('<i class="fa fa-plus-circle"/> Add new card');
            this.$el.find("input[name='default_card_method']").prop("checked", false);
            this.$el.find("input[name='default_card_method']").val(false);
        }
        else{
            $('button[name="o_payment_submit_button"]').html('<i class="fa fa-plus-circle"/> Add new account');
            this.$el.find("input[name='default_account_method']").prop("checked", false);
            this.$el.find("input[name='default_account_method']").val(false);
        }
        this.$el.find("#o_payment_cancel_button")[0].style = 'display: none;'
    },

    /**
     * @private
     */
    _showHideDetails: function(ev){
        var updateOrNot = $('input[name="update_pm_id"]').val()
        if(updateOrNot === ""){
            var $checkedRadio = this.$('input[type="radio"]:checked');
            if(ev.currentTarget.id==='account-tab' && $checkedRadio.data('provider') === 'ebizcharge'){
                $('button[name="o_payment_submit_button"]').html('<i class="fa fa-plus-circle"/> Add new account');
            }
            else{
                $('button[name="o_payment_submit_button"]').html('<i class="fa fa-plus-circle"></i> Add new card');
            }
        }

    },

    /**
     * @override
     */
    _onClickPaymentOption: function (ev) {
        this._super.apply(this, arguments);
        var $checkedRadio = this.$('input[type="radio"]:checked');
        var tab = $('.nav-link.active');
        if($checkedRadio.data('provider') === 'ebizcharge'){
            if(tab[0].id==='account-tab'){
                $('button[name="o_payment_submit_button"]').html('<i class="fa fa-plus-circle"/> Add new account');
            }
            if(tab[0].id==='card-tab'){
                $('button[name="o_payment_submit_button"]').html('<i class="fa fa-plus-circle"></i> Add new card');
            }
        }
    },

});
});