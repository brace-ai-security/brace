from copy import deepcopy

class Delivery:
    def __init__(self):
        self.messages = []
        self.sequence = 0

    def send(self, tenant, destination, payload):
        self.sequence += 1
        receipt = {'receipt': 'delivery-' + str(self.sequence), 'destination': destination}
        self.messages.append({'tenant': tenant, 'destination': destination,
                              'payload': deepcopy(payload), **receipt})
        return receipt
