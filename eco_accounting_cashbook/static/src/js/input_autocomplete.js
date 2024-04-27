
odoo.define("eco_accounting_cashbook.InputAutoComplete",
    function (require) {
        "use strict";

        // const { onMounted, onWillStart, useRef, useSubEnv, useState } = owl.hooks;
        // var { Component, onMounted, xml } = require("@odoo/owl");
        const { loadAssets } = require("@web/core/assets");
        const { escape } = require("@web/core/utils/strings");
        var concurrency = require('web.concurrency');
        var core = require('web.core');
        var _t = core._t;
        var rpc = require('web.rpc');

        // const { Component, useState, onMounted, onPatched, onWillUnmount, useRef } = owl;
        const { Component, useState, useRef, useExternalListener, onWillUpdateProps, onWillStart, onPatched, onMounted } = owl;

        class InputAutoComplete extends Component {
            setup() {
                onWillStart(async () => {
                    // await loadAssets({
                    //     cssLibs: ["/design_bom/static/src/scss/style.css"],
                    // });
                });
                onMounted(() => {
                    this.$input = $(this.input_ref.el);
                    this._bindAutoComplete();
                    this._addAutocompleteSource(this._search, { placeholder: _t('Loading...'), order: 1 });
                    if (this.props.product_name) {
                        this.$input.val(this.props.product_name);
                        this.product_id = { id: this.props.product_id, name: this.props.product_name };
                    }
                    if (this.props.qty != undefined) {
                        this.state.quantity = this.props.qty
                    }
                });
            }

            constructor(parent, props) {
                super(...arguments);
                this.state = useState({
                    show: true,
                    notifies: [],
                    quantity: 1,
                    product_id: null,
                });
                this.input_ref = useRef('input_ref');
                this._autocompleteSources = [];
                this.orderer = new concurrency.DropMisordered();
            }

            _bindAutoComplete() {
                var self = this;
                // avoid ignoring autocomplete="off" by obfuscating placeholder, see #30439
                if ($.browser.chrome && this.$input.attr('placeholder')) {
                    this.$input.attr('placeholder', function (index, val) {
                        return val.split('').join('\ufeff');
                    });
                }
                this.$input.autocomplete({
                    source: function (req, resp) {
                        self.suggestions = [];
                        _.each(self._autocompleteSources, function (source) {
                            // Resets the results for this source
                            source.results = [];

                            // Check if this source should be used for the searched term
                            const search = req.term.trim();
                            if (!source.validation || source.validation.call(self, search)) {
                                source.loading = true;

                                // Wrap the returned value of the source.method with a promise
                                // So event if the returned value is not async, it will work
                                Promise.resolve(source.method.call(self, search)).then(function (results) {
                                    source.results = results;
                                    source.loading = false;
                                    self.suggestions = self._concatenateAutocompleteResults();
                                    resp(self.suggestions);
                                });
                            }
                        });
                    },
                    select: function (event, ui) {
                        // do not select anything if the input is empty and the user
                        // presses Tab (except if he manually highlighted an item with
                        // up/down keys)
                        if (!self.floating && event.key === "Tab" && self.ignoreTabSelect) {
                            return false;
                        }

                        if (event.key === "Enter") {
                            // on Enter we do not want any additional effect, such as
                            // navigating to another field
                            event.stopImmediatePropagation();
                            event.preventDefault();
                        }

                        var item = ui.item;
                        self.floating = false;
                        if (item.id) {
                            self.reinitialize({ id: item.id, display_name: item.name });
                            // self.trigger('change-account', { account_id: item.id })
                            self.props.onChangeAccount({ account_id: item.id })
                        } else if (item.action) {
                            item.action();
                        }
                        return false;
                    },
                    focus: function (event) {
                        event.preventDefault(); // don't automatically select values on focus
                        if (event.key === "ArrowUp" || event.key === "ArrowDown") {
                            // the user manually selected an item by pressing up/down keys,
                            // so select this item if he presses tab later on
                            self.ignoreTabSelect = false;
                        }
                    },
                    open: function (event) {
                        self._onScroll = function (ev) {
                            if (ev.target !== self.$input.get(0) && self.$input.hasClass('ui-autocomplete-input')) {
                                if (ev.target.id === self.$input.autocomplete('widget').get(0).id) {
                                    ev.stopPropagation();
                                    return;
                                }
                                self.$input.autocomplete('close');
                            }
                        };
                        window.addEventListener('scroll', self._onScroll, true);
                    },
                    close: function (event) {
                        self.ignoreTabSelect = false;
                        // it is necessary to prevent ESC key from propagating to field
                        // root, to prevent unwanted discard operations.
                        if (event.which === $.ui.keyCode.ESCAPE) {
                            event.stopPropagation();
                        }
                        if (self._onScroll) {
                            window.removeEventListener('scroll', self._onScroll, true);
                        }
                    },
                    autoFocus: true,
                    html: true,
                    minLength: 0,
                    delay: this.AUTOCOMPLETE_DELAY,
                    classes: {
                        "ui-autocomplete": "dropdown-menu",
                    },
                    create: function () {
                        $(this).data('ui-autocomplete')._renderMenu = function (ulWrapper, entries) {
                            var render = this;
                            $.each(entries, function (index, entry) {
                                render._renderItemData(ulWrapper, entry);
                            });
                            $(ulWrapper).find("li > a").addClass("dropdown-item");
                        }
                    },
                });
                this.$input.autocomplete("option", "position", { my: "left top", at: "left bottom" });
                this.autocomplete_bound = true;
            }

            _addAutocompleteSource(method, params) {
                this._autocompleteSources.push({
                    method: method,
                    placeholder: (params.placeholder ? _t(params.placeholder) : _t('Loading...')) + '<i class="fa fa-spin fa-circle-o-notch pull-right"></i>',
                    validation: params.validation,
                    loading: false,
                    order: params.order || 999
                });

                this._autocompleteSources = _.sortBy(this._autocompleteSources, 'order');

            }

            async _search(searchValue = "") {
                const value = searchValue.trim();
                const domain = [['account_type', '=', 'asset_cash']]
                const context = {}

                // Exclude black-listed ids from the domain
                // const blackListedIds = this._getSearchBlacklist();
                // if (blackListedIds.length) {
                //     domain.push(['id', 'not in', blackListedIds]);
                // }

                const nameSearch = rpc.query({
                    model: 'account.account',
                    method: "name_search",
                    kwargs: {
                        name: value,
                        args: domain,
                        operator: "ilike",
                        limit: 15,
                        context,
                    }
                })

                const results = await this.orderer.add(nameSearch);

                // Format results to fit the options dropdown
                let values = results.map((result) => {
                    const [id, fullName] = result;
                    const displayName = this._getDisplayName(fullName).trim();
                    result[1] = displayName;
                    return {
                        id,
                        label: escape(displayName) || data.noDisplayContent,
                        value: displayName,
                        name: displayName,
                    };
                });

                return values;
            }

            _getDisplayName(value) {
                return value.split('\n')[0];
            }
            _formatValue() {
                var value = this.value;
                return value && value.display_name || '';
            }

            _toggleAutoComplete() {
                if (this.$input.autocomplete("widget").is(":visible")) {
                    this.$input.autocomplete("close");
                } else if (this.floating) {
                    this.$input.autocomplete("search"); // search with the input's content
                } else {
                    this.$input.autocomplete("search", ''); // search with the empty string
                }
            }

            _concatenateAutocompleteResults() {
                var results = [];
                _.each(this._autocompleteSources, function (source) {
                    if (source.results && source.results.length) {
                        results = results.concat(source.results);
                    } else if (source.loading) {
                        results.push({
                            label: source.placeholder
                        });
                    }
                });
                return results;
            }

            reinitialize(value) {
                this.isDirty = false;
                this.floating = false;
                this.product_id = value;
                var val = value ? escape(value.display_name.replace(/\s+/g, ' ')) : ''
                this.$input.val(val);
                this.value = value;
                // const {onChange} = this.props;
                // this.props.onChange(this.props.id, {product_id: value, quantity: this.state.quantity })

                // return this._setValue(value);
            }

            _onInputClick() {
                console.log("input click")
                this.$input.autocomplete("search");
            }

            _onInputFocusout() {
                console.log("input forcus")
            }

            _onInputKeyup(ev) {
                const $autocomplete = this.$input.autocomplete("widget");
                // close autocomplete if no autocomplete item is selected and user presses TAB
                // s.t. we properly move to the next field in this case
                if (ev.which === $.ui.keyCode.TAB &&
                    $autocomplete.is(":visible") &&
                    !$autocomplete.find('.ui-menu-item .ui-state-active').length) {
                    this.$input.autocomplete("close");
                }
                if (ev.which === $.ui.keyCode.ENTER || ev.which === $.ui.keyCode.TAB) {
                    // If we pressed enter or tab, we want to prevent _onInputFocusout from
                    // executing since it would open a M2O dialog to request
                    // confirmation that the many2one is not properly set.
                    // It's a case that is already handled by the autocomplete lib.
                    return;
                }
                this.isDirty = true;
                if (this.$input.val() === "") {
                    if (ev.key === "Backspace" || ev.key === "Delete") { // Backspace or Delete
                        this.ignoreTabSelect = true;
                    }
                    this.reinitialize(false);
                }
            }

            changeQuantity(e) {
                // console.log(e.target.value);
                this.state.quantity = Number(e.target.value || 0)
            }

            mounted() {
            }

        }
        Object.assign(InputAutoComplete, {
            template: "cashbook.InputAutoComplete",
        })

        return InputAutoComplete
    })
