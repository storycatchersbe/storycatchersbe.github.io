# Storycatchers V1

Static website for [Storycatchers](https://storycatchers.be).

- **Repository:** [storycatchersbe/storycatchersbe.github.io](https://github.com/storycatchersbe/storycatchersbe.github.io)
- **Live site:** [storycatchers.be](https://storycatchers.be) (custom domain via `CNAME`)

## Local preview

```bash
./serve.command
```

Or:

```bash
python3 -m http.server 8811
```

Then open `http://localhost:8811/nl/`.

## Git workflow

All commits and pushes go to `origin`:

```text
https://github.com/storycatchersbe/storycatchersbe.github.io.git
```

Typical flow:

1. Work on a feature branch (for example `cursor/my-change`)
2. Commit and push: `git push -u origin HEAD`
3. Open a pull request into `main`
4. Merge the PR on GitHub

Check remotes with:

```bash
git remote -v
```

## Deploy

The site deploys automatically to GitHub Pages when changes are merged into `main` (GitHub Actions workflow in `.github/workflows/pages.yml`).

GitHub Pages settings:

1. Go to **Settings → Pages**
2. Under **Build and deployment**, set **Source** to **GitHub Actions**
3. Confirm the custom domain `storycatchers.be` is configured
