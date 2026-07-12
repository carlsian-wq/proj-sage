# Auth Middleware

Project Sage demo docs.

## Configuration
Set AUTH_SECRET in the environment. Middleware reads JWT from the Authorization header.

## Usage
Call equire_auth() on protected routes. Returns 401 when the token is missing or expired.
