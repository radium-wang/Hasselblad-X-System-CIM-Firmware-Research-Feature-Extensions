# GitHub Publication Checklist

The repository has been sanitized locally, but the following human decisions remain before changing a GitHub repository to Public:

- [x] Choose the public author name in `LICENSE` (`Radium Wang`).
- [x] Add a standalone bilingual research disclaimer and link it from the repository entry points.
- [x] Add GitHub citation metadata and a citation-only external research index.
- [ ] Configure GitHub private vulnerability reporting or replace the placeholder route in `SECURITY.md` with a private contact.
- [ ] Replace the general entries in `THIRD_PARTY_NOTICES.md` with exact upstream commits, reused files and required license text.
- [ ] Review every file in the first Git commit and confirm no vendor material or device evidence was added through Git LFS.
- [ ] Run `python3 scripts/validate_public_repo.py` and the GitHub Actions workflow.
- [ ] Create the GitHub repository as Private first; inspect Actions artifacts and the final tree before making it Public.
- [ ] Use a research-preview release label and avoid claiming that AF speed, AF-C persistence or object recognition is production-ready.

As checked on 2026-10-06, the configured GitHub repository is already Public and uses `main`. The checklist above is the historical initial-release checklist, not a claim that every item is complete. The 2026-10-06 research update passed the public-tree validator and existing offline reproduction suite; excluded vendor inputs and original hardware evidence remain local. Repository visibility was not changed by this update.
