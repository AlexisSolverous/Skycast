import streamlit as st

from auth_session import create_remembered_login, initialize_auth, logout
from database.db_handler import DatabaseHandler
from database.seed_cities import seed_if_empty
from models.user import User
from ui import setup_page

setup_page("SkyCast", "⛅")

# The database is created (and the 100 starter cities are seeded)
# automatically the first time the app runs.
db = DatabaseHandler()
seed_if_empty(db)
initialize_auth(db)

if st.session_state.get("_redirect_after_login_token") == st.session_state.get(
    "remembered_login_token"
) and st.session_state.get("_redirect_after_login_token"):
    st.session_state.pop("_redirect_after_login_token")
    st.switch_page("pages/1_Dashboard.py")


def open_dashboard(user):
    create_remembered_login(db, user)
    st.session_state.user = user
    st.session_state["_redirect_after_login_token"] = st.session_state[
        "_active_login_token"
    ]
    st.rerun()


def login_form():
    st.subheader("Log In")
    # Forms submit together, so users can press Enter after entering a password.
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Log In")
    if submitted:
        row = db.get_user_by_username(username)
        if row is None:
            st.error("No account with that username.")
            return
        user = User(row["id"], row["username"], row["password_hash"])
        if user.check_password(password):
            open_dashboard(user)
        else:
            st.error("Incorrect password.")


def signup_form():
    st.subheader("Create an Account")
    with st.form("signup_form"):
        username = st.text_input("Choose a username", key="signup_username")
        password = st.text_input(
            "Choose a password", type="password", key="signup_password"
        )
        submitted = st.form_submit_button("Sign Up")
    if submitted:
        if not username or not password:
            st.warning("Please fill in both fields.")
            return
        if db.get_user_by_username(username) is not None:
            st.error("That username is already taken.")
            return
        db.create_user(username, User.hash_password(password))
        row = db.get_user_by_username(username)
        user = User(row["id"], row["username"], row["password_hash"])
        open_dashboard(user)


st.title("⛅ SkyCast")
st.caption("A desktop weather forecasting and trip-planning app")

if st.session_state.user:
    st.success(f"Logged in as **{st.session_state.user.username}**")
    st.write(
        "Use the sidebar to open **Dashboard** (review trips, rename or delete "
        "them, and check the weather) or **Trips** (build a multi-city itinerary)."
    )
    st.metric("Cities available", db.count_cities())
    if st.button("Log Out"):
        logout(db)
        st.rerun()
else:
    tab1, tab2 = st.tabs(["Log In", "Sign Up"])
    with tab1:
        login_form()
    with tab2:
        signup_form()
