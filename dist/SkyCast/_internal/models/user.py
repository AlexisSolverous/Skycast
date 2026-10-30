import hashlib


class User:
    """Represents one SkyCast account.

    ENCAPSULATION: the raw password is never stored anywhere. Only a
    one-way hash (_password_hash) is kept, and it is marked private
    with a leading underscore — the rest of the app is only allowed
    to ask "does this password match?" through check_password(), it
    can never read the hash back out directly.
    """

    def __init__(self, user_id, username, password_hash):
        self._id = user_id
        self._username = username
        self._password_hash = password_hash

    @staticmethod
    def hash_password(raw_password):
        """Turn a plain-text password into a one-way SHA-256 hash."""
        return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()

    def check_password(self, raw_password):
        """Return True if raw_password matches this account's password."""
        return self._password_hash == User.hash_password(raw_password)

    @property
    def id(self):
        return self._id

    @property
    def username(self):
        return self._username
