# Google sign-in

Google OAuth is **optional**. When it isn't configured the backend hides the
`/auth/google/*` routes and the frontend hides the "Continue with Google" button —
email + password still works.

## Setup (local, ports 8896 / 8897)

1. **Google Cloud Console** → create (or pick) a project.
2. **APIs & Services → OAuth consent screen**
   - User type: *External*
   - Scopes: `openid`, `.../auth/userinfo.email`, `.../auth/userinfo.profile`
   - While the app is in *Testing*, add your own Google account under *Test users*.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   - Application type: *Web application*
   - **Authorized redirect URI:** `http://localhost:8896/api/v1/auth/google/callback`
   - (optional) Authorized JavaScript origin: `http://localhost:8896`
4. Copy the **Client ID** and **Client secret** into `.env`:

   ```dotenv
   GOOGLE_OAUTH_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=xxxxxxxx
   NEXT_PUBLIC_GOOGLE_ENABLED=true
   ```

5. `docker compose up` (restart). The button appears; the routes activate.

## Production

- Set `PUBLIC_BASE_URL=https://your-domain` and add
  `https://your-domain/api/v1/auth/google/callback` as an authorized redirect URI.
- Set `ENVIRONMENT=production` so session cookies are marked `Secure`.
- Publish the OAuth consent screen so any Google user can sign in.

## How the flow works

```
Browser                     CoMark backend                     Google
   │  GET /api/v1/auth/google/authorize                            │
   ├───────────────────────────►│                                  │
   │        302 to Google + Set-Cookie: comark_oauth_state         │
   │◄───────────────────────────┤                                  │
   │  consent screen                                               │
   ├──────────────────────────────────────────────────────────────►│
   │  302 back to /api/v1/auth/google/callback?code=…&state=…       │
   │◄──────────────────────────────────────────────────────────────┤
   ├───────────────────────────►│  verify state cookie             │
   │                            │  exchange code → token ─────────►│
   │                            │  fetch id + email ──────────────►│
   │                            │  find-or-create User (+ link     │
   │                            │  oauth_account, associate_by_email)
   │        302 /dashboard + Set-Cookie: comark_session            │
   │◄───────────────────────────┤                                  │
```

Implementation: `backend/app/api/v1/routes/auth_google.py` (thin routes over
`httpx-oauth` + `fastapi-users`' `UserManager.oauth_callback`). The session cookie
issued at the end is the same one email/password login uses, so everything
downstream is identical.
