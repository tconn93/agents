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
from . import sandbox_api

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


async def read_file(file_path: str, max_lines: int = 500) -> str:
    """
    Reads and returns the contents of a file from the sandbox.
    """
    print(f"[Tool] Executing read_file on: '{file_path}'")
    content = await sandbox_api.read_file(file_path)

    if content.startswith("Error"):
        return content

    lines = content.splitlines(True) # keepends=True
    if len(lines) > max_lines:
        content = "".join(lines[:max_lines])
        content += f"\n\n... (truncated, showing first {max_lines} lines of {len(lines)} total)"

    return f"Contents of {file_path}:\n\n{content}"

async def write_file(file_path: str, content: str) -> str:
    """
    Writes content to a file in the sandbox. Creates the file if it doesn't exist, overwrites if it does.
    """
    print(f"[Tool] Executing write_file to: '{file_path}'")

    # First, try to create the file.
    create_response = await sandbox_api.create_file(file_path, content)

    # If the file already exists, the API might return an error.
    # In that case, we can try to update it.
    if create_response == "Error: File already exists.":
        print(f"[Tool] File '{file_path}' already exists. Attempting to update.")
        update_response = await sandbox_api.update_file(file_path, content)
        return update_response

    return create_response

async def bash_command(command: str, timeout: int = 30) -> str:
    """
    Executes a bash command in the sandbox and returns the output.
    """
    print(f"[Tool] Executing bash_command: '{command}'")
    return await sandbox_api.run(command, timeout)

async def bash_script(script_content: str, timeout: int = 60) -> str:
    """
    Executes a bash script provided as a string in the sandbox and returns the output.
    """
    print(f"[Tool] Executing bash_script")
    # The sandbox API's /run endpoint can handle multi-line scripts directly.
    return await sandbox_api.run(script_content, timeout)

# ============================================================================
# ============================================================================
# PHASE 1: Essential Tools
# ============================================================================

async def explore_project(path: str = ".") -> str:
    """
    Explores a project directory structure and returns a tree-like representation.
    Lists directories and files up to a reasonable depth.
    Note: This tool can be slow on large directories due to recursive API calls.
    """
    print(f"[Tool] Executing explore_project on path: '{path}'")

    async def _explore_recursive(current_path, indent=""):
        # List the contents of the current directory
        contents = await sandbox_api.list_directory(current_path)
        if isinstance(contents, str): # Error handling
            return [f"{indent}Error listing {current_path}: {contents}"]

        tree = []

        for item in contents:
            item_name = item['name']
            item_type = item['type']
            full_path = os.path.join(current_path, item_name)

            if item_type == "DIR":
                tree.append(f"{indent}{item_name}/")
                # Recursively explore subdirectories
                tree.extend(await _explore_recursive(full_path, indent + "  "))
            else: # FILE
                tree.append(f"{indent}{item_name}")

        return tree

    # Start the recursive exploration from the given path
    result_tree = await _explore_recursive(path)
    return f"Directory structure of: {path}\n" + "\n".join(result_tree)

async def search_code(pattern: str, path: str = ".", file_pattern: str = "*", max_results: int = 50) -> str:
    """
    Searches for a pattern in files using grep-like functionality.
    Returns file paths, line numbers, and matching lines.
    Note: This tool can be slow on large directories as it reads files one by one.
    """
    print(f"[Tool] Executing search_code with pattern: '{pattern}' in path: '{path}'")

    # Use the find_files tool to get a list of files to search
    files_str = await find_files(file_pattern, path)
    if files_str.startswith("No files found"):
        return "No files to search."

    files = files_str.splitlines()

    results = []
    count = 0

    for file_path in files:
        if count >= max_results:
            break

        content = await sandbox_api.read_file(file_path)
        if content.startswith("Error"):
            continue

        for line_num, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line, re.IGNORECASE):
                results.append(f"{file_path}:{line_num}: {line.strip()}")
                count += 1
                if count >= max_results:
                    break

    if not results:
        return f"No matches found for pattern '{pattern}' in {path}"

    return "\n".join(results)

