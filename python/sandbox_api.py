import httpx
import os

SANDBOX_API_URL = os.getenv("SANDBOX_API_URL", "http://127.0.0.1:5000")


async def run(command: str, timeout: int = 30) -> str:
    """
    Runs a shell command in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SANDBOX_API_URL}/run",
                json={"command": command},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            output = []
            if "stdout" in data and data["stdout"]:
                output.append(f"STDOUT:\n{data['stdout']}")
            if "stderr" in data and data["stderr"]:
                output.append(f"STDERR:\n{data['stderr']}")

            if "returncode" in data:
                 output.append(f"\nExit code: {data['returncode']}")

            return "\n".join(output) if output else "Command executed with no output."

        except httpx.TimeoutException:
            return f"Error: Command timed out after {timeout} seconds."
        except httpx.HTTPStatusError as e:
            return f"Error running command: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error running command: {e}"


async def create_file(path: str, content: str) -> str:
    """
    Creates a file in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SANDBOX_API_URL}/files",
                json={"path": path, "content": content},
            )
            response.raise_for_status()
            return response.json().get("message", "File created successfully.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                return "Error: File already exists."
            return f"Error creating file: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error creating file: {e}"


async def read_file(path: str) -> str:
    """
    Reads a file from the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SANDBOX_API_URL}/files",
                params={"path": path},
            )
            response.raise_for_status()
            return response.json().get("content", "")
        except httpx.HTTPStatusError as e:
            return f"Error reading file: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error reading file: {e}"


async def update_file(path: str, content: str) -> str:
    """
    Updates a file in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"{SANDBOX_API_URL}/files",
                json={"path": path, "content": content},
            )
            response.raise_for_status()
            return response.json().get("message", "File updated successfully.")
        except httpx.HTTPStatusError as e:
            return f"Error updating file: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error updating file: {e}"


async def delete_file(path: str) -> str:
    """
    Deletes a file from the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{SANDBOX_API_URL}/files",
                params={"path": path},
            )
            response.raise_for_status()
            return response.json().get("message", "File deleted successfully.")
        except httpx.HTTPStatusError as e:
            return f"Error deleting file: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error deleting file: {e}"


async def create_directory(path: str) -> str:
    """
    Creates a directory in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SANDBOX_API_URL}/directories",
                json={"path": path},
            )
            response.raise_for_status()
            return response.json().get("message", "Directory created successfully.")
        except httpx.HTTPStatusError as e:
            return f"Error creating directory: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error creating directory: {e}"


from typing import List, Dict, Union

async def list_directory(path: str) -> Union[List[Dict[str, str]], str]:
    """
    Lists a directory from the sandbox.
    Returns a list of dictionaries, each representing a file or directory,
    or an error string.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SANDBOX_API_URL}/directories",
                params={"path": path},
            )
            response.raise_for_status()
            files_str_list = response.json().get("files", [])

            parsed_files = []
            for file_str in files_str_list:
                parts = file_str.split(maxsplit=2)
                if len(parts) == 3:
                    item_type, item_size, item_name = parts
                    parsed_files.append({"type": item_type, "size": item_size, "name": item_name})
            return parsed_files

        except httpx.HTTPStatusError as e:
            return f"Error listing directory: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error listing directory: {e}"


async def git_clone(repo_url: str) -> str:
    """
    Clones a git repository into the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SANDBOX_API_URL}/git/clone",
                json={"repo_url": repo_url},
            )
            response.raise_for_status()
            return response.json().get("message", "Repository cloned successfully.")
        except httpx.HTTPStatusError as e:
            return f"Error cloning repository: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error cloning repository: {e}"


async def git_status() -> str:
    """
    Gets the git status of the repository in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{SANDBOX_API_URL}/git/status")
            response.raise_for_status()
            return response.json().get("status", "")
        except httpx.HTTPStatusError as e:
            return f"Error getting git status: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error getting git status: {e}"


async def git_branch(branch_name: str = None) -> str:
    """
    Creates a new branch in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SANDBOX_API_URL}/git/branch",
                json={"branch": branch_name} if branch_name else {},
            )
            response.raise_for_status()
            return response.json().get("message", "Branch operation successful.")
        except httpx.HTTPStatusError as e:
            return f"Error with git branch: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error with git branch: {e}"


async def git_checkout(branch_name: str) -> str:
    """
    Checks out a branch in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SANDBOX_API_URL}/git/checkout",
                json={"branch": branch_name},
            )
            response.raise_for_status()
            return response.json().get("message", "Checkout successful.")
        except httpx.HTTPStatusError as e:
            return f"Error checking out branch: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error checking out branch: {e}"


async def git_add(files: list[str]) -> str:
    """
    Adds files to the git index in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SANDBOX_API_URL}/git/add",
                json={"files": files},
            )
            response.raise_for_status()
            return response.json().get("message", "Files added successfully.")
        except httpx.HTTPStatusError as e:
            return f"Error adding files to git: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error adding files to git: {e}"


async def git_commit(message: str) -> str:
    """
    Commits files in the sandbox.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SANDBOX_API_URL}/git/commit",
                json={"message": message},
            )
            response.raise_for_status()
            return response.json().get("message", "Commit successful.")
        except httpx.HTTPStatusError as e:
            return f"Error committing files: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return f"Error committing files: {e}"
