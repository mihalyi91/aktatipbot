# pylint: disable=C0115, W0231

"""
TODO
"""

class InvalidCommandError(Exception):
    def __init__(self, command: str) -> None:
        self.command = command

class ZeroTransactionError(Exception):
    pass

class UserNotOptedInError(Exception):
    pass

class ReceiverNotOptedInError(Exception):
    pass

class AlreadyOptedInError(Exception):
    pass

class InsufficientFundsError(Exception):
    def __init__(self, amount: float, balance: float) -> None:
        self.amount, self.balance = amount, balance

class InvalidUserError(Exception):
    def __init__(self, username: str) -> None:
        self.username = username

class FirstTransactionError(Exception):
    def __init__(self, amount: float) -> None:
        self.amount = amount

