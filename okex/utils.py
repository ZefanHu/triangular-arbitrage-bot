import hmac
import base64
import time
import datetime
from . import consts as c


def clean_dict_none(d: dict) -> dict:
    return {k:d[k] for k in d.keys() if d[k] != None}


def sign(message, secretKey):
    mac = hmac.new(bytes(secretKey, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()
    return base64.b64encode(d)


def pre_hash(timestamp, method, request_path, body):
    return str(timestamp) + str.upper(method) + request_path + body


def get_header(api_key, sign, timestamp, passphrase, flag):
    header = dict()
    header[c.CONTENT_TYPE] = c.APPLICATION_JSON
    header[c.OK_ACCESS_KEY] = api_key
    header[c.OK_ACCESS_SIGN] = sign
    header[c.OK_ACCESS_TIMESTAMP] = str(timestamp)
    header[c.OK_ACCESS_PASSPHRASE] = passphrase
    header['x-simulated-trading'] = flag
    return header


def parse_params_to_str(params):
    params = clean_dict_none(params)
    url = '?'
    for key, value in params.items():
        url = url + str(key) + '=' + str(value) + '&'
    return url[0:-1]


def get_timestamp():
    now = datetime.datetime.now(datetime.timezone.utc)
    t = now.isoformat("T", "milliseconds")
    # 移除+00:00时区信息，因为我们已经知道这是UTC时间
    if t.endswith('+00:00'):
        t = t[:-6]
    return t + "Z"


def signature(timestamp, method, request_path, body, secret_key):
    if str(body) == '{}' or str(body) == 'None':
        body = ''
    message = str(timestamp) + str.upper(method) + request_path + str(body)

    mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()

    return base64.b64encode(d)
