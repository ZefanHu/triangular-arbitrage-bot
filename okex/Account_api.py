from .client import Client
from .consts import *


class AccountAPI(Client):

    def __init__(self, api_key, api_secret_key, passphrase, use_server_time=False, flag='0'):
        Client.__init__(self, api_key, api_secret_key, passphrase, use_server_time, flag)

    # Get Positions
    def get_position_risk(self, instType=None):
        params = {}
        if instType:
            params['instType'] = instType
        return self._request_with_params(GET, POSITION_RISK, params)

    # Get Balance
    def get_account(self, ccy=None):
        params = {}
        if ccy:
            params['ccy'] = ccy
        return self._request_with_params(GET, ACCOUNT_INFO, params)

    # Get Positions
    def get_positions(self, instType=None, instId=None):
        params = {}
        if instType:
            params['instType'] = instType
        if instId:
            params['instId'] = instId
        return self._request_with_params(GET, POSITION_INFO, params)

    # Get Bills Details (recent 7 days)
    def get_bills_detail(self, instType=None, ccy=None, mgnMode=None, ctType=None, type=None, subType=None, after=None, before=None,
                         limit=None):
        params = {'instType': instType, 'ccy': ccy, 'mgnMode': mgnMode, 'ctType': ctType, 'type': type,
                  'subType': subType, 'after': after, 'before': before, 'limit': limit}
        return self._request_with_params(GET, BILLS_DETAIL, params)

    # Get Bills Details (recent 3 months)
    def get_bills_details(self, instType=None, ccy=None, mgnMode=None, ctType=None, type=None, subType=None, after=None, before=None,
                          limit=None):
        local_vars = locals()
        params = {}
        for var_name in ['instType', 'ccy', 'mgnMode', 'ctType', 'type', 'subType', 'after', 'before', 'limit']:
            var_value = local_vars.get(var_name)
            if var_value is not None:
                params[var_name] = var_value
        return self._request_with_params(GET, BILLS_ARCHIVE, params)

    # Get Account Configuration
    def get_account_config(self):
        return self._request_without_params(GET, ACCOUNT_CONFIG)

    # Get Account Configuration
    def set_position_mode(self, posMode):
        params = {'posMode': posMode}
        return self._request_with_params(POST, POSITION_MODE, params)

    # Get Account Configuration
    def set_leverage(self, lever, mgnMode, instId=None, ccy=None, posSide=None):
        params = {'lever': lever, 'mgnMode': mgnMode, 'instId': instId, 'ccy': ccy, 'posSide': posSide}
        return self._request_with_params(POST, SET_LEVERAGE, params)

    # Get Maximum Tradable Size For Instrument
    def get_maximum_trade_size(self, instId, tdMode, ccy=None, px=None):
        params = {'instId': instId, 'tdMode': tdMode, 'ccy': ccy, 'px': px}
        return self._request_with_params(GET, MAX_TRADE_SIZE, params)

    # Get Maximum Available Tradable Amount
    def get_max_avail_size(self, instId, tdMode, ccy=None, reduceOnly=None):
        params = {'instId': instId, 'tdMode': tdMode, 'ccy': ccy, 'reduceOnly': reduceOnly}
        return self._request_with_params(GET, MAX_AVAIL_SIZE, params)

    # Increase / Decrease margin
    def Adjustment_margin(self, instId, posSide, type, amt):
        params = {'instId': instId, 'posSide': posSide, 'type': type, 'amt': amt}
        return self._request_with_params(POST, ADJUSTMENT_MARGIN, params)

    # Get Leverage
    def get_leverage(self, instId, mgnMode):
        params = {'instId': instId, 'mgnMode': mgnMode}
        return self._request_with_params(GET, GET_LEVERAGE, params)

    def adjust_leverage_info(self, instType, mgnMode, lever, instId=None, ccy=None, posSide=None):
        params = {'instType': instType, 'mgnMode': mgnMode, 'lever': lever, 'instId': instId, 'ccy': ccy, 'posSide': posSide}
        return self._request_with_params(GET, ADJUST_LEVERAGE_INFO, params)

    # Get the maximum loan of isolated MARGIN
    def get_max_loan(self, instId, mgnMode, mgnCcy):
        params = {'instId': instId, 'mgnMode': mgnMode, 'mgnCcy': mgnCcy}
        return self._request_with_params(GET, MAX_LOAN, params)

    def set_auto_loan(self, auto_loan):
        params = {'autoLoan': auto_loan}
        return self._request_with_params(POST, AUTO_LOAN, params)

    def set_account_level(self, account_level):
        params = {'acctLv': account_level}
        return self._request_with_params(POST, ACCOUNT_LEVEL, params)

    # Get Fee Rates
    def get_fee_rates(self, instType, instId=None, uly=None, category=None):
        params = {'instType': instType, 'instId': instId, 'uly': uly, 'category': category}
        return self._request_with_params(GET, FEE_RATES, params)

    def vip_borrow_repay(self, ccy, side, amt, ordId=None):
        params = {'ccy': ccy, 'side': side, 'amt': amt, 'ordId': ordId}
        return self._request_with_params(POST, BORROW_REPAY, params)

    def vip_borrow_repay_history(self, ccy=None, after=None, before=None, limit=None):
        params = {'ccy': ccy, 'after': after, 'before': before, 'limit': limit}
        return self._request_with_params(GET, BORROW_REPAY_HISTORY, params)

    def vip_interest_accrued(self, ccy=None, ordId=None, after=None, before=None, limit=None):
        params = {'ccy': ccy, 'ordId': ordId, 'after': after, 'before': before, 'limit': limit}
        return self._request_with_params(GET, VIP_INTEREST_ACCRUED, params)

    def vip_interest_deducted(self, ordId=None, ccy=None, after=None, before=None, limit=None):
        params = {'ordId': ordId, 'ccy': ccy, 'after': after, 'before': before, 'limit': limit}
        return self._request_with_params(GET, VIP_INTEREST_DEDUCTED, params)

    def vip_loan_order_list(self, ordId=None, state=None, ccy=None, after=None, before=None, limit=None):
        params = {'ordId': ordId, 'state': state, 'ccy': ccy, 'after': after, 'before': before, 'limit': limit}
        return self._request_with_params(GET, VIP_LOAN_ORDER_LIST, params)

    def vip_loan_order_detail(self, ordId, ccy=None, after=None, before=None, limit=None):
        params = {'ordId': ordId, 'ccy': ccy, 'after': after, 'before': before, 'limit': limit}
        return self._request_with_params(GET, VIP_LOAN_ORDER_DETAIL, params)

    # Get interest-accrued
    def get_interest_accrued(self, type=None, ccy=None, instId=None, mgnMode=None, after=None, before=None, limit=None):
        params = {'type': type, 'ccy': ccy, 'instId': instId, 'mgnMode': mgnMode, 'after': after, 'before': before, 'limit': limit}
        return self._request_with_params(GET, INTEREST_ACCRUED, params)

    # Get interest-accrued
    def get_interest_rate(self, ccy=None):
        params = {'ccy': ccy}
        return self._request_with_params(GET, INTEREST_RATE_ACCOUNT, params)

    def get_interest_limits(self, type=None, ccy=None):
        params = {'type': type, 'ccy': ccy}
        return self._request_with_params(GET, INTEREST_LIMITS, params)

    # Set Greeks (PA/BS)
    def set_greeks(self, greeksType):
        params = {'greeksType': greeksType}
        return self._request_with_params(POST, SET_GREEKS, params)

    # Get Maximum Withdrawals
    def get_max_withdrawal(self, ccy=None):
        params = {}
        if ccy:
            params['ccy'] = ccy
        return self._request_with_params(GET, MAX_WITHDRAWAL, params)

    def move_positions(self, from_account, to_account, legs, client_id):
        params = {'fromAcct': from_account, 'toAcct': to_account, 'legs': legs, 'clientId': client_id}
        return self._request_with_params(POST, MOVE_POSITIONS, params)