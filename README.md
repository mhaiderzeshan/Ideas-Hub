# Ideas Hub

Ideas Hub is a FastAPI-based backend application for a platform where users can share and manage their ideas. It includes features like user authentication (local and Google OAuth), idea management, image uploads, and more.

## Features

- **User Authentication:** Secure user registration and login with JWT (JSON Web Tokens).
- **Google OAuth 2.0:** Users can sign up and log in using their Google accounts.
- **Email Verification:** New users receive a verification email to activate their accounts.
- **Idea Management:** CRUD (Create, Read, Update, Delete) operations for ideas.
- **Likes:** Users can like and unlike ideas.
- **Image Uploads:** Supports image uploads to Cloudinary.
- **Role-Based Access Control:** Differentiated access levels for users.
- **Rate Limiting:** Protects the API from brute-force attacks.
- **CORS Support:** Allows access from a frontend application.
- **Dockerized:** Ready for containerization and deployment.

## Technologies Used

- **Backend:** Python, FastAPI
- **Database:** MySQL (with SQLAlchemy ORM and asyncmy driver)
- **Authentication:** Passlib for password hashing, python-jose for JWT
- **Image Storage:** Cloudinary
- **Email Service:** Brevo
- **Caching:** Redis
- **Containerization:** Docker
- **Environment Management:** pydantic-settings

## Project Structure

```
├── app/
│   ├── core/         # Core application logic (config, security, etc.)
│   ├── crud/         # CRUD operations for database models
│   ├── db/           # Database setup and models
│   ├── routers/      # API endpoint definitions
│   ├── schemas/      # Pydantic schemas for data validation
│   └── services/     # Business logic services
├── .env.example      # Example environment variables
├── Dockerfile        # Docker configuration
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/ideas-hub.git
    cd ideas-hub
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv env
    source env/bin/activate  # On Windows: env\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file by copying `.env.example` and fill in the required values.
    ```bash
    cp .env.example .env
    ```

## Running the Application

### Without Docker

To run the application locally, use `uvicorn`:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### With Docker

1.  **Build the Docker image:**
    ```bash
    docker build -t ideas-hub .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8000:8000 --env-file .env ideas-hub
    ```
The application will be available at `http://localhost:8000`.

## API Endpoints

Below is a detailed list of the available API endpoints. For interactive documentation, run the application and visit `http://localhost:8000/docs`.

### Authentication (`/auth`)

-   `POST /signup`: Register a new user.
-   `POST /login`: Log in a user with email and password.
-   `POST /logout`: Log out the current user and invalidate tokens.
-   `POST /refresh`: Refresh the access token using a refresh token.
-   `GET /google/login`: Initiate the Google OAuth 2.0 login flow.
-   `GET /auth/callback`: Callback URL for Google OAuth 2.0.
-   `POST /forgot-password`: Request a password reset email.
-   `POST /resend-reset-email`: Resend the password reset email.
-   `POST /verify-reset-token`: Verify the password reset token.
-   `POST /reset-password`: Reset the user's password using a valid token.

### Email Verification

-   `POST /verify-email`: Verify a user's email address with a token.
-   `GET /verify-email`: Verify email from a URL link.
-   `POST /resend-verification`: Resend the email verification link.
-   `GET /verification-status`: Check the email verification status of the current user.

### Users (`/users`)

-   `GET /me`: Get the profile of the currently authenticated user.
-   `GET /admin`: (Admin only) Example protected route for admin users.

### Ideas (`/ideas`)

-   `POST /`: Create a new idea.
-   `GET /`: Get a paginated list of ideas.
-   `GET /{id}`: Get a single idea by its ID.
-   `PUT /{idea_id}`: Update an existing idea.
-   `DELETE /{idea_id}`: Soft-delete an idea.

### Likes (`/posts`)

-   `POST /{post_id}/like`: Toggle like/unlike on a post.
-   `GET /{post_id}/likes`: Get the total number of likes for a post.

### Image Upload (`/upload`)

-   `POST /images`: Upload up to 5 images.

## Environment Variables

The following environment variables are required:

- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host
- `DB_PORT`: Database port
- `DB_NAME`: Database name
- `ENVIRONMENT`: Application environment (e.g., `development`, `production`)
- `SECRET_KEY`: Secret key for JWT
- `ALGORITHM`: JWT algorithm (e.g., `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiration time in minutes
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiration time in days
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `GOOGLE_REDIRECT_URI`: Google OAuth redirect URI
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins
- `REDIS_URL`: Redis connection URL
- `BREVO_API_KEY`: Brevo API key
- `EMAIL_FROM`: Sender email address
- `EMAIL_FROM_NAME`: Sender name
- `FRONTEND_URL`: Frontend application URL (for email links)
- `EMAIL_TIMEOUT`: Timeout for sending emails
- `MAX_RETRIES`: Maximum retries for sending emails
