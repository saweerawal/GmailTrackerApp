# Gmail Tracker App

Gmail Tracker App is a Flask-based web application that integrates with Gmail via OAuth 2.0 to fetch and display unread emails. It provides a simple interface for users to authenticate with Google and view their email data.

## Features

- **OAuth Authentication**: Secure login using Google OAuth to access Gmail API with readonly permissions.
- **Email Fetching**: Retrieve unread emails or filter by custom queries (e.g., "is:unread").
- **Email Details**: Display key information for each email, including subject, sender name and email, date, and a snippet of the content.
- **Session Management**: Handles user sessions for authentication state, with options to check status and logout.
- **Static File Serving**: Serves a frontend interface (assumed to be in the `static` folder) for interacting with the API.
- **CORS Support**: Enabled for cross-origin requests, with credentials support.

## Setup

1. Obtain Google API credentials and place `credentials.json` in the project root.
2. Install dependencies: `pip install flask flask-cors google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`.
3. Run the app: `python app.py`.
4. Access at `http://127.0.0.1:5000`.

## API Endpoints

- `GET /auth/login`: Initiates OAuth flow.
- `GET /oauth/callback`: Handles OAuth callback.
- `GET /auth/status`: Checks authentication status.
- `GET /auth/logout`: Logs out the user.
- `GET /api/emails`: Fetches emails (params: `max`, `q`).
- `GET /`: Serves the frontend.

Note: This app is for localhost development only.