from .commands import Command
from .validation import name

class Routes:
    def __init__(self, accounts, receipts):
        self.accounts = accounts
        self.receipts = receipts

    def create(self, request):
        command = Command.parse(request.principal, request.arguments)
        self.accounts.authorize(request.principal, command)
        return self.receipts.execute(command, self.accounts.transfer)

    def balance(self, request):
        return self.accounts.balance(request.principal, name(request.arguments['account']))

    def receipt(self, request):
        return self.receipts.owned(request.principal, name(request.arguments['receipt']))
