# Repository Access & Freeze — D2 Report Appendix (evidence row 18)

> Fill the ⟨placeholders⟩ at freeze time (EOD Tue 7 Jul); everything else is
> ready. This page satisfies the rubric items "make sure lecturers have access
> to the GitHub Repo for marking" and "repo frozen upon submission".

## Repository

| Item | Value |
|---|---|
| Repository URL | https://github.com/leewayne451/ssd (private) |
| Default branch | `main` |
| **Frozen commit SHA** | ⟨run `git rev-parse main` after the final merge⟩ |
| Freeze tag | `d2-freeze` → ⟨same SHA⟩ |
| Freeze date/time | ⟨e.g. Tue 7 Jul 2026, 23:xx SGT⟩ |
| Deployed application | https://chateaucollective.duckdns.org |

## Access for marking

| Who | GitHub username | Role | Added on |
|---|---|---|---|
| Lecturer/marker | ⟨username from prof⟩ | Read | ⟨date⟩ |
| ⟨2nd marker if any⟩ | ⟨username⟩ | Read | ⟨date⟩ |

*Screenshot to attach:* Settings → Collaborators page showing all 7 team
members + marker access.

## Freeze procedure (leader runs at freeze)

```bash
git checkout main && git pull
git tag -a d2-freeze -m "D2 submission freeze"
git push origin d2-freeze
git rev-parse main    # -> SHA for the table above
```

Then: merge nothing further to `main`; branch protection stays on so nothing
lands accidentally. (If a post-freeze emergency fix is ever debated: don't —
D3 QA reviews the frozen SHA; divergence looks worse than any bug.)

## Team contribution snapshot (rubric: every member contributing)

*Screenshots to attach at freeze:*
1. Insights → Contributors graph (all 7 members visible)
2. Closed PRs list (each member authoring + reviewing)
3. Issues board "Chateau Collective - D2" (Done column per owner)
