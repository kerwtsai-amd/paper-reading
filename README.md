# Paper Reading

This repository turns paper discovery, deep reading, and evidence-traceable Traditional Chinese HTML summaries into a browsable research website. Both HTML and Confluence summaries use a reader-first explanatory spine: minimal prerequisites → problem and root cause → prior-art gap → derived requirements → end-to-end method → claim-aligned evidence → limitations. Each paper follows the project structure `<Topic>/<Subtopic>/<Formal Paper Title>/`. Its summary is created from `html template/summary-template.html` and must pass validation defined by the paper-reading Skill. All generated paper summaries must be written in Traditional Chinese, even though the repository documentation and Skill instructions are written in English.

## Automation Architecture

The workflow is deliberately divided into three stages so that paper processing, website deployment, and notification each have a clear responsibility boundary:

1. **Local Codex project cron**: Runs daily in the project's actual checkout, reads `automation/daily-reading.json`, discovers candidate papers for enabled topics, filters them for quality, and deduplicates them. It then follows `.agents/skills/paper-reading/SKILL.md` to read each selected paper in full, create its classification, write its Traditional Chinese summary, extract any necessary figures or tables, validate the result, and only then commit and push it.
2. **GitHub Actions / Pages**: After a push to the default branch, the Pages workflow in this repository builds and deploys the publicly browsable static website. This stage processes only committed website sources; it does not discover or read papers.
3. **Local Teams notification**: After pushing, the Codex cron waits for the corresponding GitHub Pages deployment to succeed. It then uses the local `m365-teams` Skill to send the new summary's Pages URL to the configured chat or channel. Teams credentials remain local and are never provided to GitHub Actions.

```text
Daily Codex cron (local)
  └─ Discover → read deeply → validate → commit/push
                                          └─ GitHub Actions → Pages deployment
                                                                            └─ Local m365-teams notification after success
```

At the beginning of every scheduled run, the automation first resumes any work that was already committed and pushed but whose Pages deployment or Teams notification was not confirmed. It starts new paper discovery only after all reconciliation work is complete. If no eligible unread paper is found that day, the recovery check still runs, but the automation does not create an empty commit or publication record and does not send a new “paper added” notification. If a previously pending commit is confirmed as not yet notified, its notification is sent exactly once.

## Published Site Structure

- `/` is the dashboard. It links to the library, shows up to three recently active Topic/Subtopic folders, and presents the three most recently updated paper readings.
- `/library/` is the searchable repository. Its generated folder pages provide `Topic → Subtopic → Paper` navigation.
- `/papers/<stable-slug>/` contains each published summary. A paper keeps this source-derived URL when its Topic or Subtopic classification changes.

Recency comes from each summary's validated update-date metadata rather than filesystem timestamps or Git checkout time. All navigation pages contain only generated HTML and links to already approved public summary assets; local PDFs and internal workspace files remain excluded.

## Daily Reading Configuration

The configuration file is [`automation/daily-reading.json`](automation/daily-reading.json). Its `topics` array is currently empty, so the automation will neither invent nor enable a research topic. Add at least one topic with `enabled: true` before automatic paper selection can begin.

The complete rules for safety checks, paper selection, validation, precise staging, Pages readiness, crash recovery, and duplicate-proof Teams notification are in [`automation/daily-run.md`](automation/daily-run.md). To configure the Teams destination, copy [`automation/daily-reading.local.example.json`](automation/daily-reading.local.example.json) to the local file `automation/daily-reading.local.json`; the actual local file is ignored by Git.

Before pushing each publication commit, the workflow creates `automation/state/publications/<commit-sha>--<destination-key>.json` and updates it atomically after the push, deployment, and notification are confirmed. This Git-ignored record uses the full commit SHA and a destination hash as its stable identity. The notification also contains a deterministic marker. After a timeout, the next run checks the remote branch, the Pages deployment for that exact SHA, and existing Teams messages for that marker instead of blindly pushing, deploying, or notifying again. A record is marked complete only after all three stages are confirmed, and completed records are never notified again.

