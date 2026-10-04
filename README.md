# Fullstack Coding Challenge

**Implementation notes.** This solution is FastAPI + Vue 3 + PostgreSQL. Run with `make up` (or `docker compose up --build`) — see [SETUP.md](SETUP.md).

GitHub’s REST <a href="https://docs.github.com/en/rest/commits/commits#list-commits" target="_blank" rel="noopener noreferrer">List commits</a> endpoint returns at most 100 commits per page, so 1000 commits is about 10 requests. Unauthenticated clients are limited to **60 requests per hour**; a <a href="https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens" target="_blank" rel="noopener noreferrer">personal access token</a> raises the primary limit to **5,000 requests per hour** (<a href="https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api" target="_blank" rel="noopener noreferrer">Rate limits for the REST API</a>). Decisions and trade-offs are in [DECISIONS.md](DECISIONS.md).

Thanks for your interest in the Fullstack Developer role at Circunomics. This challenge is the next step in our process.
 
We care far more about how you reason than about how much you build. Please read the timebox and the notes on scope before you start.
 
## Prerequisites
 
- A backend language and framework of your choice — PHP/Symfony is our stack and is what we'd most like to see, but Java, Node.js, Python, Go, C# or anything else you're strong in is equally accepted
- A relational database (MySQL, PostgreSQL)
- A component-based frontend framework — Angular preferred, React or Vue perfectly acceptable
- Docker
Use whatever you're fastest and best in. We work in PHP/Symfony and expect you to pick it up from day one, but this challenge is about how you build, not which framework you already know.
 
## Timebox
 
Please spend no more than **6 hours**. We would rather see a small, solid, well-reasoned result than a large half-finished one. Cutting scope deliberately is part of what we are assessing — tell us what you cut and why.
 
## Task
 
1. Fork this repository.
2. Create a `source` folder for your code.
3. Build a web application with a backend in the language and framework of your choice, and a frontend in Angular, React or Vue.
The application lets a user track contributor activity across GitHub repositories. It should provide:
 
**Add a repository** — the user enters an `owner/repo` and the application imports its most recent commits (hashes, author, date) from the <a href="https://docs.github.com/en/rest" target="_blank" rel="noopener noreferrer">GitHub REST API</a>, storing them in the database. Aim for up to 1000 commits per repository. Re-importing the same repository must not create duplicates.
 
**Repository list** — every imported repository, with its commit count and when it was last synced. Each one can be re-synced.
 
**Contributors** — for a given repository, the authors and their commit counts. Sortable, searchable, filterable by date range, and paginated. Sorting, filtering and pagination must happen server-side.
 
**Contributor detail** — the commits belonging to one author, paginated, each linking to the commit on GitHub.
 
Keep your solution flexible enough to support other providers, such as the GitLab or Bitbucket APIs, later on.
 
## Requirements
 
- Every screen has explicit loading, empty and error states
- Re-importing is idempotent, with a test that proves it
- `docker compose up` brings up the application and its database in one command
- Use your ecosystem's standard dependency manager and project layout
- Automated tests — you decide what is worth testing, and tell us why
Visual design is **not** assessed. Plain, unstyled components are fine.
 
## Decisions
 
Some parts of the task above are deliberately underspecified. Where something isn't defined, decide, and record the decision and your reasoning in `DECISIONS.md`.
 
Questions you will probably run into, among others:
 
- What should the interface do while a long import is running?
- What happens if the GitHub API rate-limits you halfway through an import?
- Is the same person appearing under two email addresses one contributor or two?
- What does "last synced" mean if the last sync failed partway?
Please also include a short section in `DECISIONS.md` covering what you deliberately did **not** build, and what you would do next with more time.
 
## AI usage
 
We use AI coding assistants as a normal part of our engineering workflow, and you should use them here as you normally would. In `AI_USAGE.md`, please tell us:
 
- Which tools or agents you used
- How you split the work between yourself and the agent
- One thing the agent produced that you rejected or rewrote, and why
## Conceptual questions
 
Please answer these in a Markdown file and commit it to the repository. English, and diagrams are welcome.
 
1. How did you debug this project, and with which tools?
2. What is your approach to testing this project, and what did you choose to leave untested?
3. You now need to support GitLab and Bitbucket. Walk through what changes in your code and what doesn't.
4. A user imports a repository with 500,000 commits and the contributors page becomes unusable. Where do you look first, and what are your options?
5. Which part of your solution would you not ship to production as-is, and why?
## What we are looking for
 
Roughly in order of weight:
 
- **Data model and correctness** — schema design, idempotent imports, sensible handling of partial failure
- **End-to-end coherence** — the API is shaped by what the interface needs, and the feature works from database to screen
- **Decisions under ambiguity** — you noticed the gaps, made a call, and can defend it
- **Tests** — proportionate, meaningful, and you can say why these and not others
- **Code quality** — readable, maintainable, reviewable
## Once complete
 
1. Create a `SETUP.md` in the base directory with setup instructions.
2. Create a **private** repository on GitHub and grant access to <jobs@circunomics.com>.
3. Email <jobs@circunomics.com> to let us know you are done.
 
