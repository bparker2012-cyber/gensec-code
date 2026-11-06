# Homework 6 recording script

Target **4:40**, maximum **5:00**. Start with your camera on and record your
own narration. Use unlisted YouTube; test the link signed out. A Loom-only
link does not satisfy the written hosting instruction.

## Preparation before recording

Have Git, uv, and your Codex interface ready and authenticated. Close unrelated
personal windows and use readable fonts. Rehearse the real generation once;
its duration varies. Keep the actual generation visible. Do not present copied
source as a new generation or claim success before the regenerated app works.

Preview the checked-in app from its `hw6/` folder with
`uv run --locked python app.py`. It runs on port 5006; use port 5007 for the
regenerated app. Fresh clones have no sample account or database.

## 0:00–0:25 Introduction and clone

Camera on. Say:

“I’m Brehon Parker, bparker2012. For Homework 6 I used OpenAI Codex to generate
Secure Notes, a Python application for private notes. I’ll clone the repository,
show the prompts, regenerate the app, and demonstrate its security and limits.”

Run:

```sh
HW6_TAKE="$(mktemp -d "${TMPDIR:-/tmp}/hw6-recording.XXXXXX")"
git clone --branch codex/hw6-secure-notes --single-branch https://github.com/bparker2012-cyber/gensec-code.git "$HW6_TAKE/course"
cd "$HW6_TAKE/course"
git log -5 --oneline
```

## 0:25–0:50 Prompt overview

Open `hw6/prompts.txt`. Say:

“Prompt 1 defines the notes app and its security requirements. Prompt 2 asks
Codex to test adversarial input and prepare the demonstration. These standalone
replay prompts come from our agreed task. The original chat is also preserved.”

## 0:50–2:45 Generate from the prompts

```sh
HW6_REPLAY="$(python3 hw6/prepare_replay.py --path-only)"
printf '%s\n' "$HW6_REPLAY"
ls -a "$HW6_REPLAY/hw6"
```

Open the printed replay root in a fresh Codex workspace. Paste the complete
Prompt 1 and then Prompt 2 from `prompts.txt`. Allow the agent to create and
check the files. Say while it works:

“This folder started with prompts and pinned dependencies only. Codex is
writing the implementation. The finished application needs no model API.”

In the replay workspace terminal, run the newly generated code:

```sh
cd "$HW6_REPLAY/hw6"
uv sync --locked --group dev
uv run --locked pytest -q
uv run --locked python app.py --demo
```

These commands assume the generated output follows the prompts. If it does
not, ask Codex to fix it and save the follow-up prompt. Rehearse before the
final take. The original 59 passing tests do not prove a different regenerated
implementation is correct. In a separate terminal, use the printed absolute
replay path if the `HW6_REPLAY` variable is unavailable.

## 2:45–3:25 Security explanation

Show the owner checks, hashing, and CSRF verification in the actual generated
source. Say only if present:

“Every note operation checks the signed-in owner. SQL uses parameters, and
template escaping keeps note text from becoming executable HTML. Passwords
use salted scrypt hashes. POST forms require CSRF tokens. Signing out revokes
the server-side session token. Sessions and input sizes are bounded, and
repeated authentication attempts are limited.”

Explain that `--demo` calls real handlers through Flask's in-process test
client with temporary data; it is separate from the browser demonstration.

## 3:25–4:25 Functionality and limitations

```sh
uv run --locked python app.py --port 5007
```

Open `http://127.0.0.1:5007`. Register a sample account, create a note, edit it,
and reopen it. If time allows, save `<script>alert(1)</script>` as note text
and show it stays text. Open Privacy and security. Say:

“I can create, reopen, and edit my notes. The checks also exercise cross-account
access, CSRF, SQL injection, and revoked sessions. Notes are plaintext at rest,
so this is not an encrypted vault. HTTP on loopback and the development server
are for class. Public use needs HTTPS and production operations. There is no
MFA or password recovery.”

## 4:25–4:40 Close

“The repository contains the code, prompts, tests, evidence, and report. This
shows what was generated and tested, including its limitations.” Stop before 5:00.

## After recording

1. Upload as **Unlisted** on YouTube and test the link in incognito.
2. Put only the real URL in `hw6/screencast_url.txt`.
3. Refresh the Word/PDF report and include any new replay prompts/evidence.
4. Commit and push the completed recording stage separately.
5. Upload the final PDF to Homework 06 on Canvas. Observed deadline:
   Friday, November 6, 2026 at 11:59 p.m. Eastern.
