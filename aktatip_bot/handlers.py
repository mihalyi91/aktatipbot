# pylint: disable=C0321

"""
File containing the EventHandler class, that takes in
a praw Event and performs the matching action
"""

from time import time_ns
from typing import Union

from algosdk import encoding

from praw.models.reddit.comment import Comment
from praw.models.reddit.message import Message

from clients import console
from errors import (InsufficientFundsError, InvalidCommandError, AlreadyOptedInError, ReceiverNotOptedInError,
                      UserNotOptedInError, UserNotOptedInError, InvalidUserError, ZeroTransactionError)
from instances import User
from templates import (EVENT_RECEIVED, INSUFFICIENT_FUNDS, SENDER_NOT_OPT_IN,
                              RECEIVER_NOT_OPT_IN, NO_WALLET, ZERO_TRANSACTION)
from utils import is_float, valid_user,  COMMENT_COMMANDS

class EventHandler:
    """
    Class used to handle an incoming event
    and keep in memory the unconfirmed transactions
    note: could probably do  without a class
    """
    unconfirmed_transactions: set = set()

    def handle_comment(self, comment: Comment) -> None:
        """
        Handle a comment.
        The only use of the comment is to tip the person whose
        post/comment was commented using !asatip
        """
        author = User(comment.author.name)
        if author.new:
            comment.reply(NO_WALLET)
            return
        receiver = User(comment.parent().author.name)
        command = comment.body.split()
        first_word = command.pop(0).lower()
        if first_word not in COMMENT_COMMANDS:
            return

        if not command: raise InvalidCommandError(comment.body) # If command empty after popping username
        amountIn = command.pop(0)  
  
        if not is_float(amountIn): raise InvalidCommandError(comment.body)
        amount = float(amountIn)
        note = " ".join(command)

        try:
            transaction = author.send(receiver, amount, note, comment)
            self.unconfirmed_transactions.add(transaction)
        except UserNotOptedInError:
            comment.reply(SENDER_NOT_OPT_IN)
        except ReceiverNotOptedInError:
            comment.reply(RECEIVER_NOT_OPT_IN)
        except ZeroTransactionError:
            comment.reply(ZERO_TRANSACTION)
        except InsufficientFundsError as e: # pylint: disable=C0103
            comment.reply(INSUFFICIENT_FUNDS.substitute(balance=e.balance,
                                                         amount=e.amount))
    def handle_message(self, message: Message) -> None: # pylint: disable=R0912, R0915
        """
        Parses the incoming message to determine what action to take
        The user can:
         * tip
         * withdraw
         * check balance
        """
        author = User(message.author.name)
        command = message.body.split()
        main_cmd = command.pop(0).lower()

        ######################### Handle tip command #########################
        if main_cmd == "tip": # This whole check is ugly, make it nice
            if len(command) < 2: raise InvalidCommandError(message.body)

            amountIn = command.pop(0)
            if not is_float(amountIn): raise InvalidCommandError(message.body)
            username = command.pop(0)
            if not valid_user(username): raise InvalidUserError(username)

            amount = float(amountIn)
            receiver = User(username)
            note = " ".join(command)

            try:
                transaction = author.send(receiver, amount, note, message)
                self.unconfirmed_transactions.add(transaction)
            except UserNotOptedInError:
                message.reply(SENDER_NOT_OPT_IN)
            except ReceiverNotOptedInError:
                message.reply(RECEIVER_NOT_OPT_IN)
            except ZeroTransactionError:
                message.reply(ZERO_TRANSACTION)
            except InsufficientFundsError as e: # pylint: disable=C0103
                message.reply(INSUFFICIENT_FUNDS.substitute(balance=e.balance,
                                                             amount=e.amount))

        ######################### Handle withdraw command #########################
        elif main_cmd == "withdraw":
            if len(command) < 2: raise InvalidCommandError(message.body)
            amount = command.pop(0)
            if not ((amount) or is_float(amount)): raise InvalidCommandError(message.body)
            address = command.pop(0)
            if not encoding.is_valid_address(address): raise InvalidCommandError(message.body)
            note = " ".join(command)

            try:
                transaction = author.withdraw(amount, address, note, message, False)
                self.unconfirmed_transactions.add(transaction)
            except ZeroTransactionError:
                message.reply(ZERO_TRANSACTION)
            except InsufficientFundsError as e: # pylint: disable=C0103
                message.reply(INSUFFICIENT_FUNDS.substitute(balance=e.balance,
                                                             amount=e.amount))
        ######################### Handle algo withdraw command #########################
        elif main_cmd == "algowithdraw":
            if len(command) < 2: raise InvalidCommandError(message.body)
            amount = command.pop(0)
            if not ((amount) or is_float(amount)): raise InvalidCommandError(message.body)
            address = command.pop(0)
            if not encoding.is_valid_address(address): raise InvalidCommandError(message.body)
            note = " ".join(command)

            try:
                transaction = author.withdraw(amount, address, note, message, True)
                self.unconfirmed_transactions.add(transaction)
            except ZeroTransactionError:
                message.reply(ZERO_TRANSACTION)
            except InsufficientFundsError as e: # pylint: disable=C0103
                message.reply(INSUFFICIENT_FUNDS.substitute(balance=e.balance,
                                                             amount=e.amount))
        ######################### Handle opt in command #########################
        elif main_cmd == "optin":
            if len(command) > 0: raise InvalidCommandError(message.body)

            if author.new:
                pass

            try:
                transaction = author.optin(message)
                self.unconfirmed_transactions.add(transaction)
            except ZeroTransactionError:
                message.reply(ZERO_TRANSACTION)
            except AlreadyOptedInError:
                message.reply("Already opted in, no need to repeate")
            except InsufficientFundsError as e: # pylint: disable=C0103
                message.reply(INSUFFICIENT_FUNDS.substitute(balance=e.balance,
                                                             amount=e.amount))
        ######################### Handle wallet command #########################
        elif main_cmd == "wallet":
            if len(command) > 0: raise InvalidCommandError(message.body)

            if author.new:
                pass
            else:
                message.reply(str(author.wallet))

            console.log(f"Wallet information sent to {author.name} (#{author.user_id})")

        ######################### Handle unknown command #########################
        else:
            raise InvalidCommandError(message.body)

    def handle_event(self, event: Union[Comment, Message]) -> None:
        """
        Logs the incoming event and distributes it to handle_comment
        or handle_message depending on the type
        """
        console.log(EVENT_RECEIVED.substitute(author=event.author,
                                              event_type=type(event).__name__.lower(),
                                              body=event.body))

        if isinstance(event, Message):
            self.handle_message(event)
        elif isinstance(event, Comment):
            self.handle_comment(event)
        else:
            console.log(f"Unknown event was received, of type : {type(event)}")
