# FastAPI + PostgreSQL Auth API

A REST API built with FastAPI and PostgreSQL, currently focused on authentication and account management, with an event/RSVP feature designed and planned on top of it (see "Current state" below). This is part of one of my personal projects, built to get real, hands-on experience with authentication, password security, and a relational data model — not from a tutorial, but by designing and implementing it myself.

## Current state

- **Accounts and authentication**: fully implemented and working. Sign up, log in, view/update/delete your profile.
- **Events, guests, and RSVPs**: the data model is designed and the tables exist in `db.py`. The API routes for them are next on the list.

## Authentication

The authentication system follows FastAPI's official security documentation (OAuth2 with Password flow and JWT bearer tokens) closely: `OAuth2PasswordBearer` for extracting the token from the request, `OAuth2PasswordRequestForm` for the login payload, and a `get_current_user` dependency that decodes the JWT and loads the user for every protected route. This is the same pattern FastAPI recommends for production APIs, and I implemented it end to end myself rather than copying a boilerplate.

A few things I made sure to get right:

- Passwords are hashed with **Argon2** via `pwdlib`, the currently recommended algorithm for password storage. Plaintext passwords are never stored or logged.
- The login endpoint hashes a dummy password even when the submitted email doesn't exist, before rejecting the request. This closes a timing side-channel: without it, a login attempt for a real account takes measurably longer than one for a fake account (because of the extra hash comparison), which an attacker could use to enumerate valid emails.
- JWTs are signed with a server-side secret key and decoded with the algorithm explicitly pinned (`algorithms=[ALGORITHM]`), which avoids algorithm-confusion attacks on the decode step.
- Tokens expire after 15 minutes, so a leaked token has a short useful lifetime.

## Running it locally

You'll need Python 3.13+ and a PostgreSQL server running locally.

1. Clone the repo and create a virtual environment:
   ```
   python3 -m venv myenv
   source myenv/bin/activate
   ```
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your own values (database credentials and a secret key for signing tokens):
   ```
   cp .env.example .env
   ```
4. Create the database tables:
   ```
   python3 -c "from db import db_setup; db_setup()"
   ```
5. Start the server:
   ```
   uvicorn fastapi_config:app --reload
   ```

The API runs at `http://127.0.0.1:8000`. FastAPI generates interactive docs automatically at `http://127.0.0.1:8000/docs`, where every endpoint can be tried directly from the browser.

## API overview

| Method | Route | What it does | Auth required |
|---|---|---|---|
| GET | `/` | Health check | no |
| POST | `/signup` | Create an account | no |
| POST | `/login` | Log in, get back a JWT | no |
| GET | `/home` | Example protected route | yes |
| GET | `/account` | View your profile | yes |
| PATCH | `/account` | Update your profile | yes |
| DELETE | `/account` | Delete your account | yes |

For protected routes, the token from `/login` goes in the request header as `Authorization: Bearer <token>`.

## Testing

```
pytest
```

The suite covers signup, login, the auth dependency, and the account routes, both through the actual HTTP layer (`tests/test_auth.py`, `tests/test_account.py`) and at the unit level directly against `jwt_auth.py` (`tests/test_jwt_auth.py`) — including a token-expiry check that doesn't require waiting 15 minutes for a token to actually expire.

Tests never touch the real database: `conftest.py` points the app at a temporary SQLite file for the duration of the run and tears it down afterward, so running the suite is safe on any machine, with or without Postgres set up.
