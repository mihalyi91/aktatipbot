"""
File containing message templates
"""

from string import Template

from clients import NETWORK

AKTA_ID = 10458941

ALGOEXPLORER_LINK = f"https://{'testnet.' if NETWORK == 'testnet' else ''}algoexplorer.io"

TRANSACTION_CONFIRMATION = Template("Your tip to $receiver for $amount AKTAs was successfuly sent \n\n"
                                    f"You can check the transaction [here]({ALGOEXPLORER_LINK}/tx/$transaction_id)")

WALLET_REPR = Template(f"Public key : [$public_key]({ALGOEXPLORER_LINK}/address/$public_key) "
                       "[(QR Code)]($qr_code_link) \n\n"
                       "Private key : $private_key \n\n"
                       "Balance : $balanceAKTA AKTA, $balance Algos")

WALLET_CREATED = Template("Wallet created for user $user \n"
                          "Public key : $public_key")

EVENT_RECEIVED = Template("Received a new $event_type from $author\n"
                          "Event body : $body")


WITHDRAWAL_CONFIRMATION = Template(f"Withdrawal of $amount AKTAs to address [$address]({ALGOEXPLORER_LINK}/address/$address) successful \n\n"
                                   f"You can check the transaction [here]({ALGOEXPLORER_LINK}/tx/$transaction_id)")

WITHDRAWAL_ALGO_CONFIRMATION = Template(f"Withdrawal of $amount Algos to address [$address]({ALGOEXPLORER_LINK}/address/$address) successful \n\n"
                                   f"You can check the transaction [here]({ALGOEXPLORER_LINK}/tx/$transaction_id)")

NO_WALLET = ("You do not have an account yet. To open one, click on this "
             "[link](https://www.reddit.com/message/compose/?to=ASA_tip_bot&subject=NewAccount&message=wallet)"
             " and send the message")

INVALID_COMMAND = ("Sorry, I didn't understand what you were trying to do. \n\n"
                   "List of available commands: \n\n"
                   "**Comment:** - Comment to a post/comment \n\n"
                   "!atip *amount* - Give tip to the author of post/comment \n\n"
                   "**Message:** - Send direct message to the bot \n\n"
                   "wallet -  Get private/public keys of your wallet and your current balance \n\n"
                   "optin -  Opt-in to AKTA, make sure you have at least 0.11 Algo before send this \n\n"
                   "withdraw *amount* *address* -  Send AKTAs to any wallet \n\n"
                   "algowithdraw *amount* *address* -  Send Algos to any wallet \n\n"
                   "tip *amount* *redditorName* -  Send anon tip to a redditor")
INSUFFICIENT_FUNDS = Template("You tried to take $amount AKTA/Algo out of your wallet"
                              " but you currently do not have enough funds to do this "
                              "transaction.\n\n"
                              "You can use `wallet` to get your address and fund your account\n\n"
                              "**Note :** the wallet needs to have 0.1 Algos to be active. "
                              "You can still withdraw it by using `withdraw all <address>`")

USER_NOT_FOUND = Template("Hey, I see that you tried to tip `$username`, "
                          "but I can't find a redditor with that username.")

ZERO_TRANSACTION = ("I cancelled your transaction because you tried to do a transaction"
                    " of less than 1e-6 Algos, which is the smallest fraction "
                    "of Algos. This transaction would send 0 Algos and make you lose the fee.")

OPT_IN = ("Sucessfully opted in AKTA, from now you can receive tips.")

SENDER_NOT_OPT_IN = "You are not opt in AKTA, transfer 0.2+ algos and send optin message to the bot to opt in."

RECEIVER_NOT_OPT_IN = ("The target is not opted in AKTA. Transfer cancelled.")
