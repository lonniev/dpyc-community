- **Shared front-end deploy.** `.github/workflows/deploy-frontend.yml` is a reusable
  workflow that builds a repo's `frontend/` and publishes it to Cloudflare Pages, making
  the Pages project on first deploy. Operator repos call it with their `pages-project`
  instead of carrying their own copy. ChartRemotely is the first caller.
- **Renovate follows `@tollbooth-dpyc/web`.** The npm browser SDK gets the same rules as
  the `tollbooth-dpyc` wheel: exact pin, patch and minor self-merge on green CI, major
  waits for review.
