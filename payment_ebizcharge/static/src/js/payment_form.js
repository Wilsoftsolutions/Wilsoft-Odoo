/* global Accept */
odoo.define('payment_ebizcharge.payment_form', require => {
    'use strict';

    const core = require('web.core');
    const ajax = require('web.ajax');
    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');
    const _t = core._t;

    const ebizchargeMixin = {
        /**
         * @private
         */
        _getAcquirerTypeFromCheckbox: function(element) {
            return element[0].id;
        },

        /**
         * @private
         * @param {jQuery} $form
         */
        getFormData: function ($form) {
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function (n, i) {
                indexed_array[n.name] = n.value;
            });
            return indexed_array;
        },

        /**
         * Return all relevant inline form inputs based on the payment method type of the acquirer.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {Object} - An object mapping the name of inline form inputs to their DOM element
         */
        _getInlineFormInputs: function (acquirerId) {
            var tab = $('.nav-link.active');
            var acquirerType = this._getAcquirerTypeFromCheckbox(tab);
            var authorizeOnly = this.$el.find("input[name='authorizeOnly']")[0]
            if(acquirerType === 'account-tab' && authorizeOnly.value === 'True'){
                Dialog.alert(self, _t("Bank account payment method is disabled."), {
                    title: _t('Validation Error'),
                });
            }else{
                if (acquirerType === 'account-tab'){
                    return {
                        accountName: document.getElementById('bank_account_holder_name'),
                        accountNumber: document.getElementById('account_number'),
                        routingNumber: document.getElementById('routing_number'),
                        accountType: document.getElementById('bank_account_type'),
                    };
                }else{
                    return {
                        card: document.getElementById('cc_number'),
                        name: document.getElementById('cc_holder_name'),
                        street: document.getElementById('avs_street'),
                        zip: document.getElementById('avs_zip'),
                        expiry: document.getElementById('cc_expiry'),
                        code: document.getElementById('cc_cvc'),
                    };
                }
            }
        },

        /**
         * Return the credit card or bank data to pass to the Accept.dispatch request.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {Object} - Data to pass to the Accept.dispatch request
         */
        _getPaymentDetails: function (acquirerId) {
            const inputs = this._getInlineFormInputs(acquirerId);
            var tab = $('.nav-link.active');
            var acquirerType = this._getAcquirerTypeFromCheckbox(tab);
            if (acquirerType === 'account-tab'){
                return {
                    acquirer_id: acquirerId,
                    bankData: {
                        nameOnAccount: inputs.accountName.value.substring(0, 22), // Max allowed by acceptjs
                        accountNumber: inputs.accountNumber.value,
                        routingNumber: inputs.routingNumber.value,
                        accountType: inputs.accountType.value,
                    },
                };
            }else{
                return {
                    acquirer_id: acquirerId,
                    cardData: {
                        cardNumber: inputs.card.value.replace(/ /g, ''), // Remove all spaces
                        name: inputs.name.value,
                        street: inputs.street.value,
                        zip: inputs.zip.value,
                        expiry: inputs.expiry.value,
                        cardCode: inputs.code.value,
                    },
                };
            }
        },

        /**
         * Prepare the inline form of Authorize.Net for direct payment.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {Promise}
         */
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
            if (provider !== 'ebizcharge') {
                return this._super(...arguments);
            }
            if (flow === 'token') {
                return Promise.resolve(); // Don't show the form for tokens
            }
            this._setPaymentFlow('direct');
        },

        /**
         * Dispatch the secure data to Authorize.Net.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {string} flow - The online payment flow of the transaction
         * @return {Promise}
         */
        _processPayment: function (provider, paymentOptionId, flow) {
           var self = this;
           var acquirerId = paymentOptionId;
           if (provider !== 'ebizcharge' || flow === 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
           }

           if (!this._validateFormInputs(paymentOptionId)) {
                this._enableButton(); // The submit button is disabled at this point, enable it
                $('body').unblock(); // The page is blocked at this point, unblock it
                return Promise.resolve();
           }
            // do the call to the route stored in the 'data_set' input of the acquirer form, the data must be called 'create-route'
            this._rpc({
                route: '/payment/ebizcharge/s2s/create_json_3ds',
                params: this._getPaymentDetails(paymentOptionId),
            }).then(function (data) {
                // if the server has returned true
                if (data.result) {
                    // and it need a 3DS authentication
                    if (data['3d_secure'] !== false) {
                        // then we display the 3DS page to the user
                        $("body").html(data['3d_secure']);
                    }
                    else{
                        return self._rpc({
                            route: self.txContext.transactionRoute,
                            params: self._prepareTransactionRouteParams('ebizcharge', acquirerId, 'direct'),
                        }).then(processingValues => {
                            // Initiate the payment
                            return self._rpc({
                                route: '/payment/ebizcharge',
                                params: {
                                    'reference': processingValues.reference,
                                    'partner_id': processingValues.partner_id,
                                    'opaque_data': response.opaqueData,
                                    'access_token': processingValues.access_token,
                                }
                            }).then(() => window.location = '/payment/status');
                        }).guardedCatch((error) => {
                            error.event.preventDefault();
                            self._displayError(
                                _t("Server Error"),
                                _t("We are not able to process your payment."),
                                error.message.data.message
                            );
                        });
                    }
                }
                // if the server has returned false, we display an error
                else {
                    if (data.error) {
                        self.displayError(
                            '',
                            data.error);
                    } else { // if the server doesn't provide an error message
                        var tab = $('.nav-link.active');
                        if(tab[0].id ==='card-tab'){
                            self.displayError(
                            _t('Server Error'),
                            _t('e.g. Your credit card details are wrong. Please verify.'));
                        }
                        else{
                            self.displayError(
                            _t('Server Error'),
                            _t('e.g. Your account details are wrong. Please verify.'));
                        }
                    }
                }
                // here we remove the 'processing' icon from the 'add a new payment' button
                self.enableButton(button);
            }).guardedCatch(function (error) {
                error.event.preventDefault();
                // if the rpc fails, pretty obvious
                self.enableButton(button);

                self.displayError(
                    _t('Server Error'),
                    _t("We are not able to add your payment method at the moment.") +
                        self._parseError(error)
                );
            });
        },

        /**
         * Handle the response from Authorize.Net and initiate the payment.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @param {object} response - The payment nonce returned by Authorized.Net
         * @return {Promise}
         */
//        _responseHandler: function (acquirerId, response) {
//            if (response.messages.resultCode === 'Error') {
//                let error = "";
//                response.messages.message.forEach(msg => error += `${msg.code}: ${msg.text}\n`);
//                this._displayError(
//                    _t("Server Error"),
//                    _t("We are not able to process your payment."),
//                    error
//                );
//                return Promise.resolve();
//            }
//
//            // Create the transaction and retrieve the processing values
//            return this._rpc({
//                route: this.txContext.transactionRoute,
//                params: this._prepareTransactionRouteParams('authorize', acquirerId, 'direct'),
//            }).then(processingValues => {
//                // Initiate the payment
//                return this._rpc({
//                    route: '/payment/authorize/payment',
//                    params: {
//                        'reference': processingValues.reference,
//                        'partner_id': processingValues.partner_id,
//                        'opaque_data': response.opaqueData,
//                        'access_token': processingValues.access_token,
//                    }
//                }).then(() => window.location = '/payment/status');
//            }).guardedCatch((error) => {
//                error.event.preventDefault();
//                this._displayError(
//                    _t("Server Error"),
//                    _t("We are not able to process your payment."),
//                    error.message.data.message
//                );
//            });
//        },

        /**
         * Checks that all payment inputs adhere to the DOM validation constraints.
         *
         * @private
         * @param {number} acquirerId - The id of the selected acquirer
         * @return {boolean} - Whether all elements pass the validation constraints
         */
        _validateFormInputs: function (acquirerId) {
            const inputs = Object.values(this._getInlineFormInputs(acquirerId));
            return inputs.every(element => element.reportValidity());
        },

    };

    checkoutForm.include(ebizchargeMixin);
    manageForm.include(ebizchargeMixin);
});