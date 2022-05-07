"""
Utility functions
"""

from prawcore.exceptions import NotFound, ServerError

from clients import algod, reddit, cur, con

COMMENT_COMMANDS = {"!asatip"}
SUBREDDITS = {"bottesting"}

def is_float(value: str) -> bool:
    """
    Utility function to know whether or not a given string
    contains a valid float

    Args:
        value: string to check
    Returns:
        Boolean:
            True if string can be converted to float
            False otherwise
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


def valid_user(username: str) -> bool:
    """
    Checks whether or not the username is valid

    Args:
        username: username to check
    Returns:
        Boolean:
            True if username exists
            False otherwise
    """
    try:
        reddit.redditor(username).id
    except NotFound:
        return False
    return True

def save_wallet(user_id, private_key, public_key):
    """
    Saves the walletdata to the db
    """
    cur.execute("INSERT INTO wallets VALUES (?, ?, ?)", (user_id, private_key, public_key))
    con.commit()

def get_wallet_by_userId(user_id):
    """
    Gets the wallet private/public kaye from the db based on user id
    """
    for row in cur.execute('SELECT * FROM wallets WHERE user_id = ?', (user_id, )):
        return {'private_key': row[1], 'public_key': row[2]}
def save_user(name, id):
    """
    Saves the user data to the db
    """
    cur.execute("INSERT INTO users VALUES (?, ?)", (id, name))
    con.commit()
def get_userId_by_name(name):
    """
    Gets the userid from the db based on user name
    """
    for row in cur.execute("SELECT id FROM users where name = ?", (name, )):
        return row[0]
    return None
def get_next_userId():
    """
    Gets the next userid from the db
    """
    for row in cur.execute('SELECT count(*) FROM users'):
        return row[0] + 1

def get_comment_cache():
    """
    Gets the processed comments from the db
    """
    comments = []
    for row in cur.execute('SELECT id FROM comments'):
        comments.append(row[0])
    return comments
def add_comment_cache(comments):
    """
    Saves the processing comments to the db
    """
    for comment in comments:
        cur.execute("INSERT INTO comments VALUES (?)", (str(comment), ))
        con.commit()
  
def stream():
    """
    Fetches the unread items in the inbox and all comments in the
    targeted subreddits that contain an AlgoTip command
    Adds the comments to a cache to know which ones were already dealt with
    """
    try:
        inbox_unread = set(reddit.inbox.unread())
        comment_cache = get_comment_cache()
        comments = {comment for comment in reddit.subreddit("+".join(SUBREDDITS)).comments(limit=100)
                            if any(command in comment.body for command in COMMENT_COMMANDS)
                            and comment.id not in comment_cache}
    except ServerError: # Avoid having the bot crash everytime the Reddit API is struggling
        return set()

    if comments:
        add_comment_cache(comments)

    return set.union(inbox_unread, comments)


# Comes from https://developer.algorand.org/docs/build-apps/hello_world/
def wait_for_confirmation(transaction_id, timeout):
    """
    Wait until the transaction is confirmed or rejected, or until 'timeout'
    number of rounds have passed.
    Args:
        transaction_id (str): the transaction to wait for
        timeout (int): maximum number of rounds to wait
    Returns:
        dict: pending transaction information, or throws an error if the transaction
            is not confirmed or rejected in the next timeout rounds
    """
    start_round = algod.status()["last-round"] + 1
    current_round = start_round

    while current_round < start_round + timeout:
        try:
            pending_txn = algod.pending_transaction_info(transaction_id)
        except Exception: # pylint: disable=W0703
            return None
        if pending_txn.get("confirmed-round", 0) > 0: # pylint: disable=R1705
            return pending_txn
        elif pending_txn["pool-error"]: # pylint: disable=R1705
            raise Exception(
                'pool error: {}'.format(pending_txn["pool-error"]))
        algod.status_after_block(current_round)
        current_round += 1
    raise TimeoutError(
        'pending tx not found in timeout rounds, timeout value = : {}'.format(timeout))
