# Git Guide

Бұл бөлім жобаңызды Git-ке дұрыс шығару үшін.

## 1. Репозиторийді инициализациялау

Егер `.git` әлі жоқ болса:

```bash
git init
git branch -M main
```

## 2. Ignore ережелері

Жобада `.gitignore` бар. Ол төмендегілерді push-тен қорғайды:

- `__pycache__/`
- `*.db`
- `.env`
- `token.json`
- `model/saved_model/*` (үлкен model artifact-тер)
- `data/processed/*`

## 3. Алғашқы commit

```bash
git add .
git commit -m "feat: scaffold PhishGuard MVP and add full docs"
```

## 4. Remote қосу және push

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## 5. Қалыпты workflow (келесі өзгерістерге)

```bash
git checkout -b codex/docs-update
git add docs/ README.md
git commit -m "docs: update technical runbook and architecture"
git push -u origin codex/docs-update
```

Содан кейін GitHub-та Pull Request ашасыз.

## 6. Диплом алдында ұсынылатын Git hygiene

1. `main` тармағында тек stable нұсқа қалдыру.
2. Large файлдарды (model checkpoints) репоға қоспау.
3. `README.md` + `docs/` актуал күйде болу.
4. Тег қою:

```bash
git tag -a v1.0-diploma -m "PhishGuard diploma MVP"
git push origin v1.0-diploma
```