Each item in `topics` supports:

| Field | Purpose |
| --- | --- |
| `id` | Stable, unique machine identifier; lowercase alphanumeric characters and hyphens are recommended. |
| `name` | Topic name shown in execution records. |
| `enabled` | Whether the topic participates in the daily search. |
| `queries` | One or more search queries; candidate results for the same topic are merged and deduplicated. |
| `excludeTerms` | Terms that exclude a result when found in its title or abstract. |

Use the following shape for a topic object, replacing the angle-bracket placeholders:

```json
{
  "id": "<topic-id>",
  "name": "<topic-name>",
  "enabled": true,
  "queries": ["<search-query-one>", "<search-query-two>"],
  "excludeTerms": ["<excluded-term>"]
}
```

Global paper-selection rules:

- `selection.dailyMaxPapers`: Maximum number of papers completed in one run. The default is `1`, shared across all topics rather than applied separately to each topic.
- `selection.lookback.days`: Candidate-paper lookback window. The default is `7` days, evaluated against the `submittedOrPublished` date.
- `quality`: Requires a canonical landing page, accessible full text, complete author information, and an abstract, with first-party sources preferred. `preferPeerReviewed` is a ranking preference and does not strictly exclude recent preprints.
- `deduplication`: Compares DOI, arXiv ID, and normalized title in that order. It also scans existing summaries and skips papers that have already been processed.

Topic definitions are safe to commit, but tokens, cookies, Teams chat or channel IDs, private webhooks, and other credentials do not belong in this configuration file. Notification destinations and authentication state must be provided through secure local storage used by the automation or Skill.

## Enabling the Daily Workflow

Create the Codex project cron only after the Git remote, GitHub Pages workflow, and Pages URL are configured. The recommended schedule is every morning in the `Asia/Taipei` time zone. Its prompt should require at least the following behavior:

- Read this repository's `AGENTS.md`, the paper-reading Skill, and `automation/daily-reading.json` before doing any work.
- Exit safely when `topics` is empty or no topic is enabled; never invent a topic.
- Discover papers, cross-check sources, apply the quality and deduplication rules, and select no more than `dailyMaxPapers` papers.
- Read every selected paper in full, classify it, create its template-based Traditional Chinese summary, extract necessary figures or tables, and validate the result. Never generate a summary from the abstract alone.
- Commit only the website content produced in the current run that passed validation. Synchronize remote changes before pushing, and never force-push after a conflict or failure.
- After pushing, confirm that the GitHub Pages deployment for the exact commit succeeded before sending an accessible summary URL through the local `m365-teams` Skill. Do not send a broken link when deployment fails.
- Reconcile all Git-ignored pending publication records at the beginning of every run. When an outcome is uncertain, check the deployment or Teams marker before beginning that day's discovery.

The schedule and Teams destination are local Codex settings and are not created automatically by files in this repository. This boundary also prevents company account information from entering Git history.

## Security and Publishing Boundaries

- **Do not publish PDFs**: `.gitignore` excludes every `*.pdf`. Paper PDFs are for local reading only and must not be copied into the GitHub Pages artifact. A summary may link to the canonical publisher or arXiv page, but it must not assume that a local PDF link will work on the public website.
- **Do not commit secrets**: Never commit access tokens, cookies, webhooks, Teams conversation identifiers, or `.env` or local override files containing secrets. If a secret has ever entered a commit, deleting it from the current tree is insufficient; revoke and rotate the credential as well.
- **Public Pages is not access control**: Treat every HTML file, image, and metadata item on the public GitHub Pages site as readable by anyone. Do not publish AMD-confidential or NDA-covered material, personal data, or private research notes. Robots directives, hard-to-guess URLs, and omission from the index are not access controls.
- **Respect licensing**: Keep summaries and necessary quotations paraphrased and traceable to their sources. Whether a paper's figures or tables may be published must still be evaluated under the paper's license and the applicable fair-use context.