async def edit_file(file_path: str, old_text: str, new_text: str) -> str:
    """
    Edits a file by replacing old_text with new_text.
    More efficient than rewriting entire file.
    """
    print(f"[Tool] Executing edit_file on: '{file_path}'")

    # Read the file content
    content = await sandbox_api.read_file(file_path)
    if content.startswith("Error"):
        return content

    # Check if old_text exists
    if old_text not in content:
        return f"Error: Text to replace not found in {file_path}"

    # Replace text
    new_content = content.replace(old_text, new_text, 1)  # Replace first occurrence

    # Write back the updated content
    return await sandbox_api.update_file(file_path, new_content)

async def search_and_replace(file_path: str, search_pattern: str, replace_text: str, is_regex: bool = False) -> str:
    """
    Searches for a pattern in a file and replaces all occurrences.
    """
    print(f"[Tool] Executing search_and_replace on: '{file_path}'")

    content = await sandbox_api.read_file(file_path)
    if content.startswith("Error"):
        return content

    if is_regex:
        new_content, count = re.subn(search_pattern, replace_text, content)
    else:
        count = content.count(search_pattern)
        new_content = content.replace(search_pattern, replace_text)

    if count == 0:
        return f"Pattern not found in {file_path}."

    result = await sandbox_api.update_file(file_path, new_content)
    if result.startswith("Error"):
        return result

    return f"Replaced {count} occurrences in {file_path}."

async def copy_file(source_path: str, destination_path: str) -> str:
    """
    Copies a file from a source path to a destination path.
    """
    print(f"[Tool] Executing copy_file from '{source_path}' to '{destination_path}'")

    content = await sandbox_api.read_file(source_path)
    if content.startswith("Error"):
        return content

    result = await sandbox_api.create_file(destination_path, content)
    return result

async def move_file(source_path: str, destination_path: str) -> str:
    """
    Moves a file from a source path to a destination path.
    """
    print(f"[Tool] Executing move_file from '{source_path}' to '{destination_path}'")

    # Implemented as copy-then-delete as the API lacks a rename/move endpoint.
    copy_result = await copy_file(source_path, destination_path)
    if copy_result.startswith("Error"):
        return f"Error during move (copy step): {copy_result}"

    delete_result = await sandbox_api.delete_file(source_path)
    if delete_result.startswith("Error"):
        return f"Warning: File copied to '{destination_path}' but failed to delete original at '{source_path}': {delete_result}"

    return f"File successfully moved from '{source_path}' to '{destination_path}'."

async def find_files(pattern: str, path: str = ".", max_results: int = 100) -> str:
    """
    Finds files matching a pattern (glob-style or regex).
    Returns list of matching file paths.
    Note: This tool can be slow on large directories due to recursive API calls.
    """
    print(f"[Tool] Executing find_files with pattern: '{pattern}' in path: '{path}'")

    all_files = []
    async def _find_recursive(current_path):
        contents = await sandbox_api.list_directory(current_path)
        if isinstance(contents, str): # Error handling
            return

        for item in contents:
            item_name = item['name']
            item_type = item['type']
            full_path = os.path.join(current_path, item_name)

            if item_type == "DIR":
                await _find_recursive(full_path)
            else: # FILE
                all_files.append(full_path)

    await _find_recursive(path)

    # Now filter the collected files
    results = []
    count = 0
    is_glob = '*' in pattern or '?' in pattern

    for file_path in all_files:
        if count >= max_results:
            break

        file_name = os.path.basename(file_path)

        if is_glob:
            from fnmatch import fnmatch
            if fnmatch(file_name, pattern):
                results.append(file_path)
                count += 1
        else:
            if re.search(pattern, file_name):
                results.append(file_path)
                count += 1

    if not results:
        return f"No files found matching pattern '{pattern}' in {path}"

    return "\n".join(results)


# ============================================================================
# PHASE 2: High Value Tools
# ============================================================================

async def git_status() -> str:
    """
    Returns the git status of a repository.
    """
    print(f"[Tool] Executing git_status")
    return await sandbox_api.git_status()

async def git_commit(message: str) -> str:
    """
    Creates a git commit with the specified message.
    """
    print(f"[Tool] Executing git_commit with message: '{message}'")
    return await sandbox_api.git_commit(message)

