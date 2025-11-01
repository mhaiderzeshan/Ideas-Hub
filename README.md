# Ideas Hub

Ideas Hub is a FastAPI-based application that allows users to manage their ideas. It provides a secure authentication system using both local authentication (email/password) and Google OAuth.

## Features

- **User Authentication:**
  - Local authentication (signup/login with email and password).
  - Google OAuth 2.0 for social login.
  - JWT-based authentication with access and refresh tokens.
- **User Management:**
  - Get user profile information.
- **Idea Management (Future):**
  - Create, read, update, and delete ideas.

## Technologies Used

- **Backend:**
  - [FastAPI](https://fastapi.tiangolo.com/): A modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints.
  - [SQLAlchemy](https://www.sqlalchemy.org/): The Python SQL Toolkit and Object Relational Mapper.
  - [Pydantic](https://pydantic-docs.helpmanual.io/): Data validation and settings management using Python type annotations.
  - [Alembic](https://alembic.sqlalchemy.org/en/latest/): A lightweight database migration tool for usage with the SQLAlchemy Database Toolkit for Python.
  - [Uvicorn](https://www.uvicorn.org/): An ASGI server implementation, for use with FastAPI.
- **Authentication:**
  - [Passlib](https://passlib.readthedocs.io/en/stable/): for hashing passwords.
  - [python-jose](https://python-jose.readthedocs.io/en/latest/): for JWT creation and validation.
  - [Authlib](https://authlib.org/): for Google OAuth integration.
- **Database:**
  - [MySQL](https://www.mysql.com/) (can be configured to use other databases).

## API Endpoints

### Local Authentication

- `POST /signup`: Register a new user.
- `POST /login`: Log in a user and get access and refresh tokens.

### Google Authentication

- `GET /auth/google/login`: Redirect to Google's login page.
- `GET /auth/callback`: Handle the callback from Google after authentication.
- `POST /auth/refresh`: Refresh the access token.
- `POST /auth/logout`: Log out the user.

### Users

- `GET /me`: Get the current user's profile.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/mhaiderzeshan/Ideas-Hub.git
    cd ideas-hub
    ```

2.  **Create a virtual environment and activate it:**

    ```bash
    python -m venv env
    source env/bin/activate  # On Windows, use `env\Scripts\activate`
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the environment variables:**

    Create a `.env` file in the root directory and add the following variables:

    ```
    SECRET_KEY=your-secret-key
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    REFRESH_TOKEN_EXPIRE_DAYS=7
    GOOGLE_CLIENT_ID=your-google-client-id
    GOOGLE_CLIENT_SECRET=your-google-client-secret
    DATABASE_URL=mysql+pymysql://user:password@host/db_name
    CORS_ORIGINS=http://localhost:3000
    ENVIRONMENT=development
    ```

5.  **Run the database migrations:**

    ```bash
    alembic upgrade head
    ```

## Usage

1.  **Start the application:**

    ```bash
    uvicorn app.main:app --reload
    ```

2.  **Access the API documentation:**

    Open your browser and go to `http://localhost:8000/docs` to see the interactive API documentation (Swagger UI).

![Screenshot](images/doc.png)
