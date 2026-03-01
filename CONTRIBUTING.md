# 🤝 Contributing to SAFE-Triage

Welcome to the SAFE-Triage project! This guide helps AUC team members get set up and contribute.

---

## Getting Started

### 1. Get Access

Ask Ahmed (@DrAhmed7887) to add you as a collaborator on the repository.

### 2. Clone the Repository

```bash
git clone https://github.com/DrAhmed7887/safe-triage-project.git
cd safe-triage-project
```

### 3. Create Your Branch

Never push directly to `main`. Always create a feature branch:

```bash
git checkout -b your-name/what-youre-working-on
# Example: git checkout -b sara/update-frontend-ui
```

### 4. Make Changes and Push

```bash
git add .
git commit -m "Brief description of what you changed"
git push origin your-name/what-youre-working-on
```

### 5. Create a Pull Request

Go to the repository on GitHub and create a Pull Request. Ahmed will review and merge.

---

## Project Structure

```
safe-triage-project/
├── backend/          → Python/FastAPI backend (Cloud Run)
├── frontend/         → React/Vite frontend (Firebase Hosting)
├── docs/             → Documentation, papers, presentations
├── validation/       → Test suites and validation data
└── README.md         → Project overview
```

---

## What Can You Contribute?

| Area | Examples |
|------|----------|
| **Documentation** | Update TEAM.md with your info, improve docs |
| **Frontend** | UI improvements, new dashboard features |
| **Validation** | Add test cases, run validation scripts |
| **Research** | Literature review, dataset analysis |
| **Presentations** | Slides for Harvard application, competition decks |

---

## Rules

1. **Never commit secrets** — No API keys, tokens, passwords, or service account files
2. **Never push to main directly** — Always use branches + Pull Requests
3. **Never modify the triage engine rules** without Ahmed's approval — patient safety is non-negotiable
4. **Always test** before pushing — run the validation suite
5. **Write clear commit messages** — "fixed stuff" is not acceptable

---

## Environment Setup

### Backend (Python)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values. **Never commit .env files.**

---

## Questions?

Reach out to Ahmed Zayed on the team group chat or open a GitHub Issue.
