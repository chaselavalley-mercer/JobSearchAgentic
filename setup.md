# JobSearchToolAgentic Machine Setup Guide

When cloning this repository to a new machine, certain files are intentionally left out (like the virtual environment and `.env` secrets) to keep the repository clean and secure.

Follow these exact steps to get your environment running perfectly on a new machine.

## 1. Clone the Repository
If you haven't already, clone the repository and navigate into it:
```bash
git clone <your-repo-url>
cd JobSearchToolAgentic
```

## 2. Create the Virtual Environment
Create a fresh virtual environment specifically for this machine:
```bash
python -m venv .venv
```

## 3. Activate the Virtual Environment
You **must** activate the environment before installing anything.
* **On Windows (PowerShell or Command Prompt):**
  ```bash
  .\.venv\Scripts\activate
  ```
* **On Mac / Linux:**
  ```bash
  source .venv/bin/activate
  ```
*(You will know it worked when `(.venv)` appears at the start of your terminal line).*

## 4. Install Dependencies
Now that you are inside the virtual environment, install all the required Python packages (including `python-docx`):
```bash
pip install -r requirements.txt
```

## 5. Configure Your Editor (Antigravity / VS Code)
To ensure your editor's Pyre2 type-checking doesn't throw `missing-module-attribute` errors, you need to verify it is looking at your new virtual environment.

We have included a `pyrightconfig.json` file in this repository so that Antigravity automatically knows to look in the `.venv` folder. You shouldn't need to do anything manual for Antigravity.

If using VS Code separately: Press `Ctrl+Shift+P` -> `Python: Select Interpreter` -> Choose the one with `('.venv': venv)`.

## 6. Restore Your `.env` Secrets
Because `.env` files contain sensitive API keys and secrets, they are never pushed to GitHub.
1. Create a new file in the root directory named exactly `.env`
2. Manually copy your API keys or secrets from your old machine into this new file.

---
**Done!** Your environment is now perfectly replicated and `remodel_docx.py` (and all other scripts) will work flawlessly.
