```markdown
# claude-code-skill-factory Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill introduces the core development patterns and conventions used in the `claude-code-skill-factory` Python repository. You'll learn best practices for file naming, import/export styles, commit messaging, and testing approaches. This guide is designed to help you quickly onboard and contribute effectively to the codebase.

## Coding Conventions

### File Naming
- **Snake case** is used for all file names.
  - Example: `my_module.py`, `data_processor.py`

### Import Style
- **Relative imports** are preferred within the package.
  - Example:
    ```python
    from .utils import helper_function
    from ..models import DataModel
    ```

### Export Style
- **Named exports** are used to explicitly define what a module exposes.
  - Example (`my_module.py`):
    ```python
    def useful_function():
        pass

    __all__ = ['useful_function']
    ```

### Commit Patterns
- **Freeform commit messages** with no strict prefixing.
- Average commit message length is about 72 characters.
  - Example:  
    ```
    Add data validation to input parser for better error handling
    ```

## Workflows

### Adding a New Module
**Trigger:** When you need to introduce new functionality.
**Command:** `/add-module`

1. Create a new Python file using snake_case naming.
2. Implement your functions/classes.
3. Use relative imports for any internal dependencies.
4. Define `__all__` for explicit exports.
5. Write corresponding tests in a `*.test.*` file.

### Writing and Running Tests
**Trigger:** When you add or modify code.
**Command:** `/run-tests`

1. Create test files matching the pattern `*.test.*` (e.g., `my_module.test.py`).
2. Write test functions for your code.
3. Use the project's preferred (unknown) test framework.
4. Run tests manually or via CI if configured.

### Making Commits
**Trigger:** After completing a logical unit of work.
**Command:** `/commit`

1. Write a clear, concise commit message (~72 characters).
2. No strict prefixing required.
3. Commit your changes.

## Testing Patterns

- **Test files** follow the `*.test.*` naming convention (e.g., `utils.test.py`).
- The specific test framework is not enforced; use standard Python testing tools (e.g., `unittest`, `pytest`) unless otherwise specified.
- Place tests alongside or near the code they test for easy discovery.

  Example test file (`my_module.test.py`):
  ```python
  import unittest
  from .my_module import useful_function

  class TestUsefulFunction(unittest.TestCase):
      def test_basic(self):
          self.assertTrue(useful_function())
  ```

## Commands
| Command      | Purpose                                      |
|--------------|----------------------------------------------|
| /add-module  | Scaffold and add a new module                |
| /run-tests   | Run all tests in the repository              |
| /commit      | Make a commit with a clear, concise message  |
```