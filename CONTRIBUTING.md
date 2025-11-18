# 🤝 Contributing to PyEssential

Thank you for considering contributing to `PyEssential`! We rely on community contributions to keep this collection of utilities useful and robust.

Please review this document to ensure a smooth contribution process.

---

## 🐞 Reporting Bugs

If you find a bug in the code:

1.  **Search Existing Issues:** Check the [Issues page](https://github.com/YourUser/PyEssential/issues) to see if the bug has already been reported.
2.  **Open a New Issue:** If not reported, open a new issue.
3.  **Provide Details:** Clearly describe the bug, including:
    * The version of `PyEssential` you are using.
    * Your Python version.
    * **Steps to reproduce** the error.
    * The expected behavior versus the actual behavior.

---

## ✨ Suggesting Enhancements

If you have an idea for a new utility function, decorator, or a structural improvement:

1.  **Check Relevance:** Ensure the enhancement fits the scope of a general-purpose utility library.
2.  **Open a Feature Request:** Open an issue and title it clearly (e.g., `[Feature Request] Add JSON validation utility`).
3.  **Explain the Use Case:** Describe why this enhancement is valuable and provide a brief example of how it would be used.

---

## ⚙️ Development Workflow

We use a standard GitHub flow for contributions.

### 1. Fork and Clone

Start by forking the repository to your own GitHub account and cloning it locally.

```bash
git clone https://github.com/Abhi39054/PyEssential.git
cd PyEssential
```

### Set up the Environment
We use pip in editable mode (-e) to install the package and its dependencies, which is required for running tests.

```
# Create and activate a virtual environment (highly recommended)
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate

# Install the project and testing dependencies
pip install -e .
pip install pytest
```

### 3. Implement Your Changes

Create a new branch for your fix or feature:

```
git checkout -b fix/issue-10-time-it
# OR
git checkout -b feat/add-new-validator
```

Implement your code in the appropriate subdirectory (e.g., pyessential/decorators/).

Write Tests: All new features and bug fixes must include corresponding unit tests in the tests/ directory to prove correctness.

### 4. Run Tests

```
pytest
```

### 5. Commit and Push

Commit your changes using a descriptive commit message.

```
git commit -m "feat: Add new function to convert dict keys to snake case"
```

Push your branch to your fork.

```
git push origin your-branch-name
```

### 6. Submit a Pull Request (PR)

Go to the original PyEssential repository on GitHub and open a Pull Request from your branch to the main branch.

Reference any related issues (e.g., Fixes #10).

Describe the changes and the testing you performed.

We appreciate your help and look forward to reviewing your contributions!