async def git_add(file_paths: str) -> str:
    """
    Stages files for commit. file_paths can be a single file or multiple files separated by spaces.
    """
    print(f"[Tool] Executing git_add for: '{file_paths}'")
    files = file_paths.split()
    return await sandbox_api.git_add(files)

async def git_branch(action: str = "list", branch_name: str = None) -> str:
    """
    Git branch operations: list, create, or switch branches.
    action: 'list', 'create', 'switch'
    """
    print(f"[Tool] Executing git_branch with action: '{action}'")
    if action == "switch":
        return await sandbox_api.git_checkout(branch_name)
    elif action == "create":
        return await sandbox_api.git_branch(branch_name)
    else: # list
        return await sandbox_api.git_branch()

async def git_diff(cached: bool = False) -> str:
    """
    Shows git diff. Use cached=True for staged changes.
    """
    print(f"[Tool] Executing git_diff with cached={cached}")
    command = "git diff"
    if cached:
        command += " --cached"
    return await sandbox_api.run(command)

async def git_log(max_count: int = 10) -> str:
    """
    Shows git log.
    """
    print(f"[Tool] Executing git_log with max_count={max_count}")
    command = f"git log -n {max_count} --oneline"
    return await sandbox_api.run(command)

async def delete_file(path: str, confirm: bool = False) -> str:
    """
    Deletes a file or directory from the sandbox. Requires confirm=True for safety.
    """
    print(f"[Tool] Executing delete_file on: '{path}'")
    if not confirm:
        return "Error: Must set confirm=True to delete files. This is a safety measure."
    return await sandbox_api.delete_file(path)

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

async def list_directory(path: str = ".") -> str:
    """
    Lists contents of a directory in the sandbox.
    """
    print(f"[Tool] Executing list_directory on: '{path}'")

    contents = await sandbox_api.list_directory(path)

    if isinstance(contents, str): # Error handling
        return contents

    if not contents:
        return f"Directory '{path}' is empty."

    # Format the output string from the structured data
    output_lines = [f"{item['type']:<5} {item['size']:>10} {item['name']}" for item in contents]

    header = f"Contents of {path}:\n" + "-" * 50
    return header + "\n" + "\n".join(output_lines)

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
    "copy_file": {
        "execute": copy_file,
        "definition": {
            "type": "function",
            "function": {
                "name": "copy_file",
                "description": "Copies a file from a source path to a destination path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_path": {"type": "string", "description": "The path of the file to copy."},
                        "destination_path": {"type": "string", "description": "The path to copy the file to."},
                    },
                    "required": ["source_path", "destination_path"],
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
                "description": "Moves a file from a source path to a destination path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_path": {"type": "string", "description": "The path of the file to move."},
                        "destination_path": {"type": "string", "description": "The path to move the file to."},
                    },
                    "required": ["source_path", "destination_path"],
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
    "search_and_replace": {
        "execute": search_and_replace,
        "definition": {
            "type": "function",
            "function": {
                "name": "search_and_replace",
                "description": "Searches for a pattern in a file and replaces all occurrences.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "The path to the file to edit."},
                        "search_pattern": {"type": "string", "description": "The text or regex pattern to search for."},
                        "replace_text": {"type": "string", "description": "The text to replace the search pattern with."},
                        "is_regex": {"type": "boolean", "description": "Whether the search pattern is a regex (default: false)."},
                    },
                    "required": ["file_path", "search_pattern", "replace_text"],
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
    # === Phase 2 Tools ===
    "git_status": {
        "execute": git_status,
        "definition": {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Returns the git status of a repository showing staged/unstaged changes.",
                "parameters": {
                    "type": "object",
                    "properties": {},
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
                    },
                    "required": ["file_paths"],
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
                "description": "Shows git diff. Use cached=True for staged changes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cached": {"type": "boolean", "description": "Whether to show staged changes (default: false)."},
                    },
                    "required": [],
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
                "description": "Shows git log.",
                "parameters": {
                    "type": "object",
                    "properties": {
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
                        "action": {"type": "string", "description": "Action to perform: 'list', 'create', or 'switch' (default: 'list')."},
                        "branch_name": {"type": "string", "description": "Branch name for create/switch actions."},
                    },
                    "required": [],
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