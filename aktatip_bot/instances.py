"""
TODO
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import time_ns
from typing import Optional

from algosdk import transaction
from algosdk.account import generate_account
from algosdk.mnemonic import from_private_key
from algosdk.util import algos_to_microalgos, microalgos_to_algos

from clients import algod, console, reddit
from errors import (FirstTransactionError, InsufficientFundsError, ReceiverNotOptedInError,
                               UserNotOptedInError, ZeroTransactionError, AlreadyOptedInError)
from templates import (TRANSACTION_CONFIRMATION, WALLET_REPR, AKTA_ID, OPT_IN,
                             WITHDRAWAL_ALGO_CONFIRMATION, WITHDRAWAL_CONFIRMATION)
from utils import get_next_userId, get_wallet_by_userId, get_userId_by_name, save_user, save_wallet

@dataclass
class Wallet:
    """
    Class representing an ALGO wallet, containing helper methods
    """
    private_key: str
    public_key: str

    @classmethod
    def generate(cls) -> "Wallet":
        """
        Generates a public/private key pair

        Returns:
            wallet: an instance of the class Wallet with the generated keys
        """
        private_key, public_key = generate_account()
        return cls(private_key, public_key)

    @classmethod
    def load(cls, user_id: int) -> Optional["Wallet"]:
        """
        Loads the wallet keys from the given user

        Args:
            user_id: the DB user-id for which we want the keys
        Returns:
            wallet:
                None if the wallet information isn't found in the DB
                An instance of the class Wallet with the fetched keys otherwise
        """
        wallet_dict = get_wallet_by_userId(user_id)
        if not wallet_dict: # pylint: disable=R1705
            return None
        else:
            return cls(wallet_dict["private_key"], wallet_dict["public_key"])

    def log(self, user: "User") -> None:
        """
        Saves the wallet information to the database

        Args:
            user: an instance of User corresponding to the wallet owner
        """
        console.log(f"Wallet created for user {user.name} (#{user.user_id})")
        save_wallet(user.user_id, self.private_key, self.public_key)

    @property
    def qrcode(self) -> None:
        """
        Returns the link to a QR code created from the public key of this wallet
        """
        return f"https://api.qrserver.com/v1/create-qr-code/?data={self.public_key}&size=220x220&margin=4"

    @property
    def balance(self) -> float:
        """
        Returns the balance of the wallet

        Returns:
            balance: the balance of the wallet as a float, in Algos
        """
        account_info = algod.account_info(self.public_key)
        balance = float(microalgos_to_algos(account_info["amount"]))
        return balance

    @property
    def balanceAKTA(self) -> float:
        """
        Returns the balance of the wallet

        Returns:
            balance: the balance of the wallet as a float, in AKTAs
        """
        account_info = algod.account_info(self.public_key)
        for scrutinized_asset in account_info['assets']:      
         if (scrutinized_asset['asset-id'] == AKTA_ID):
           return microalgos_to_algos(scrutinized_asset['amount'])
        return "not opt-in"

    def __repr__(self) -> str:
        """
        Returns all information about the wallet in a string

        Returns:
            str
        """
        return WALLET_REPR.substitute(private_key=from_private_key(self.private_key),
                                      public_key=self.public_key,
                                      balance=self.balance,
                                      balanceAKTA=self.balanceAKTA,
                                      qr_code_link=self.qrcode)

class User:
    """
    Class representing a Reddit user
    """
    def __init__(self, name: str, wallet: Wallet = None) -> None:
        """
        TODO: doc
        """
        self.name = name.lower()
        user_id = get_userId_by_name(self.name)
        if user_id is None:
           user_id = get_next_userId()
           self.user_id = user_id
           self.log()
        else:
           self.user_id = user_id

        self.new = False

        if wallet is None:
            wallet = Wallet.load(self.user_id)
  
        if wallet is None:
            self.new = True
            wallet = Wallet.generate()
            wallet.log(self)

        self.wallet = wallet

    def send(self, other_user: "User", amount: float, note: str, message) -> Optional["Transaction"]:
        """
        Send AKTAs to the targeted user

        Args:
            other_user:
            amount:
            note:
            event:
        Returns:
            trsctn: the Transaction instance representing the transaction that was sent
        """
        trsctn = TipTransaction(self, other_user, amount, note, message)
        trsctn.validate()
        trsctn.send()
        return trsctn
    
    def withdraw(self, amount: float, address: str, note: str, message, isAlgo) -> Optional["Transaction"]:
        """
        Withdraw AKTAs to the targeted address

        Args:
            amount:
            address:
            note:
        Returns:
            trsctn: the Transaction  instance representing the transaction that was sent
        """
        trsctn = WithdrawTransaction(self, address, amount, note, message, isAlgo)
        trsctn.validate()
        trsctn.send()
        return trsctn

    def optin(self, message) -> Optional["Transaction"]:
        """
        Optin AKTAs to the targeted address

        Args:
            message:
        Returns:
            trsctn: the Transaction  instance representing the transaction that was sent
        """
        trsctn = OptInTransaction(self, message)
        trsctn.validate()
        trsctn.send()
        return trsctn

    def log(self):
        """
        Log the user creation in the console and save it in the DB
        """
        console.log(f"New user : {self.name} (#{self.user_id})")
        save_user(self.name, self.user_id)


class Transaction(ABC):
    """
    Abstract class to define the methods required for a
    transaction
    """
    @abstractmethod
    def validate(self) -> bool: # pylint: disable=C0116
        pass

    @abstractmethod
    def send(self) -> "Transaction": # pylint: disable=C0116
        pass

    @abstractmethod
    def confirmed(self) -> bool: # pylint: disable=C0116
        pass

    @abstractmethod
    def send_confirmation(self) -> None: # pylint: disable=C0116
        pass

    @abstractmethod
    def log(self) -> None: # pylint: disable=C0116
        pass

    @abstractmethod
    def __hash__(self) -> int: # pylint: disable=C0116
        pass

@dataclass
class OptInTransaction(Transaction): # pylint: disable=R0902
    """
    Subclass of the Transaction class containing
    an opt-in transaction
    """
    sender: "User"
    reddit_message: "praw.models.Message"
    tx_id: str = None
    fee: float = None
    time: int = None
    params = None

    def validate(self) -> bool:
        """
        Check that the transaction is valid, otherwise raise
        a custom error indicating the issue.
        """
        if self.sender.wallet.balanceAKTA != "not opt-in":
           raise AlreadyOptedInError()
        self.params = algod.suggested_params()
        self.fee = float(microalgos_to_algos(self.params.min_fee))

        if (self.fee + 0.11) > self.sender.wallet.balance:
            raise InsufficientFundsError(self.fee + 0.11,
                                         self.sender.wallet.balance)

        if self.sender.wallet.balance == 0 and self.sender.wallet.balance < 0.1:
            raise FirstTransactionError(self.sender.wallet.balance)
    def send(self) -> "OptInTransaction":
        """
        Perform checks to make sure that the transaction can be done
        before creating it and sending it

        Returns:
            Transaction: returns itself if the transaction was successfully
                         None otherwise
        """
        params = self.params
        params.flat_fee = True
        txn = transaction.AssetTransferTxn(self.sender.wallet.public_key,
                                    0.001,
                                    params.first,
                                    params.last,
                                    params.gh,
                                    self.sender.wallet.public_key,
                                    algos_to_microalgos(0.0),
                                    flat_fee=True,
                                    index=AKTA_ID)

        signed_txn = txn.sign(self.sender.wallet.private_key)

        algod.send_transaction(signed_txn)
        self.time = time_ns() * 1e-6
        self.tx_id = signed_txn.transaction.get_txid()

        console.log(f"Transaction #{self.tx_id} opted in AKTA")
    def confirmed(self) -> bool:
        """
        Checks if the transaction has been confirmed
        Returns:
            Bool:
                True if the transaction is confirmed
                False otherwise
        """
        txinfo = algod.pending_transaction_info(self.tx_id)
        return txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0
    def send_confirmation(self) -> None:
        """
        Send a message to confirm the sender of the transaction confirmation
        """
        self.reddit_message.reply(OPT_IN)
    def log(self) -> None:
        """
        Log the transaction
        """
        console.log(f"OptInTransaction #{self.tx_id} confirmed")

    def __hash__(self) -> int:
        return hash(self.tx_id)
@dataclass
class TipTransaction(Transaction): # pylint: disable=R0902
    """
    Subclass of the Transaction class containing
    a tip transaction
    """
    sender: "User"
    receiver: "User"
    amount: float
    message: str
    reddit_message: "praw.models.Message"
    tx_id: str = None
    fee: float = None
    time: int = None
    params = None

    def validate(self) -> bool:
        """
        Check that the transaction is valid, otherwise raise
        a custom error indicating the issue.
        """
        if self.sender.wallet.balanceAKTA == "not opt-in":
           raise UserNotOptedInError()
        if self.receiver.wallet.balanceAKTA == "not opt-in":
           raise ReceiverNotOptedInError()

        self.params = algod.suggested_params()
        self.fee = float(microalgos_to_algos(self.params.min_fee))

        if self.amount < 1e-6:
            raise ZeroTransactionError

        if (self.fee + 0.2) > self.sender.wallet.balance:
            raise InsufficientFundsError(self.amount,
                                         self.sender.wallet.balance)

        if (self.amount + 0.2) > self.sender.wallet.balanceAKTA:
            raise InsufficientFundsError(self.amount,
                                         self.sender.wallet.balanceAKTA)

        if self.receiver.wallet.balance == 0 and self.amount < 0.1:
            raise FirstTransactionError(self.amount)

    def send(self) -> "TipTransaction":
        """
        Perform checks to make sure that the transaction can be done
        before creating it and sending it

        Returns:
            Transaction: returns itself if the transaction was successfully
                         None otherwise
        """
        params = self.params
        txn = transaction.AssetTransferTxn(self.sender.wallet.public_key,
                                    0.001,
                                    params.first,
                                    params.last,
                                    params.gh,
                                    self.receiver.wallet.public_key,
                                    algos_to_microalgos(self.amount),
                                    AKTA_ID,
                                    note=str.encode(self.message))

        signed_txn = txn.sign(self.sender.wallet.private_key)

        algod.send_transaction(signed_txn)
        self.time = time_ns() * 1e-6
        self.tx_id = signed_txn.transaction.get_txid()

        console.log(f"Transaction #{self.tx_id} sent by {self.sender.name} to {self.receiver.name}")

    def confirmed(self) -> bool:
        """
        Returns a boolean indicating whether or not the
        transaction is confirmed
        """
        txinfo = algod.pending_transaction_info(self.tx_id)
        return txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0


    def send_confirmation(self) -> None:
        """
        Send a message to confirm the sender of the transaction confirmation
        """
        self.reddit_message.reply(TRANSACTION_CONFIRMATION.substitute(
                                amount=self.amount,
                                receiver=self.receiver.name,
                                transaction_id=self.tx_id)
        )

    def log(self) -> None:
        """
        Log the transaction
        """
        console.log(f"TipTransaction #{self.tx_id} confirmed")

    def __hash__(self) -> int:
        return hash(self.tx_id)

@dataclass
class WithdrawTransaction(Transaction): # pylint: disable=R0902
    """
    Subclass of the Transaction class containing a
    withdrawal

    """
    sender: "User"
    destination: str
    amount: float
    message: str
    reddit_message: "praw.models.Message"
    isAlgo: bool
    tx_id: str = None
    close_account: bool = False
    fee: float = None
    time: int = None
    params = None

    def validate(self) -> bool:
        """
        Chech that the transaction is valid, otherwise raise an error
        that indicates the type of issue
        """
        print(Wallet("", self.destination).balanceAKTA)
        if self.isAlgo == False and Wallet("", self.destination).balanceAKTA == "not opt-in":
            raise ReceiverNotOptedInError() 

        self.params = algod.suggested_params()
        self.fee = float(microalgos_to_algos(self.params.min_fee))

        self.amount = self.sender.wallet.balance if self.amount == "all" else float(self.amount)
        self.close_account = (self.amount == self.sender.wallet.balance)

        if self.close_account:
            self.amount = self.amount - self.fee

        if self.amount < 1e-6:
            raise ZeroTransactionError

        if (self.fee + (int(not self.close_account)*0.2)) > self.sender.wallet.balance:
            raise InsufficientFundsError(self.amount, self.sender.wallet.balance)

        if (self.amount + (int(not self.close_account)*0.2)) > self.sender.wallet.balanceAKTA:
            raise InsufficientFundsError(self.amount, self.sender.wallet.balanceAKTA)

        if Wallet("", self.destination).balance == 0 and self.amount < 0.1:
            raise FirstTransactionError(self.amount)

    def send(self) -> "WithdrawTransaction":
        """
        Send the transaction with the parameters given during initialization of the class
        Gets the db tx id to preserve creation order
        """
        params = self.params
        if self.isAlgo:
         txn = transaction.PaymentTxn(self.sender.wallet.public_key,
                                     params.min_fee,
                                     params.first,
                                     params.last,
                                     params.gh,
                                     self.destination,
                                     algos_to_microalgos(self.amount),
                                     note=str.encode(self.message),
                                     close_remainder_to=None if not self.close_account else self.destination,
                                     flat_fee=True)
        else:
         txn = transaction.AssetTransferTxn(self.sender.wallet.public_key,
                                    0.001,
                                    params.first,
                                    params.last,
                                    params.gh,
                                    self.destination,
                                    algos_to_microalgos(self.amount),
                                    AKTA_ID)

        signed_txn = txn.sign(self.sender.wallet.private_key)

        algod.send_transaction(signed_txn)
        self.time = time_ns() * 1e-6
        self.tx_id = signed_txn.transaction.get_txid()

        console.log(f"Withdrawal #{self.tx_id} sent by {self.sender.name}")

    def confirmed(self) -> bool:
        """
        Checks if the transaction has been confirmed
        Returns:
            Bool:
                True if the transaction is confirmed
                False otherwise
        """
        txinfo = algod.pending_transaction_info(self.tx_id)
        return txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0

    def send_confirmation(self) -> None:
        """
        Sends a message to the Reddit user to confirm the withdrawal,
        and give a link to AlgoExplorer to have a proof of transaction
        """
        if self.isAlgo:
          self.reddit_message.reply(WITHDRAWAL_ALGO_CONFIRMATION.substitute(amount=self.amount,
                                                               address=self.destination,
                                                               transaction_id=self.tx_id))
        else:
          self.reddit_message.reply(WITHDRAWAL_CONFIRMATION.substitute(amount=self.amount,
                                                               address=self.destination,
                                                               transaction_id=self.tx_id))

    def log(self) -> None:
        """
        Logs the confirmation of the withdrawal to the console
        """
        console.log(f"Withdrawal #{self.tx_id} confirmed")

    def __hash__(self) -> int:
        """
        Returns a hash of the Algo transaction ID (int)
        Allows the use of this class in sets and dictionaries
        """
        return hash(self.tx_id)
