from models.user import User


def test_password_hash_and_check():
    hashed = User.hash_password("mypassword123")
    user = User(1, "juan", hashed)
    assert user.check_password("mypassword123") is True
    assert user.check_password("wrongpassword") is False


def test_hash_is_not_plain_text():
    hashed = User.hash_password("secret")
    assert hashed != "secret"


def test_same_password_gives_same_hash():
    assert User.hash_password("abc123") == User.hash_password("abc123")
