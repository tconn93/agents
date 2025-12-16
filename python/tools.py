# This file defines the tools that the LLM agent can use.

import asyncio
import os
import subprocess
import re
import tempfile
from math import sqrt
from pathlib import Path
from typing import List, Dict, Any
import json

async def web_search(query: str) -> str:
    """
    A mock web search tool. In a real application, this would call a search API.
    """
    print(f"[Tool] Executing web_search with query: '{query}'")
    # In a real implementation, you would use an API like Google Search, Brave, etc.
    await asyncio.sleep(0.5) # Simulate network latency
    if "weather in london" in query.lower():
        return "The weather in London is cloudy with a high of 15°C."
    return f"Search results for '{query}' are not available in this mock implementation."

async def calculator(expression: str) -> str:
    """
    A calculator tool that can evaluate mathematical expressions.
    """
    print(f"[Tool] Executing calculator with expression: '{expression}'")
    try:
        # WARNING: Using eval is a security risk in a real production environment.
        # It's used here for simplicity. A safer library like 'numexpr' is recommended.
        # We'll add a simple whitelist of allowed functions for basic safety.
        allowed_names = {
            "sqrt": sqrt,
            "pi": 3.141592653589793,
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"

async def explore_project(path: str = ".") -> str:
    """
    Explores a project directory structure and returns a tree-like representation.
    Lists directories and files up to a reasonable depth.
    """
    print(f"[Tool] Executing explore_project on path: '{path}'")
    try:
        path_obj = Path(path).resolve()
        if not path_obj.exists():
            return f"Error: Path '{path}' does not exist."

        if not path_obj.is_dir():
            return f"Error: Path '{path}' is not a directory."

        result = [f"Directory structure of: {path_obj}\n"]
        max_items = 100  # Limit output to prevent overwhelming the LLM
        count = 0

        for root, dirs, files in os.walk(path_obj):
            if count >= max_items:
                result.append(f"\n... (truncated, showing first {max_items} items)")
                break

            # Filter out common directories to ignore
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', '.env', 'dist', 'build']]

            level = str(root).replace(str(path_obj), '').count(os.sep)
            indent = '  ' * level
            result.append(f"{indent}{os.path.basename(root)}/")

            sub_indent = '  ' * (level + 1)
            for file in sorted(files)[:20]:  # Limit files per directory
                if count >= max_items:
                    break
                result.append(f"{sub_indent}{file}")
                count += 1

        return "\n".join(result)
    except Exception as e:
        return f"Error exploring project: {e}"

async def read_file(file_path: str, max_lines: int = 500) -> str:
    """
    Reads and returns the contents of a file.
    Includes basic security checks to prevent reading sensitive files.
    """
    print(f"[Tool] Executing read_file on: '{file_path}'")
    try:
        path_obj = Path(file_path).resolve()

        if not path_obj.exists():
            return f"Error: File '{file_path}' does not exist."

        if not path_obj.is_file():
            return f"Error: '{file_path}' is not a file."

        # Basic security: prevent reading sensitive files
        sensitive_patterns = ['.env', 'id_rsa', '.pem', '.key', 'credentials']
        if any(pattern in str(path_obj) for pattern in sensitive_patterns):
            return f"Error: Cannot read potentially sensitive file '{file_path}'."

        # Read file with line limit
        with open(path_obj, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > max_lines:
                content = ''.join(lines[:max_lines])
                content += f"\n\n... (truncated, showing first {max_lines} lines of {len(lines)} total)"
            else:
                content = ''.join(lines)

        return f"Contents of {file_path}:\n\n{content}"
    except UnicodeDecodeError:
        return f"Error: File '{file_path}' appears to be binary or has encoding issues."
    except Exception as e:
        return f"Error reading file: {e}"

async def write_file(file_path: str, content: str) -> str:
    """
    Writes content to a file. Creates the file if it doesn't exist, overwrites if it does.
    Includes basic security checks.
    """
    print(f"[Tool] Executing write_file to: '{file_path}'")
    try:
        path_obj = Path(file_path).resolve()

        # Basic security: prevent writing to sensitive locations
        sensitive_patterns = ['.env', '.git/', 'id_rsa', '.pem', '.key', 'credentials']
        if any(pattern in str(path_obj) for pattern in sensitive_patterns):
            return f"Error: Cannot write to potentially sensitive location '{file_path}'."

        # Create parent directories if they don't exist
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(path_obj, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"

async def bash_command(command: str, timeout: int = 30) -> str:
    """
    Executes a bash command and returns the output.
    Includes timeout and basic security restrictions.
    """
    print(f"[Tool] Executing bash_command: '{command}'")
    try:
        # Basic security: block dangerous commands
        dangerous_patterns = ['rm -rf /', 'mkfs', 'dd if=', ':(){:|:&};:', 'fork bomb']
        if any(pattern in command.lower() for pattern in dangerous_patterns):
            return f"Error: Command contains potentially dangerous pattern and was blocked."

        # Execute the command with timeout
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        output.append(f"\nExit code: {result.returncode}")

        return "\n".join(output) if output else "Command executed with no output."
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing command: {e}"

async def bash_script(script_content: str, timeout: int = 60) -> str:
    """
    Executes a bash script provided as a string and returns the output.
    The script is written to a temporary file and executed.
    """
    print(f"[Tool] Executing bash_script")
    try:
        import tempfile

        # Basic security: block dangerous patterns
        dangerous_patterns = ['rm -rf /', 'mkfs', 'dd if=', ':(){:|:&};:']
        if any(pattern in script_content.lower() for pattern in dangerous_patterns):
            return f"Error: Script contains potentially dangerous pattern and was blocked."

        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name

        try:
            # Make script executable
            os.chmod(script_path, 0o755)

            # Execute the script
            result = subprocess.run(
                ['bash', script_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = []
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
            output.append(f"\nExit code: {result.returncode}")

            return "\n".join(output) if output else "Script executed with no output."
        finally:
            # Clean up temporary file
            try:
                os.unlink(script_path)
            except:
                pass

    except subprocess.TimeoutExpired:
        return f"Error: Script timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing script: {e}"

# ============================================================================
# PHASE 1: Essential Tools
# ============================================================================

async def search_code(pattern: str, path: str = ".", file_pattern: str = "*", max_results: int = 50) -> str:
    """
    Searches for a pattern in files using grep-like functionality.
    Returns file paths, line numbers, and matching lines.
    """
    print(f"[Tool] Executing search_code with pattern: '{pattern}' in path: '{path}'")
    try:
        path_obj = Path(path).resolve()
        if not path_obj.exists():
            return f"Error: Path '{path}' does not exist."

        results = []
        count = 0
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build'}

        for root, dirs, files in os.walk(path_obj):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if count >= max_results:
                    results.append(f"\n... (truncated, showing first {max_results} matches)")
                    break

                file_path = Path(root) / file

                # Skip binary and sensitive files
                if file.endswith(('.pyc', '.so', '.dll', '.exe', '.jpg', '.png', '.gif', '.pdf')):
                    continue
                if '.env' in str(file_path) or '.key' in str(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                results.append(f"{file_path}:{line_num}: {line.strip()}")
                                count += 1
                                if count >= max_results:
                                    break
                except (UnicodeDecodeError, PermissionError):
                    continue

            if count >= max_results:
                break

        if not results:
            return f"No matches found for pattern '{pattern}' in {path}"

        return "\n".join(results)
    except Exception as e:
        return f"Error searching code: {e}"

async def edit_file(file_path: str, old_text: str, new_text: str) -> str:
    """
    Edits a file by replacing old_text with new_text.
    More efficient than rewriting entire file.
    """
    print(f"[Tool] Executing edit_file on: '{file_path}'")
    try:
        path_obj = Path(file_path).resolve()

        if not path_obj.exists():
            return f"Error: File '{file_path}' does not exist."

        # Security check
        sensitive_patterns = ['.env', '.git/', 'id_rsa', '.pem', '.key', 'credentials']
        if any(pattern in str(path_obj) for pattern in sensitive_patterns):
            return f"Error: Cannot edit potentially sensitive file '{file_path}'."

        # Read file
        with open(path_obj, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if old_text exists
        if old_text not in content:
            return f"Error: Text to replace not found in {file_path}"

        # Replace text
        new_content = content.replace(old_text, new_text, 1)  # Replace first occurrence

        # Write back
        with open(path_obj, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"Successfully edited {file_path}"
    except Exception as e:
        return f"Error editing file: {e}"

async def find_files(pattern: str, path: str = ".", max_results: int = 100) -> str:
    """
    Finds files matching a pattern (glob-style or regex).
    Returns list of matching file paths.
    """
    print(f"[Tool] Executing find_files with pattern: '{pattern}' in path: '{path}'")
    try:
        path_obj = Path(path).resolve()
        if not path_obj.exists():
            return f"Error: Path '{path}' does not exist."

        results = []
        count = 0
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build'}

        # Check if pattern is glob or regex
        is_glob = '*' in pattern or '?' in pattern

        for root, dirs, files in os.walk(path_obj):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if count >= max_results:
                    results.append(f"\n... (truncated, showing first {max_results} results)")
                    break

                if is_glob:
                    from fnmatch import fnmatch
                    if fnmatch(file, pattern):
                        results.append(str(Path(root) / file))
                        count += 1
                else:
                    if re.search(pattern, file):
                        results.append(str(Path(root) / file))
                        count += 1

            if count >= max_results:
                break

        if not results:
            return f"No files found matching pattern '{pattern}' in {path}"

        return "\n".join(results)
    except Exception as e:
        return f"Error finding files: {e}"

async def git_status(repo_path: str = ".") -> str:
    """
    Returns the git status of a repository.
    """
    print(f"[Tool] Executing git_status in: '{repo_path}'")
    try:
        result = subprocess.run(
            ['git', 'status'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Git status command timed out."
    except Exception as e:
        return f"Error executing git status: {e}"

async def git_diff(repo_path: str = ".", file_path: str = None) -> str:
    """
    Returns the git diff for the repository or a specific file.
    """
    print(f"[Tool] Executing git_diff in: '{repo_path}'")
    try:
        cmd = ['git', 'diff']
        if file_path:
            cmd.append(file_path)

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        if not result.stdout:
            return "No changes detected."

        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Git diff command timed out."
    except Exception as e:
        return f"Error executing git diff: {e}"

async def git_commit(message: str, repo_path: str = ".") -> str:
    """
    Creates a git commit with the specified message.
    """
    print(f"[Tool] Executing git_commit with message: '{message}'")
    try:
        # First check if there are staged changes
        status_result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=repo_path,
            capture_output=True,
            timeout=10
        )

        if status_result.returncode == 0:
            return "Error: No staged changes to commit. Use git_add first."

        result = subprocess.run(
            ['git', 'commit', '-m', message],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Git commit command timed out."
    except Exception as e:
        return f"Error executing git commit: {e}"

async def git_add(file_paths: str, repo_path: str = ".") -> str:
    """
    Stages files for commit. file_paths can be a single file or multiple files separated by spaces.
    """
    print(f"[Tool] Executing git_add for: '{file_paths}'")
    try:
        files = file_paths.split()
        cmd = ['git', 'add'] + files

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        return f"Successfully staged: {file_paths}"
    except subprocess.TimeoutExpired:
        return "Error: Git add command timed out."
    except Exception as e:
        return f"Error executing git add: {e}"

async def git_log(repo_path: str = ".", max_count: int = 10) -> str:
    """
    Returns the git log with recent commits.
    """
    print(f"[Tool] Executing git_log in: '{repo_path}'")
    try:
        result = subprocess.run(
            ['git', 'log', f'--max-count={max_count}', '--oneline', '--decorate'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Git log command timed out."
    except Exception as e:
        return f"Error executing git log: {e}"

async def git_branch(repo_path: str = ".", action: str = "list", branch_name: str = None) -> str:
    """
    Git branch operations: list, create, or switch branches.
    action: 'list', 'create', 'switch'
    """
    print(f"[Tool] Executing git_branch with action: '{action}'")
    try:
        if action == "list":
            cmd = ['git', 'branch', '-a']
        elif action == "create":
            if not branch_name:
                return "Error: branch_name required for create action."
            cmd = ['git', 'branch', branch_name]
        elif action == "switch":
            if not branch_name:
                return "Error: branch_name required for switch action."
            cmd = ['git', 'checkout', branch_name]
        else:
            return f"Error: Invalid action '{action}'. Use 'list', 'create', or 'switch'."

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        return result.stdout if result.stdout else f"Successfully executed git branch {action}"
    except subprocess.TimeoutExpired:
        return "Error: Git branch command timed out."
    except Exception as e:
        return f"Error executing git branch: {e}"

# ============================================================================
# PHASE 2: High Value Tools
# ============================================================================

async def search_and_replace(pattern: str, replacement: str, path: str = ".", file_pattern: str = "*", dry_run: bool = True) -> str:
    """
    Find and replace text across multiple files.
    dry_run=True shows what would be changed without actually changing it.
    """
    print(f"[Tool] Executing search_and_replace: '{pattern}' -> '{replacement}' (dry_run={dry_run})")
    try:
        path_obj = Path(path).resolve()
        if not path_obj.exists():
            return f"Error: Path '{path}' does not exist."

        results = []
        files_changed = 0
        total_replacements = 0
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build'}

        for root, dirs, files in os.walk(path_obj):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                file_path = Path(root) / file

                # Skip binary and sensitive files
                if file.endswith(('.pyc', '.so', '.dll', '.exe', '.jpg', '.png', '.gif', '.pdf')):
                    continue
                if '.env' in str(file_path) or '.key' in str(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check if pattern exists
                    matches = len(re.findall(pattern, content))
                    if matches > 0:
                        if dry_run:
                            results.append(f"{file_path}: {matches} match(es)")
                        else:
                            new_content = re.sub(pattern, replacement, content)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            results.append(f"{file_path}: {matches} replacement(s) made")

                        files_changed += 1
                        total_replacements += matches

                except (UnicodeDecodeError, PermissionError):
                    continue

        if not results:
            return f"No matches found for pattern '{pattern}'"

        summary = f"{'[DRY RUN] ' if dry_run else ''}Found {total_replacements} match(es) in {files_changed} file(s)\n\n"
        return summary + "\n".join(results)
    except Exception as e:
        return f"Error in search and replace: {e}"

async def copy_file(source: str, destination: str) -> str:
    """
    Copies a file or directory from source to destination.
    """
    print(f"[Tool] Executing copy_file: '{source}' -> '{destination}'")
    try:
        import shutil

        source_path = Path(source).resolve()
        dest_path = Path(destination).resolve()

        if not source_path.exists():
            return f"Error: Source '{source}' does not exist."

        # Security check
        sensitive_patterns = ['.env', '.git/', 'id_rsa', '.pem', '.key', 'credentials']
        if any(pattern in str(dest_path) for pattern in sensitive_patterns):
            return f"Error: Cannot copy to sensitive location '{destination}'."

        if source_path.is_dir():
            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
            return f"Successfully copied directory '{source}' to '{destination}'"
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            return f"Successfully copied file '{source}' to '{destination}'"
    except Exception as e:
        return f"Error copying file: {e}"

async def move_file(source: str, destination: str) -> str:
    """
    Moves/renames a file or directory from source to destination.
    """
    print(f"[Tool] Executing move_file: '{source}' -> '{destination}'")
    try:
        import shutil

        source_path = Path(source).resolve()
        dest_path = Path(destination).resolve()

        if not source_path.exists():
            return f"Error: Source '{source}' does not exist."

        # Security check
        sensitive_patterns = ['.env', '.git/', 'id_rsa', '.pem', '.key', 'credentials']
        if any(pattern in str(source_path) for pattern in sensitive_patterns):
            return f"Error: Cannot move sensitive file '{source}'."
        if any(pattern in str(dest_path) for pattern in sensitive_patterns):
            return f"Error: Cannot move to sensitive location '{destination}'."

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(dest_path))
        return f"Successfully moved '{source}' to '{destination}'"
    except Exception as e:
        return f"Error moving file: {e}"

async def delete_file(path: str, confirm: bool = False) -> str:
    """
    Deletes a file or directory. Requires confirm=True for safety.
    """
    print(f"[Tool] Executing delete_file on: '{path}'")
    try:
        if not confirm:
            return "Error: Must set confirm=True to delete files. This is a safety measure."

        import shutil

        path_obj = Path(path).resolve()

        if not path_obj.exists():
            return f"Error: Path '{path}' does not exist."

        # Security check - prevent deleting critical paths
        critical_patterns = ['.git', '.env', 'id_rsa', '.pem', '.key', 'credentials']
        if any(pattern in str(path_obj) for pattern in critical_patterns):
            return f"Error: Cannot delete sensitive path '{path}'."

        # Prevent deleting root-level directories
        if len(path_obj.parts) <= 2:
            return f"Error: Cannot delete root-level path '{path}' for safety."

        if path_obj.is_dir():
            shutil.rmtree(path_obj)
            return f"Successfully deleted directory '{path}'"
        else:
            path_obj.unlink()
            return f"Successfully deleted file '{path}'"
    except Exception as e:
        return f"Error deleting file: {e}"

async def install_package(package_name: str, package_manager: str = "auto") -> str:
    """
    Installs a package using npm, pip, or yarn.
    package_manager: 'npm', 'pip', 'yarn', or 'auto' (auto-detect)
    """
    print(f"[Tool] Executing install_package: '{package_name}' with {package_manager}")
    try:
        if package_manager == "auto":
            # Auto-detect based on project files
            if Path("package.json").exists():
                package_manager = "npm"
            elif Path("requirements.txt").exists() or Path("setup.py").exists():
                package_manager = "pip"
            else:
                return "Error: Could not auto-detect package manager. Please specify 'npm', 'pip', or 'yarn'."

        if package_manager == "npm":
            cmd = ['npm', 'install', package_name]
        elif package_manager == "pip":
            cmd = ['pip', 'install', package_name]
        elif package_manager == "yarn":
            cmd = ['yarn', 'add', package_name]
        else:
            return f"Error: Unsupported package manager '{package_manager}'"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes for package installation
        )

        if result.returncode != 0:
            return f"Error installing {package_name}:\n{result.stderr}"

        return f"Successfully installed {package_name}\n{result.stdout}"
    except subprocess.TimeoutExpired:
        return f"Error: Package installation timed out after 5 minutes."
    except Exception as e:
        return f"Error installing package: {e}"

async def run_tests(test_path: str = ".", framework: str = "auto") -> str:
    """
    Runs tests using pytest, jest, or other test frameworks.
    framework: 'pytest', 'jest', 'npm', or 'auto' (auto-detect)
    """
    print(f"[Tool] Executing run_tests in: '{test_path}' with framework: {framework}")
    try:
        if framework == "auto":
            # Auto-detect test framework
            if Path("package.json").exists():
                framework = "npm"
            elif Path("pytest.ini").exists() or Path("setup.py").exists():
                framework = "pytest"
            else:
                return "Error: Could not auto-detect test framework. Please specify 'pytest', 'jest', or 'npm'."

        if framework == "pytest":
            cmd = ['pytest', test_path, '-v']
        elif framework == "jest":
            cmd = ['jest', test_path]
        elif framework == "npm":
            cmd = ['npm', 'test']
        else:
            return f"Error: Unsupported test framework '{framework}'"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes for tests
        )

        output = []
        if result.stdout:
            output.append(result.stdout)
        if result.stderr:
            output.append(result.stderr)

        status = "PASSED" if result.returncode == 0 else "FAILED"
        output.append(f"\nTest Status: {status}")

        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return "Error: Tests timed out after 5 minutes."
    except Exception as e:
        return f"Error running tests: {e}"

async def http_request(url: str, method: str = "GET", headers: str = None, body: str = None) -> str:
    """
    Makes an HTTP request and returns the response.
    headers should be JSON string like '{"Content-Type": "application/json"}'
    """
    print(f"[Tool] Executing http_request: {method} {url}")
    try:
        import json
        try:
            import httpx
        except ImportError:
            return "Error: httpx library not installed. Install with: pip install httpx"

        headers_dict = {}
        if headers:
            headers_dict = json.loads(headers)

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers_dict)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers_dict, content=body)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers_dict, content=body)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers_dict)
            else:
                return f"Error: Unsupported HTTP method '{method}'"

            result = [
                f"Status: {response.status_code}",
                f"Headers: {dict(response.headers)}",
                f"\nBody:\n{response.text[:5000]}"  # Limit response size
            ]

            return "\n".join(result)
    except Exception as e:
        return f"Error making HTTP request: {e}"

# ============================================================================
# PHASE 3: Advanced Tools
# ============================================================================

async def lint_code(file_path: str = ".", linter: str = "auto") -> str:
    """
    Runs a code linter on files.
    linter: 'eslint', 'pylint', 'flake8', or 'auto' (auto-detect)
    """
    print(f"[Tool] Executing lint_code on: '{file_path}' with linter: {linter}")
    try:
        if linter == "auto":
            # Auto-detect based on project
            if Path("package.json").exists():
                linter = "eslint"
            elif Path("setup.py").exists() or file_path.endswith('.py'):
                linter = "pylint"
            else:
                return "Error: Could not auto-detect linter. Please specify 'eslint', 'pylint', or 'flake8'."

        if linter == "eslint":
            cmd = ['eslint', file_path]
        elif linter == "pylint":
            cmd = ['pylint', file_path]
        elif linter == "flake8":
            cmd = ['flake8', file_path]
        else:
            return f"Error: Unsupported linter '{linter}'"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = []
        if result.stdout:
            output.append(result.stdout)
        if result.stderr:
            output.append(result.stderr)

        if result.returncode == 0:
            return "No linting issues found!"

        return "\n".join(output) if output else "Linting completed with issues."
    except subprocess.TimeoutExpired:
        return "Error: Linting timed out after 60 seconds."
    except FileNotFoundError:
        return f"Error: {linter} is not installed or not in PATH."
    except Exception as e:
        return f"Error running linter: {e}"

async def format_code(file_path: str = ".", formatter: str = "auto") -> str:
    """
    Formats code using prettier, black, or other formatters.
    formatter: 'prettier', 'black', or 'auto' (auto-detect)
    """
    print(f"[Tool] Executing format_code on: '{file_path}' with formatter: {formatter}")
    try:
        if formatter == "auto":
            # Auto-detect based on file type
            if file_path.endswith(('.js', '.ts', '.jsx', '.tsx', '.json', '.html', '.css')):
                formatter = "prettier"
            elif file_path.endswith('.py'):
                formatter = "black"
            else:
                return "Error: Could not auto-detect formatter. Please specify 'prettier' or 'black'."

        if formatter == "prettier":
            cmd = ['prettier', '--write', file_path]
        elif formatter == "black":
            cmd = ['black', file_path]
        else:
            return f"Error: Unsupported formatter '{formatter}'"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return f"Error formatting code:\n{result.stderr}"

        return f"Successfully formatted {file_path}\n{result.stdout}"
    except subprocess.TimeoutExpired:
        return "Error: Formatting timed out after 60 seconds."
    except FileNotFoundError:
        return f"Error: {formatter} is not installed or not in PATH."
    except Exception as e:
        return f"Error formatting code: {e}"

async def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """
    Lists contents of a directory with details.
    """
    print(f"[Tool] Executing list_directory on: '{path}'")
    try:
        path_obj = Path(path).resolve()
        if not path_obj.exists():
            return f"Error: Path '{path}' does not exist."

        if not path_obj.is_dir():
            return f"Error: '{path}' is not a directory."

        items = []
        for item in sorted(path_obj.iterdir()):
            if not show_hidden and item.name.startswith('.'):
                continue

            item_type = "DIR" if item.is_dir() else "FILE"
            try:
                size = item.stat().st_size if item.is_file() else "-"
                items.append(f"{item_type:6} {size:>12} {item.name}")
            except:
                items.append(f"{item_type:6} {'?':>12} {item.name}")

        if not items:
            return f"Directory '{path}' is empty."

        header = f"Contents of {path}:\n{'TYPE':6} {'SIZE':>12} NAME\n" + "-" * 50
        return header + "\n" + "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {e}"

async def get_file_info(file_path: str) -> str:
    """
    Gets metadata about a file (size, modified date, permissions, line count).
    """
    print(f"[Tool] Executing get_file_info on: '{file_path}'")
    try:
        path_obj = Path(file_path).resolve()

        if not path_obj.exists():
            return f"Error: Path '{file_path}' does not exist."

        stat = path_obj.stat()
        info = [
            f"Path: {path_obj}",
            f"Type: {'Directory' if path_obj.is_dir() else 'File'}",
            f"Size: {stat.st_size} bytes",
            f"Modified: {stat.st_mtime}",
            f"Permissions: {oct(stat.st_mode)[-3:]}",
        ]

        if path_obj.is_file():
            try:
                with open(path_obj, 'r', encoding='utf-8') as f:
                    lines = sum(1 for _ in f)
                info.append(f"Lines: {lines}")
            except:
                pass

        return "\n".join(info)
    except Exception as e:
        return f"Error getting file info: {e}"

async def build_project(build_command: str = None) -> str:
    """
    Runs a build command for the project.
    If build_command is None, auto-detects based on project files.
    """
    print(f"[Tool] Executing build_project with command: '{build_command}'")
    try:
        if not build_command:
            # Auto-detect build command
            if Path("package.json").exists():
                build_command = "npm run build"
            elif Path("Makefile").exists():
                build_command = "make"
            elif Path("setup.py").exists():
                build_command = "python setup.py build"
            else:
                return "Error: Could not auto-detect build command. Please specify a build command."

        result = subprocess.run(
            build_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes for build
        )

        output = []
        if result.stdout:
            output.append(result.stdout[-5000:])  # Last 5000 chars
        if result.stderr:
            output.append(result.stderr[-5000:])

        status = "SUCCESS" if result.returncode == 0 else "FAILED"
        output.append(f"\nBuild Status: {status}")

        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return "Error: Build timed out after 10 minutes."
    except Exception as e:
        return f"Error building project: {e}"

# ============================================================================
# BROWSER AUTOMATION TOOLS (QA Testing)
# ============================================================================

# Global browser instance for reuse across tool calls
_browser_instance = None
_browser_page = None

async def _get_browser():
    """Get or create browser instance."""
    global _browser_instance, _browser_page

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None, "Error: Playwright not installed. Install with: pip install playwright && playwright install"

    if _browser_instance is None:
        playwright = await async_playwright().start()
        # Check environment variable for headless mode (defaults to True)
        headless = os.getenv('BROWSER_HEADLESS', 'true').lower() in ('true', '1', 'yes')
        _browser_instance = await playwright.chromium.launch(headless=headless)
        _browser_page = await _browser_instance.new_page()

    return _browser_page, None

async def browser_navigate(url: str, wait_until: str = "load") -> str:
    """
    Navigate browser to a URL.
    wait_until: 'load', 'domcontentloaded', 'networkidle'
    """
    print(f"[Tool] Executing browser_navigate to: '{url}'")
    try:
        page, error = await _get_browser()
        if error:
            return error

        await page.goto(url, wait_until=wait_until, timeout=30000)
        title = await page.title()

        return f"Successfully navigated to {url}\nPage title: {title}"
    except Exception as e:
        return f"Error navigating to {url}: {e}"

async def browser_screenshot(filename: str = "screenshot.png", full_page: bool = False) -> str:
    """
    Take a screenshot of the current page.
    """
    print(f"[Tool] Executing browser_screenshot to: '{filename}'")
    try:
        page, error = await _get_browser()
        if error:
            return error

        await page.screenshot(path=filename, full_page=full_page)

        return f"Screenshot saved to {filename}"
    except Exception as e:
        return f"Error taking screenshot: {e}"

async def browser_click(selector: str, timeout: int = 30) -> str:
    """
    Click an element on the page using CSS selector.
    """
    print(f"[Tool] Executing browser_click on: '{selector}'")
    try:
        page, error = await _get_browser()
        if error:
            return error

        await page.click(selector, timeout=timeout * 1000)

        return f"Successfully clicked element: {selector}"
    except Exception as e:
        return f"Error clicking {selector}: {e}"

async def browser_type(selector: str, text: str, timeout: int = 30) -> str:
    """
    Type text into an input field using CSS selector.
    """
    print(f"[Tool] Executing browser_type on: '{selector}'")
    try:
        page, error = await _get_browser()
        if error:
            return error

        await page.fill(selector, text, timeout=timeout * 1000)

        return f"Successfully typed text into: {selector}"
    except Exception as e:
        return f"Error typing into {selector}: {e}"

async def browser_get_text(selector: str, timeout: int = 30) -> str:
    """
    Get text content from an element using CSS selector.
    """
    print(f"[Tool] Executing browser_get_text from: '{selector}'")
    try:
        page, error = await _get_browser()
        if error:
            return error

        element = await page.wait_for_selector(selector, timeout=timeout * 1000)
        text = await element.text_content()

        return f"Text from {selector}: {text}"
    except Exception as e:
        return f"Error getting text from {selector}: {e}"

async def browser_evaluate(javascript_code: str) -> str:
    """
    Execute JavaScript code in the browser context.
    Returns the result as a string.
    """
    print(f"[Tool] Executing browser_evaluate")
    try:
        page, error = await _get_browser()
        if error:
            return error

        result = await page.evaluate(javascript_code)

        return f"JavaScript result: {json.dumps(result, indent=2)}"
    except Exception as e:
        return f"Error evaluating JavaScript: {e}"

async def browser_wait_for(selector: str, state: str = "visible", timeout: int = 30) -> str:
    """
    Wait for an element to reach a specific state.
    state: 'attached', 'detached', 'visible', 'hidden'
    """
    print(f"[Tool] Executing browser_wait_for: '{selector}' to be '{state}'")
    try:
        page, error = await _get_browser()
        if error:
            return error

        await page.wait_for_selector(selector, state=state, timeout=timeout * 1000)

        return f"Element {selector} is now {state}"
    except Exception as e:
        return f"Error waiting for {selector}: {e}"

async def browser_fill_form(form_data: str) -> str:
    """
    Fill multiple form fields at once.
    form_data should be a JSON string like: '{"#username": "user", "#password": "pass"}'
    """
    print(f"[Tool] Executing browser_fill_form")
    try:
        page, error = await _get_browser()
        if error:
            return error

        data = json.loads(form_data)
        results = []

        for selector, value in data.items():
            await page.fill(selector, value)
            results.append(f"{selector} = {value}")

        return f"Successfully filled form fields:\n" + "\n".join(results)
    except Exception as e:
        return f"Error filling form: {e}"

async def browser_get_url() -> str:
    """
    Get the current page URL.
    """
    print(f"[Tool] Executing browser_get_url")
    try:
        page, error = await _get_browser()
        if error:
            return error

        url = page.url

        return f"Current URL: {url}"
    except Exception as e:
        return f"Error getting URL: {e}"

async def browser_go_back() -> str:
    """
    Navigate back in browser history.
    """
    print(f"[Tool] Executing browser_go_back")
    try:
        page, error = await _get_browser()
        if error:
            return error

        await page.go_back()

        return f"Navigated back to: {page.url}"
    except Exception as e:
        return f"Error going back: {e}"

async def browser_close() -> str:
    """
    Close the browser instance.
    """
    print(f"[Tool] Executing browser_close")
    global _browser_instance, _browser_page

    try:
        if _browser_instance:
            await _browser_instance.close()
            _browser_instance = None
            _browser_page = None

        return "Browser closed successfully"
    except Exception as e:
        return f"Error closing browser: {e}"

# --- Tool Manifest ---
# This dictionary maps tool names to their implementation and definition for the LLM.

TOOLS = {
    "web_search": {
        "execute": web_search,
        # The definition must match the schema expected by the LLM provider.
        # This includes a 'type' and a nested 'function' object.
        "definition": {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Fetches real-time information from the internet using a search query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query to execute."},
                    },
                    "required": ["query"],
                },
            },
        },
    },
    "calculator": {
        "execute": calculator,
        "definition": {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Solves mathematical expressions and equations. Can handle advanced math.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "The mathematical expression to evaluate (e.g., 'sqrt(529)', '12 * 4')."},
                    },
                    "required": ["expression"],
                },
            },
        },
    },
    "explore_project": {
        "execute": explore_project,
        "definition": {
            "type": "function",
            "function": {
                "name": "explore_project",
                "description": "Explores and returns the directory structure of a project. Useful for understanding codebase organization.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The directory path to explore. Defaults to current directory '.'"},
                    },
                    "required": [],
                },
            },
        },
    },
    "read_file": {
        "execute": read_file,
        "definition": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Reads and returns the contents of a file. Cannot read sensitive files like .env or private keys.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "The path to the file to read."},
                        "max_lines": {"type": "integer", "description": "Maximum number of lines to read (default: 500)."},
                    },
                    "required": ["file_path"],
                },
            },
        },
    },
    "write_file": {
        "execute": write_file,
        "definition": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Writes content to a file. Creates new file or overwrites existing one. Creates parent directories if needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "The path to the file to write."},
                        "content": {"type": "string", "description": "The content to write to the file."},
                    },
                    "required": ["file_path", "content"],
                },
            },
        },
    },
    "bash_command": {
        "execute": bash_command,
        "definition": {
            "type": "function",
            "function": {
                "name": "bash_command",
                "description": "Executes a bash command and returns the output. Has security restrictions to prevent dangerous operations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The bash command to execute."},
                        "timeout": {"type": "integer", "description": "Maximum execution time in seconds (default: 30)."},
                    },
                    "required": ["command"],
                },
            },
        },
    },
    "bash_script": {
        "execute": bash_script,
        "definition": {
            "type": "function",
            "function": {
                "name": "bash_script",
                "description": "Executes a multi-line bash script and returns the output. Script is written to temp file and executed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_content": {"type": "string", "description": "The bash script content to execute."},
                        "timeout": {"type": "integer", "description": "Maximum execution time in seconds (default: 60)."},
                    },
                    "required": ["script_content"],
                },
            },
        },
    },
    # === Phase 1 Tools ===
    "search_code": {
        "execute": search_code,
        "definition": {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": "Searches for a pattern across files using regex. Returns file paths, line numbers, and matching lines.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "The regex pattern to search for."},
                        "path": {"type": "string", "description": "The directory to search in (default: '.')."},
                        "file_pattern": {"type": "string", "description": "File pattern to filter (default: '*')."},
                        "max_results": {"type": "integer", "description": "Maximum number of matches to return (default: 50)."},
                    },
                    "required": ["pattern"],
                },
            },
        },
    },
    "edit_file": {
        "execute": edit_file,
        "definition": {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Edits a file by replacing old_text with new_text. More efficient than rewriting entire file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "The path to the file to edit."},
                        "old_text": {"type": "string", "description": "The text to be replaced."},
                        "new_text": {"type": "string", "description": "The replacement text."},
                    },
                    "required": ["file_path", "old_text", "new_text"],
                },
            },
        },
    },
    "find_files": {
        "execute": find_files,
        "definition": {
            "type": "function",
            "function": {
                "name": "find_files",
                "description": "Finds files matching a pattern (glob or regex). Returns list of matching file paths.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "The pattern to match (glob like '*.py' or regex)."},
                        "path": {"type": "string", "description": "The directory to search in (default: '.')."},
                        "max_results": {"type": "integer", "description": "Maximum number of results (default: 100)."},
                    },
                    "required": ["pattern"],
                },
            },
        },
    },
    "git_status": {
        "execute": git_status,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Returns the git status of a repository showing staged/unstaged changes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Path to the git repository (default: '.')."},
                    },
                    "required": [],
                },
            },
        },
    },
    "git_diff": {
        "execute": git_diff,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_diff",
                "description": "Shows git diff for repository or specific file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Path to the git repository (default: '.')."},
                        "file_path": {"type": "string", "description": "Specific file to diff (optional)."},
                    },
                    "required": [],
                },
            },
        },
    },
    "git_commit": {
        "execute": git_commit,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_commit",
                "description": "Creates a git commit with the specified message. Requires staged changes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "The commit message."},
                        "repo_path": {"type": "string", "description": "Path to the git repository (default: '.')."},
                    },
                    "required": ["message"],
                },
            },
        },
    },
    "git_add": {
        "execute": git_add,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_add",
                "description": "Stages files for commit. Can stage multiple files separated by spaces.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_paths": {"type": "string", "description": "File paths to stage, space-separated."},
                        "repo_path": {"type": "string", "description": "Path to the git repository (default: '.')."},
                    },
                    "required": ["file_paths"],
                },
            },
        },
    },
    "git_log": {
        "execute": git_log,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_log",
                "description": "Shows git commit history.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Path to the git repository (default: '.')."},
                        "max_count": {"type": "integer", "description": "Maximum number of commits to show (default: 10)."},
                    },
                    "required": [],
                },
            },
        },
    },
    "git_branch": {
        "execute": git_branch,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_branch",
                "description": "Git branch operations: list, create, or switch branches.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Path to the git repository (default: '.')."},
                        "action": {"type": "string", "description": "Action to perform: 'list', 'create', or 'switch' (default: 'list')."},
                        "branch_name": {"type": "string", "description": "Branch name for create/switch actions."},
                    },
                    "required": [],
                },
            },
        },
    },
    # === Phase 2 Tools ===
    "search_and_replace": {
        "execute": search_and_replace,
        "definition": {
            "type": "function",
            "function": {
                "name": "search_and_replace",
                "description": "Find and replace text across multiple files using regex. Supports dry-run mode.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "The regex pattern to search for."},
                        "replacement": {"type": "string", "description": "The replacement text."},
                        "path": {"type": "string", "description": "Directory to search in (default: '.')."},
                        "file_pattern": {"type": "string", "description": "File pattern filter (default: '*')."},
                        "dry_run": {"type": "boolean", "description": "If true, shows what would change without making changes (default: true)."},
                    },
                    "required": ["pattern", "replacement"],
                },
            },
        },
    },
    "copy_file": {
        "execute": copy_file,
        "definition": {
            "type": "function",
            "function": {
                "name": "copy_file",
                "description": "Copies a file or directory from source to destination.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source file or directory path."},
                        "destination": {"type": "string", "description": "Destination path."},
                    },
                    "required": ["source", "destination"],
                },
            },
        },
    },
    "move_file": {
        "execute": move_file,
        "definition": {
            "type": "function",
            "function": {
                "name": "move_file",
                "description": "Moves or renames a file or directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source file or directory path."},
                        "destination": {"type": "string", "description": "Destination path."},
                    },
                    "required": ["source", "destination"],
                },
            },
        },
    },
    "delete_file": {
        "execute": delete_file,
        "definition": {
            "type": "function",
            "function": {
                "name": "delete_file",
                "description": "Deletes a file or directory. Requires confirm=True for safety.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to delete."},
                        "confirm": {"type": "boolean", "description": "Must be true to confirm deletion (safety measure)."},
                    },
                    "required": ["path", "confirm"],
                },
            },
        },
    },
    "install_package": {
        "execute": install_package,
        "definition": {
            "type": "function",
            "function": {
                "name": "install_package",
                "description": "Installs a package using npm, pip, or yarn. Auto-detects package manager.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "package_name": {"type": "string", "description": "Name of the package to install."},
                        "package_manager": {"type": "string", "description": "Package manager: 'npm', 'pip', 'yarn', or 'auto' (default: 'auto')."},
                    },
                    "required": ["package_name"],
                },
            },
        },
    },
    "run_tests": {
        "execute": run_tests,
        "definition": {
            "type": "function",
            "function": {
                "name": "run_tests",
                "description": "Runs tests using pytest, jest, or npm test. Auto-detects test framework.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test_path": {"type": "string", "description": "Path to tests (default: '.')."},
                        "framework": {"type": "string", "description": "Test framework: 'pytest', 'jest', 'npm', or 'auto' (default: 'auto')."},
                    },
                    "required": [],
                },
            },
        },
    },
    "http_request": {
        "execute": http_request,
        "definition": {
            "type": "function",
            "function": {
                "name": "http_request",
                "description": "Makes an HTTP request and returns the response. Supports GET, POST, PUT, DELETE.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to request."},
                        "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE (default: 'GET')."},
                        "headers": {"type": "string", "description": "JSON string of headers, e.g. '{\"Content-Type\": \"application/json\"}' (optional)."},
                        "body": {"type": "string", "description": "Request body for POST/PUT (optional)."},
                    },
                    "required": ["url"],
                },
            },
        },
    },
    # === Phase 3 Tools ===
    "lint_code": {
        "execute": lint_code,
        "definition": {
            "type": "function",
            "function": {
                "name": "lint_code",
                "description": "Runs a code linter (eslint, pylint, flake8). Auto-detects linter based on project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file or directory to lint (default: '.')."},
                        "linter": {"type": "string", "description": "Linter to use: 'eslint', 'pylint', 'flake8', or 'auto' (default: 'auto')."},
                    },
                    "required": [],
                },
            },
        },
    },
    "format_code": {
        "execute": format_code,
        "definition": {
            "type": "function",
            "function": {
                "name": "format_code",
                "description": "Formats code using prettier or black. Auto-detects formatter based on file type.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to file to format (default: '.')."},
                        "formatter": {"type": "string", "description": "Formatter: 'prettier', 'black', or 'auto' (default: 'auto')."},
                    },
                    "required": [],
                },
            },
        },
    },
    "list_directory": {
        "execute": list_directory,
        "definition": {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "Lists contents of a directory with file sizes and types.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path (default: '.')."},
                        "show_hidden": {"type": "boolean", "description": "Show hidden files (default: false)."},
                    },
                    "required": [],
                },
            },
        },
    },
    "get_file_info": {
        "execute": get_file_info,
        "definition": {
            "type": "function",
            "function": {
                "name": "get_file_info",
                "description": "Gets metadata about a file: size, modified date, permissions, line count.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file."},
                    },
                    "required": ["file_path"],
                },
            },
        },
    },
    "build_project": {
        "execute": build_project,
        "definition": {
            "type": "function",
            "function": {
                "name": "build_project",
                "description": "Runs a build command for the project. Auto-detects build command if not specified.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "build_command": {"type": "string", "description": "Build command to run (optional, auto-detects)."},
                    },
                    "required": [],
                },
            },
        },
    },
    # === Browser Automation Tools ===
    "browser_navigate": {
        "execute": browser_navigate,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_navigate",
                "description": "Navigate browser to a URL for testing web applications.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to navigate to."},
                        "wait_until": {"type": "string", "description": "When to consider navigation complete: 'load', 'domcontentloaded', 'networkidle' (default: 'load')."},
                    },
                    "required": ["url"],
                },
            },
        },
    },
    "browser_screenshot": {
        "execute": browser_screenshot,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_screenshot",
                "description": "Take a screenshot of the current browser page.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Filename for the screenshot (default: 'screenshot.png')."},
                        "full_page": {"type": "boolean", "description": "Capture full scrollable page (default: false)."},
                    },
                    "required": [],
                },
            },
        },
    },
    "browser_click": {
        "execute": browser_click,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_click",
                "description": "Click an element on the page using CSS selector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector for the element to click (e.g., '#button-id', '.class-name')."},
                        "timeout": {"type": "integer", "description": "Maximum wait time in seconds (default: 30)."},
                    },
                    "required": ["selector"],
                },
            },
        },
    },
    "browser_type": {
        "execute": browser_type,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_type",
                "description": "Type text into an input field using CSS selector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector for the input field."},
                        "text": {"type": "string", "description": "Text to type into the field."},
                        "timeout": {"type": "integer", "description": "Maximum wait time in seconds (default: 30)."},
                    },
                    "required": ["selector", "text"],
                },
            },
        },
    },
    "browser_get_text": {
        "execute": browser_get_text,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_get_text",
                "description": "Get text content from an element using CSS selector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector for the element."},
                        "timeout": {"type": "integer", "description": "Maximum wait time in seconds (default: 30)."},
                    },
                    "required": ["selector"],
                },
            },
        },
    },
    "browser_evaluate": {
        "execute": browser_evaluate,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_evaluate",
                "description": "Execute JavaScript code in the browser context and return the result.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "javascript_code": {"type": "string", "description": "JavaScript code to execute in the browser."},
                    },
                    "required": ["javascript_code"],
                },
            },
        },
    },
    "browser_wait_for": {
        "execute": browser_wait_for,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_wait_for",
                "description": "Wait for an element to reach a specific state.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector for the element."},
                        "state": {"type": "string", "description": "State to wait for: 'attached', 'detached', 'visible', 'hidden' (default: 'visible')."},
                        "timeout": {"type": "integer", "description": "Maximum wait time in seconds (default: 30)."},
                    },
                    "required": ["selector"],
                },
            },
        },
    },
    "browser_fill_form": {
        "execute": browser_fill_form,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_fill_form",
                "description": "Fill multiple form fields at once using a JSON mapping of selectors to values.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "form_data": {"type": "string", "description": "JSON string mapping CSS selectors to values, e.g. '{\"#username\": \"user\", \"#password\": \"pass\"}'."},
                    },
                    "required": ["form_data"],
                },
            },
        },
    },
    "browser_get_url": {
        "execute": browser_get_url,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_get_url",
                "description": "Get the current page URL.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    },
    "browser_go_back": {
        "execute": browser_go_back,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_go_back",
                "description": "Navigate back in browser history.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    },
    "browser_close": {
        "execute": browser_close,
        "definition": {
            "type": "function",
            "function": {
                "name": "browser_close",
                "description": "Close the browser instance and free resources.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    },
}

def get_filtered_tools(allowed_tools: list[str] | None = None) -> dict:
    """
    Returns a dictionary of tools, filtered by an allowed list.
    If no list is provided, all tools are returned.
    """
    if allowed_tools is None:
        return TOOLS
    
    return {name: tool for name, tool in TOOLS.items() if name in allowed_tools}

def get_tool_definitions(tools: dict) -> list[dict]:
    """
    Returns the LLM-compatible definitions for a given dictionary of tools.
    """
    return [tool["definition"] for tool in tools.values()]