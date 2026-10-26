import json
from .errors import Refused, Invalid, Missing, Conflict, Temporary

CODES = {Refused: 'refused', Invalid: 'invalid', Missing: 'missing',
         Conflict: 'conflict', Temporary: 'temporary'}

def success(request_id, result):
    value = json.loads(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return {'id': request_id, 'ok': True, 'result': value}

def failure(request_id, error):
    code = next((value for kind, value in CODES.items() if isinstance(error, kind)), 'internal')
    return {'id': request_id, 'ok': False, 'error': {'code': code}}
