from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from .errors import Conflict, Missing, Refused

class Receipts:
    def __init__(self, capacity):
        self.lock = RLock()
        self.capacity = capacity
        self.index = OrderedDict()
        self.records = {}
        self.sequence = 0

    def execute(self, command, operation):
        with self.lock:
            key = command.storage_key()
            old = self.index.get(key)
            if old is not None:
                if old['fingerprint'] != command.fingerprint():
                    raise Conflict('request shape')
                self.index.move_to_end(key)
                return deepcopy(old['response'])
            response = operation(command)
            self.sequence += 1
            response.update(receipt='receipt-' + str(self.sequence), tenant=command.tenant,
                            subject=command.subject, units=command.units)
            self.records[response['receipt']] = deepcopy(response)
            self.index[key] = {'fingerprint': command.fingerprint(), 'response': deepcopy(response)}
            while len(self.index) > self.capacity:
                self.index.popitem(last=False)
            return deepcopy(response)

    def owned(self, principal, receipt_id):
        value = self.records.get(receipt_id)
        if value is None:
            raise Missing('receipt')
        if (value['tenant'], value['subject']) != (principal.tenant, principal.subject):
            raise Refused('receipt owner')
        return deepcopy(value)
