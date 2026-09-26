# GitHub Publication Checklist

The repository has been sanitized locally, but the following human decisions remain before changing a GitHub repository to Public:

- [ ] Choose the public author name in `LICENSE`.
- [ ] Configure GitHub private vulnerability reporting or replace the placeholder route in `SECURITY.md` with a private contact.
- [ ] Replace the general entries in `THIRD_PARTY_NOTICES.md` with exact upstream commits, reused files and required license text.
- [ ] Review every file in the first Git commit and confirm no vendor material or device evidence was added through Git LFS.
- [ ] Run `python3 scripts/validate_public_repo.py` and the GitHub Actions workflow.
- [ ] Create the GitHub repository as Private first; inspect Actions artifacts and the final tree before making it Public.
- [ ] Use a research-preview release label and avoid claiming that AF speed, AF-C persistence or object recognition is production-ready.

The local Git repository intentionally has no commit and no remote. Committing and publishing remain explicit user actions.

