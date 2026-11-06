# bparker2012 Homework 6 verification replies
FAU ID bparker2012 | Z23222679
Exact excerpts from chat-transcript.json

## Actual Codex functionality reply
The full create, read, edit, delete, and sign-out flow passed its smoke check, and the working app is committed and pushed. Canvas shows Homework 6 is due tonight at 11:59 p.m. I’m now testing the security boundaries and preparing the recording steps.

## Actual Codex security reply
All 59 security tests pass, including account isolation, CSRF rejection, HTML escaping, SQL injection attempts, and replaying a signed-out cookie. The checks also caught two error-handling bugs with hostile hostnames and oversized note IDs; both are fixed. That stage is committed and pushed.
