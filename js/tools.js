/**
 * This file defines the tools that the LLM agent can use.
 * Each tool has a `definition` for the LLM and an `execute` function for the agent.
 */

import { evaluate } from 'mathjs';
import fs from 'fs';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import os from 'os';

const execAsync = promisify(exec);

/**
 * A mock web search tool. In a real application, this would call a search API.
 * @param {string} query The search query.
 * @returns {Promise<string>} A mock search result.
 */
async function web_search(query) {
    console.log(`[Tool] Executing web_search with query: "${query}"`);
    // In a real implementation, you would use an API like Google Search, Brave, etc.
    if (query.toLowerCase().includes("weather in london")) {
        return "The weather in London is cloudy with a high of 15°C.";
    }
    return `Search results for "${query}" are not available in this mock implementation.`;
}

/**
 * A calculator tool using the mathjs library.
 * @param {string} expression The mathematical expression to evaluate.
 * @returns {Promise<string>} The result of the calculation.
 */
async function calculator(expression) {
    console.log(`[Tool] Executing calculator with expression: "${expression}"`);
    try {
        const result = evaluate(expression);
        return result.toString();
    } catch (e) {
        return `Error evaluating expression: ${e.message}`;
    }
}

/**
 * Explores a project directory structure and returns a tree-like representation.
 * @param {string} dirPath The directory path to explore.
 * @returns {Promise<string>} The directory structure.
 */
async function explore_project(dirPath = ".") {
    console.log(`[Tool] Executing explore_project on path: "${dirPath}"`);
    try {
        const resolvedPath = path.resolve(dirPath);

        if (!fs.existsSync(resolvedPath)) {
            return `Error: Path '${dirPath}' does not exist.`;
        }

        if (!fs.statSync(resolvedPath).isDirectory()) {
            return `Error: Path '${dirPath}' is not a directory.`;
        }

        const result = [`Directory structure of: ${resolvedPath}\n`];
        const maxItems = 100;
        let count = 0;

        const ignoreDirs = new Set(['.git', '__pycache__', 'node_modules', '.venv', 'venv', '.env', 'dist', 'build']);

        function walkDir(currentPath, level = 0) {
            if (count >= maxItems) return;

            const items = fs.readdirSync(currentPath);
            const indent = '  '.repeat(level);

            for (const item of items) {
                if (count >= maxItems) {
                    result.push(`\n... (truncated, showing first ${maxItems} items)`);
                    return;
                }

                const fullPath = path.join(currentPath, item);
                const stats = fs.statSync(fullPath);

                if (stats.isDirectory()) {
                    if (ignoreDirs.has(item)) continue;
                    result.push(`${indent}${item}/`);
                    count++;
                    walkDir(fullPath, level + 1);
                } else {
                    result.push(`${indent}${item}`);
                    count++;
                }
            }
        }

        walkDir(resolvedPath);
        return result.join('\n');
    } catch (e) {
        return `Error exploring project: ${e.message}`;
    }
}

/**
 * Reads and returns the contents of a file.
 * @param {string} filePath The path to the file to read.
 * @param {number} maxLines Maximum number of lines to read.
 * @returns {Promise<string>} The file contents.
 */
async function read_file(filePath, maxLines = 500) {
    console.log(`[Tool] Executing read_file on: "${filePath}"`);
    try {
        const resolvedPath = path.resolve(filePath);

        if (!fs.existsSync(resolvedPath)) {
            return `Error: File '${filePath}' does not exist.`;
        }

        if (!fs.statSync(resolvedPath).isFile()) {
            return `Error: '${filePath}' is not a file.`;
        }

        // Basic security: prevent reading sensitive files
        const sensitivePatterns = ['.env', 'id_rsa', '.pem', '.key', 'credentials'];
        if (sensitivePatterns.some(pattern => resolvedPath.includes(pattern))) {
            return `Error: Cannot read potentially sensitive file '${filePath}'.`;
        }

        // Read file with line limit
        const content = fs.readFileSync(resolvedPath, 'utf-8');
        const lines = content.split('\n');

        if (lines.length > maxLines) {
            const truncated = lines.slice(0, maxLines).join('\n');
            return `Contents of ${filePath}:\n\n${truncated}\n\n... (truncated, showing first ${maxLines} lines of ${lines.length} total)`;
        }

        return `Contents of ${filePath}:\n\n${content}`;
    } catch (e) {
        if (e.code === 'ENOENT') {
            return `Error: File '${filePath}' not found.`;
        }
        return `Error reading file: ${e.message}`;
    }
}

/**
 * Writes content to a file. Creates the file if it doesn't exist, overwrites if it does.
 * @param {string} filePath The path to the file to write.
 * @param {string} content The content to write to the file.
 * @returns {Promise<string>} Success message.
 */
async function write_file(filePath, content) {
    console.log(`[Tool] Executing write_file to: "${filePath}"`);
    try {
        const resolvedPath = path.resolve(filePath);

        // Basic security: prevent writing to sensitive locations
        const sensitivePatterns = ['.env', '.git/', 'id_rsa', '.pem', '.key', 'credentials'];
        if (sensitivePatterns.some(pattern => resolvedPath.includes(pattern))) {
            return `Error: Cannot write to potentially sensitive location '${filePath}'.`;
        }

        // Create parent directories if they don't exist
        const dir = path.dirname(resolvedPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        // Write the file
        fs.writeFileSync(resolvedPath, content, 'utf-8');

        return `Successfully wrote ${content.length} characters to ${filePath}`;
    } catch (e) {
        return `Error writing file: ${e.message}`;
    }
}

/**
 * Executes a bash command and returns the output.
 * @param {string} command The bash command to execute.
 * @param {number} timeout Maximum execution time in seconds.
 * @returns {Promise<string>} The command output.
 */
async function bash_command(command, timeout = 30) {
    console.log(`[Tool] Executing bash_command: "${command}"`);
    try {
        // Basic security: block dangerous commands
        const dangerousPatterns = ['rm -rf /', 'mkfs', 'dd if=', ':(){:|:&};:', 'fork bomb'];
        if (dangerousPatterns.some(pattern => command.toLowerCase().includes(pattern))) {
            return `Error: Command contains potentially dangerous pattern and was blocked.`;
        }

        // Execute the command with timeout
        const { stdout, stderr } = await execAsync(command, {
            timeout: timeout * 1000,
            maxBuffer: 1024 * 1024 // 1MB buffer
        });

        const output = [];
        if (stdout) output.push(`STDOUT:\n${stdout}`);
        if (stderr) output.push(`STDERR:\n${stderr}`);

        return output.length > 0 ? output.join('\n') : 'Command executed with no output.';
    } catch (e) {
        if (e.killed) {
            return `Error: Command timed out after ${timeout} seconds.`;
        }
        return `Error executing command: ${e.message}\n${e.stderr || ''}`;
    }
}

/**
 * Executes a bash script provided as a string and returns the output.
 * @param {string} scriptContent The bash script content to execute.
 * @param {number} timeout Maximum execution time in seconds.
 * @returns {Promise<string>} The script output.
 */
async function bash_script(scriptContent, timeout = 60) {
    console.log(`[Tool] Executing bash_script`);
    try {
        // Basic security: block dangerous patterns
        const dangerousPatterns = ['rm -rf /', 'mkfs', 'dd if=', ':(){:|:&};:'];
        if (dangerousPatterns.some(pattern => scriptContent.toLowerCase().includes(pattern))) {
            return `Error: Script contains potentially dangerous pattern and was blocked.`;
        }

        // Create temporary script file
        const tmpDir = os.tmpdir();
        const scriptPath = path.join(tmpDir, `script-${Date.now()}.sh`);

        fs.writeFileSync(scriptPath, scriptContent, { mode: 0o755 });

        try {
            // Execute the script
            const { stdout, stderr } = await execAsync(`bash ${scriptPath}`, {
                timeout: timeout * 1000,
                maxBuffer: 1024 * 1024 // 1MB buffer
            });

            const output = [];
            if (stdout) output.push(`STDOUT:\n${stdout}`);
            if (stderr) output.push(`STDERR:\n${stderr}`);

            return output.length > 0 ? output.join('\n') : 'Script executed with no output.';
        } finally {
            // Clean up temporary file
            try {
                fs.unlinkSync(scriptPath);
            } catch (e) {
                // Ignore cleanup errors
            }
        }
    } catch (e) {
        if (e.killed) {
            return `Error: Script timed out after ${timeout} seconds.`;
        }
        return `Error executing script: ${e.message}\n${e.stderr || ''}`;
    }
}

// ============================================================================
// PHASE 1: Essential Tools
// ============================================================================

async function search_code(pattern, searchPath = ".", filePattern = "*", maxResults = 50) {
    console.log(`[Tool] Executing search_code with pattern: "${pattern}" in path: "${searchPath}"`);
    try {
        const resolvedPath = path.resolve(searchPath);

        if (!fs.existsSync(resolvedPath)) {
            return `Error: Path '${searchPath}' does not exist.`;
        }

        const results = [];
        let count = 0;
        const ignoreDirs = new Set(['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build']);

        function searchInDir(dir) {
            if (count >= maxResults) return;

            const items = fs.readdirSync(dir);
            for (const item of items) {
                if (count >= maxResults) break;

                const fullPath = path.join(dir, item);
                const stats = fs.statSync(fullPath);

                if (stats.isDirectory()) {
                    if (!ignoreDirs.has(item)) {
                        searchInDir(fullPath);
                    }
                } else if (stats.isFile()) {
                    // Skip binary and sensitive files
                    if (item.match(/\.(pyc|so|dll|exe|jpg|png|gif|pdf)$/)) continue;
                    if (fullPath.includes('.env') || fullPath.includes('.key')) continue;

                    try {
                        const content = fs.readFileSync(fullPath, 'utf-8');
                        const lines = content.split('\n');
                        const regex = new RegExp(pattern, 'i');

                        lines.forEach((line, index) => {
                            if (count >= maxResults) return;
                            if (regex.test(line)) {
                                results.push(`${fullPath}:${index + 1}: ${line.trim()}`);
                                count++;
                            }
                        });
                    } catch (e) {
                        // Skip files that can't be read
                    }
                }
            }
        }

        searchInDir(resolvedPath);

        if (results.length === 0) {
            return `No matches found for pattern '${pattern}' in ${searchPath}`;
        }

        if (count >= maxResults) {
            results.push(`\n... (truncated, showing first ${maxResults} matches)`);
        }

        return results.join('\n');
    } catch (e) {
        return `Error searching code: ${e.message}`;
    }
}

async function edit_file(filePath, oldText, newText) {
    console.log(`[Tool] Executing edit_file on: "${filePath}"`);
    try {
        const resolvedPath = path.resolve(filePath);

        if (!fs.existsSync(resolvedPath)) {
            return `Error: File '${filePath}' does not exist.`;
        }

        // Security check
        const sensitivePatterns = ['.env', '.git/', 'id_rsa', '.pem', '.key', 'credentials'];
        if (sensitivePatterns.some(pattern => resolvedPath.includes(pattern))) {
            return `Error: Cannot edit potentially sensitive file '${filePath}'.`;
        }

        // Read file
        const content = fs.readFileSync(resolvedPath, 'utf-8');

        // Check if old_text exists
        if (!content.includes(oldText)) {
            return `Error: Text to replace not found in ${filePath}`;
        }

        // Replace text (first occurrence)
        const newContent = content.replace(oldText, newText);

        // Write back
        fs.writeFileSync(resolvedPath, newContent, 'utf-8');

        return `Successfully edited ${filePath}`;
    } catch (e) {
        return `Error editing file: ${e.message}`;
    }
}

async function find_files(pattern, searchPath = ".", maxResults = 100) {
    console.log(`[Tool] Executing find_files with pattern: "${pattern}" in path: "${searchPath}"`);
    try {
        const resolvedPath = path.resolve(searchPath);
        if (!fs.existsSync(resolvedPath)) {
            return `Error: Path '${searchPath}' does not exist.`;
        }

        const results = [];
        let count = 0;
        const ignoreDirs = new Set(['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build']);

        // Check if pattern is glob or regex
        const isGlob = pattern.includes('*') || pattern.includes('?');

        function walkDir(dir) {
            if (count >= maxResults) return;

            const items = fs.readdirSync(dir);
            for (const item of items) {
                if (count >= maxResults) break;

                const fullPath = path.join(dir, item);
                const stats = fs.statSync(fullPath);

                if (stats.isDirectory()) {
                    if (!ignoreDirs.has(item)) {
                        walkDir(fullPath);
                    }
                } else {
                    let match = false;
                    if (isGlob) {
                        // Simple glob matching
                        const regexPattern = pattern.replace(/\*/g, '.*').replace(/\?/g, '.');
                        const regex = new RegExp(`^${regexPattern}$`);
                        match = regex.test(item);
                    } else {
                        // Regex matching
                        const regex = new RegExp(pattern);
                        match = regex.test(item);
                    }

                    if (match) {
                        results.push(fullPath);
                        count++;
                    }
                }
            }
        }

        walkDir(resolvedPath);

        if (results.length === 0) {
            return `No files found matching pattern '${pattern}' in ${searchPath}`;
        }

        if (count >= maxResults) {
            results.push(`\n... (truncated, showing first ${maxResults} results)`);
        }

        return results.join('\n');
    } catch (e) {
        return `Error finding files: ${e.message}`;
    }
}

async function git_status(repoPath = ".") {
    console.log(`[Tool] Executing git_status in: "${repoPath}"`);
    try {
        const { stdout, stderr } = await execAsync('git status', {
            cwd: repoPath,
            timeout: 10000
        });

        return stdout;
    } catch (e) {
        if (e.killed) {
            return "Error: Git status command timed out.";
        }
        return `Error executing git status: ${e.message}\n${e.stderr || ''}`;
    }
}

async function git_diff(repoPath = ".", filePath = null) {
    console.log(`[Tool] Executing git_diff in: "${repoPath}"`);
    try {
        const cmd = filePath ? `git diff ${filePath}` : 'git diff';
        const { stdout, stderr } = await execAsync(cmd, {
            cwd: repoPath,
            timeout: 30000
        });

        return stdout || "No changes detected.";
    } catch (e) {
        if (e.killed) {
            return "Error: Git diff command timed out.";
        }
        return `Error executing git diff: ${e.message}\n${e.stderr || ''}`;
    }
}

async function git_commit(message, repoPath = ".") {
    console.log(`[Tool] Executing git_commit with message: "${message}"`);
    try {
        // Check if there are staged changes
        try {
            await execAsync('git diff --cached --quiet', { cwd: repoPath, timeout: 10000 });
            return "Error: No staged changes to commit. Use git_add first.";
        } catch (e) {
            // If command failed, there are staged changes (which is what we want)
        }

        const { stdout } = await execAsync(`git commit -m "${message.replace(/"/g, '\\"')}"`, {
            cwd: repoPath,
            timeout: 30000
        });

        return stdout;
    } catch (e) {
        if (e.killed) {
            return "Error: Git commit command timed out.";
        }
        return `Error executing git commit: ${e.message}\n${e.stderr || ''}`;
    }
}

async function git_add(filePaths, repoPath = ".") {
    console.log(`[Tool] Executing git_add for: "${filePaths}"`);
    try {
        const { stdout } = await execAsync(`git add ${filePaths}`, {
            cwd: repoPath,
            timeout: 30000
        });

        return `Successfully staged: ${filePaths}`;
    } catch (e) {
        if (e.killed) {
            return "Error: Git add command timed out.";
        }
        return `Error executing git add: ${e.message}\n${e.stderr || ''}`;
    }
}

async function git_log(repoPath = ".", maxCount = 10) {
    console.log(`[Tool] Executing git_log in: "${repoPath}"`);
    try {
        const { stdout } = await execAsync(`git log --max-count=${maxCount} --oneline --decorate`, {
            cwd: repoPath,
            timeout: 30000
        });

        return stdout;
    } catch (e) {
        if (e.killed) {
            return "Error: Git log command timed out.";
        }
        return `Error executing git log: ${e.message}\n${e.stderr || ''}`;
    }
}

async function git_branch(repoPath = ".", action = "list", branchName = null) {
    console.log(`[Tool] Executing git_branch with action: "${action}"`);
    try {
        let cmd;
        if (action === "list") {
            cmd = 'git branch -a';
        } else if (action === "create") {
            if (!branchName) {
                return "Error: branch_name required for create action.";
            }
            cmd = `git branch ${branchName}`;
        } else if (action === "switch") {
            if (!branchName) {
                return "Error: branch_name required for switch action.";
            }
            cmd = `git checkout ${branchName}`;
        } else {
            return `Error: Invalid action '${action}'. Use 'list', 'create', or 'switch'.`;
        }

        const { stdout } = await execAsync(cmd, {
            cwd: repoPath,
            timeout: 30000
        });

        return stdout || `Successfully executed git branch ${action}`;
    } catch (e) {
        if (e.killed) {
            return "Error: Git branch command timed out.";
        }
        return `Error executing git branch: ${e.message}\n${e.stderr || ''}`;
    }
}

// ============================================================================
// PHASE 2: High Value Tools
// ============================================================================

async function search_and_replace(pattern, replacement, searchPath = ".", filePattern = "*", dryRun = true) {
    console.log(`[Tool] Executing search_and_replace: '${pattern}' -> '${replacement}' (dry_run=${dryRun})`);
    try {
        const resolvedPath = path.resolve(searchPath);
        if (!fs.existsSync(resolvedPath)) {
            return `Error: Path '${searchPath}' does not exist.`;
        }

        const results = [];
        let filesChanged = 0;
        let totalReplacements = 0;
        const ignoreDirs = new Set(['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build']);

        function processDir(dir) {
            const items = fs.readdirSync(dir);
            for (const item of items) {
                const fullPath = path.join(dir, item);
                const stats = fs.statSync(fullPath);

                if (stats.isDirectory()) {
                    if (!ignoreDirs.has(item)) {
                        processDir(fullPath);
                    }
                } else {
                    // Skip binary and sensitive files
                    if (item.match(/\.(pyc|so|dll|exe|jpg|png|gif|pdf)$/)) continue;
                    if (fullPath.includes('.env') || fullPath.includes('.key')) continue;

                    try {
                        const content = fs.readFileSync(fullPath, 'utf-8');
                        const regex = new RegExp(pattern, 'g');
                        const matches = (content.match(regex) || []).length;

                        if (matches > 0) {
                            if (dryRun) {
                                results.push(`${fullPath}: ${matches} match(es)`);
                            } else {
                                const newContent = content.replace(regex, replacement);
                                fs.writeFileSync(fullPath, newContent, 'utf-8');
                                results.push(`${fullPath}: ${matches} replacement(s) made`);
                            }

                            filesChanged++;
                            totalReplacements += matches;
                        }
                    } catch (e) {
                        // Skip files that can't be read
                    }
                }
            }
        }

        processDir(resolvedPath);

        if (results.length === 0) {
            return `No matches found for pattern '${pattern}'`;
        }

        const summary = `${dryRun ? '[DRY RUN] ' : ''}Found ${totalReplacements} match(es) in ${filesChanged} file(s)\n\n`;
        return summary + results.join('\n');
    } catch (e) {
        return `Error in search and replace: ${e.message}`;
    }
}

async function copy_file(source, destination) {
    console.log(`[Tool] Executing copy_file: '${source}' -> '${destination}'`);
    try {
        const sourcePath = path.resolve(source);
        const destPath = path.resolve(destination);

        if (!fs.existsSync(sourcePath)) {
            return `Error: Source '${source}' does not exist.`;
        }

        // Security check
        const sensitivePatterns = ['.env', '.git/', 'id_rsa', '.pem', '.key', 'credentials'];
        if (sensitivePatterns.some(pattern => destPath.includes(pattern))) {
            return `Error: Cannot copy to sensitive location '${destination}'.`;
        }

        const stats = fs.statSync(sourcePath);
        if (stats.isDirectory()) {
            // Copy directory recursively
            function copyRecursive(src, dest) {
                if (!fs.existsSync(dest)) {
                    fs.mkdirSync(dest, { recursive: true });
                }
                const items = fs.readdirSync(src);
                for (const item of items) {
                    const srcPath = path.join(src, item);
                    const dstPath = path.join(dest, item);
                    if (fs.statSync(srcPath).isDirectory()) {
                        copyRecursive(srcPath, dstPath);
                    } else {
                        fs.copyFileSync(srcPath, dstPath);
                    }
                }
            }
            copyRecursive(sourcePath, destPath);
            return `Successfully copied directory '${source}' to '${destination}'`;
        } else {
            const destDir = path.dirname(destPath);
            if (!fs.existsSync(destDir)) {
                fs.mkdirSync(destDir, { recursive: true });
            }
            fs.copyFileSync(sourcePath, destPath);
            return `Successfully copied file '${source}' to '${destination}'`;
        }
    } catch (e) {
        return `Error copying file: ${e.message}`;
    }
}

async function move_file(source, destination) {
    console.log(`[Tool] Executing move_file: '${source}' -> '${destination}'`);
    try {
        const sourcePath = path.resolve(source);
        const destPath = path.resolve(destination);

        if (!fs.existsSync(sourcePath)) {
            return `Error: Source '${source}' does not exist.`;
        }

        // Security check
        const sensitivePatterns = ['.env', '.git/', 'id_rsa', '.pem', '.key', 'credentials'];
        if (sensitivePatterns.some(pattern => sourcePath.includes(pattern))) {
            return `Error: Cannot move sensitive file '${source}'.`;
        }
        if (sensitivePatterns.some(pattern => destPath.includes(pattern))) {
            return `Error: Cannot move to sensitive location '${destination}'.`;
        }

        const destDir = path.dirname(destPath);
        if (!fs.existsSync(destDir)) {
            fs.mkdirSync(destDir, { recursive: true });
        }

        fs.renameSync(sourcePath, destPath);
        return `Successfully moved '${source}' to '${destination}'`;
    } catch (e) {
        return `Error moving file: ${e.message}`;
    }
}

async function delete_file(filePath, confirm = false) {
    console.log(`[Tool] Executing delete_file on: '${filePath}'`);
    try {
        if (!confirm) {
            return "Error: Must set confirm=True to delete files. This is a safety measure.";
        }

        const resolvedPath = path.resolve(filePath);

        if (!fs.existsSync(resolvedPath)) {
            return `Error: Path '${filePath}' does not exist.`;
        }

        // Security check
        const criticalPatterns = ['.git', '.env', 'id_rsa', '.pem', '.key', 'credentials'];
        if (criticalPatterns.some(pattern => resolvedPath.includes(pattern))) {
            return `Error: Cannot delete sensitive path '${filePath}'.`;
        }

        // Prevent deleting root-level directories
        const parts = resolvedPath.split(path.sep);
        if (parts.length <= 2) {
            return `Error: Cannot delete root-level path '${filePath}' for safety.`;
        }

        const stats = fs.statSync(resolvedPath);
        if (stats.isDirectory()) {
            fs.rmSync(resolvedPath, { recursive: true, force: true });
            return `Successfully deleted directory '${filePath}'`;
        } else {
            fs.unlinkSync(resolvedPath);
            return `Successfully deleted file '${filePath}'`;
        }
    } catch (e) {
        return `Error deleting file: ${e.message}`;
    }
}

async function install_package(packageName, packageManager = "auto") {
    console.log(`[Tool] Executing install_package: '${packageName}' with ${packageManager}`);
    try {
        if (packageManager === "auto") {
            // Auto-detect based on project files
            if (fs.existsSync("package.json")) {
                packageManager = "npm";
            } else if (fs.existsSync("requirements.txt") || fs.existsSync("setup.py")) {
                packageManager = "pip";
            } else {
                return "Error: Could not auto-detect package manager. Please specify 'npm', 'pip', or 'yarn'.";
            }
        }

        let cmd;
        if (packageManager === "npm") {
            cmd = `npm install ${packageName}`;
        } else if (packageManager === "pip") {
            cmd = `pip install ${packageName}`;
        } else if (packageManager === "yarn") {
            cmd = `yarn add ${packageName}`;
        } else {
            return `Error: Unsupported package manager '${packageManager}'`;
        }

        const { stdout, stderr } = await execAsync(cmd, {
            timeout: 300000 // 5 minutes
        });

        return `Successfully installed ${packageName}\n${stdout}`;
    } catch (e) {
        if (e.killed) {
            return "Error: Package installation timed out after 5 minutes.";
        }
        return `Error installing ${packageName}:\n${e.stderr || e.message}`;
    }
}

async function run_tests(testPath = ".", framework = "auto") {
    console.log(`[Tool] Executing run_tests in: '${testPath}' with framework: ${framework}`);
    try {
        if (framework === "auto") {
            // Auto-detect test framework
            if (fs.existsSync("package.json")) {
                framework = "npm";
            } else if (fs.existsSync("pytest.ini") || fs.existsSync("setup.py")) {
                framework = "pytest";
            } else {
                return "Error: Could not auto-detect test framework. Please specify 'pytest', 'jest', or 'npm'.";
            }
        }

        let cmd;
        if (framework === "pytest") {
            cmd = `pytest ${testPath} -v`;
        } else if (framework === "jest") {
            cmd = `jest ${testPath}`;
        } else if (framework === "npm") {
            cmd = 'npm test';
        } else {
            return `Error: Unsupported test framework '${framework}'`;
        }

        try {
            const { stdout, stderr } = await execAsync(cmd, {
                timeout: 300000 // 5 minutes
            });

            const output = [];
            if (stdout) output.push(stdout);
            if (stderr) output.push(stderr);
            output.push("\nTest Status: PASSED");

            return output.join('\n');
        } catch (e) {
            if (e.killed) {
                return "Error: Tests timed out after 5 minutes.";
            }

            const output = [];
            if (e.stdout) output.push(e.stdout);
            if (e.stderr) output.push(e.stderr);
            output.push("\nTest Status: FAILED");

            return output.join('\n');
        }
    } catch (e) {
        return `Error running tests: ${e.message}`;
    }
}

async function http_request(url, method = "GET", headers = null, body = null) {
    console.log(`[Tool] Executing http_request: ${method} ${url}`);
    try {
        // Try to use node-fetch or built-in fetch
        let fetch;
        try {
            fetch = (await import('node-fetch')).default;
        } catch (e) {
            // Try global fetch (Node 18+)
            if (typeof globalThis.fetch !== 'undefined') {
                fetch = globalThis.fetch;
            } else {
                return "Error: fetch not available. Install node-fetch: npm install node-fetch";
            }
        }

        const options = {
            method: method.toUpperCase(),
            headers: headers ? JSON.parse(headers) : {},
            signal: AbortSignal.timeout(30000)
        };

        if (body && (method.toUpperCase() === 'POST' || method.toUpperCase() === 'PUT')) {
            options.body = body;
        }

        const response = await fetch(url, options);
        const text = await response.text();

        const result = [
            `Status: ${response.status}`,
            `Headers: ${JSON.stringify(Object.fromEntries(response.headers))}`,
            `\nBody:\n${text.substring(0, 5000)}` // Limit response size
        ];

        return result.join('\n');
    } catch (e) {
        return `Error making HTTP request: ${e.message}`;
    }
}

// ============================================================================
// PHASE 3: Advanced Tools
// ============================================================================

async function lint_code(filePath = ".", linter = "auto") {
    console.log(`[Tool] Executing lint_code on: '${filePath}' with linter: ${linter}`);
    try {
        if (linter === "auto") {
            // Auto-detect based on project
            if (fs.existsSync("package.json")) {
                linter = "eslint";
            } else if (fs.existsSync("setup.py") || filePath.endsWith('.py')) {
                linter = "pylint";
            } else {
                return "Error: Could not auto-detect linter. Please specify 'eslint', 'pylint', or 'flake8'.";
            }
        }

        let cmd;
        if (linter === "eslint") {
            cmd = `eslint ${filePath}`;
        } else if (linter === "pylint") {
            cmd = `pylint ${filePath}`;
        } else if (linter === "flake8") {
            cmd = `flake8 ${filePath}`;
        } else {
            return `Error: Unsupported linter '${linter}'`;
        }

        try {
            const { stdout, stderr } = await execAsync(cmd, { timeout: 60000 });
            const output = [];
            if (stdout) output.push(stdout);
            if (stderr) output.push(stderr);

            return output.length > 0 ? output.join('\n') : "No linting issues found!";
        } catch (e) {
            if (e.killed) {
                return "Error: Linting timed out after 60 seconds.";
            }
            if (e.code === 'ENOENT') {
                return `Error: ${linter} is not installed or not in PATH.`;
            }

            // Linters often return non-zero exit codes when there are issues
            const output = [];
            if (e.stdout) output.push(e.stdout);
            if (e.stderr) output.push(e.stderr);
            return output.length > 0 ? output.join('\n') : "Linting completed with issues.";
        }
    } catch (e) {
        return `Error running linter: ${e.message}`;
    }
}

async function format_code(filePath = ".", formatter = "auto") {
    console.log(`[Tool] Executing format_code on: '${filePath}' with formatter: ${formatter}`);
    try {
        if (formatter === "auto") {
            // Auto-detect based on file type
            if (filePath.match(/\.(js|ts|jsx|tsx|json|html|css)$/)) {
                formatter = "prettier";
            } else if (filePath.endsWith('.py')) {
                formatter = "black";
            } else {
                return "Error: Could not auto-detect formatter. Please specify 'prettier' or 'black'.";
            }
        }

        let cmd;
        if (formatter === "prettier") {
            cmd = `prettier --write ${filePath}`;
        } else if (formatter === "black") {
            cmd = `black ${filePath}`;
        } else {
            return `Error: Unsupported formatter '${formatter}'`;
        }

        const { stdout, stderr } = await execAsync(cmd, { timeout: 60000 });

        return `Successfully formatted ${filePath}\n${stdout}`;
    } catch (e) {
        if (e.killed) {
            return "Error: Formatting timed out after 60 seconds.";
        }
        if (e.code === 'ENOENT') {
            return `Error: ${formatter} is not installed or not in PATH.`;
        }
        return `Error formatting code:\n${e.stderr || e.message}`;
    }
}

async function list_directory(dirPath = ".", showHidden = false) {
    console.log(`[Tool] Executing list_directory on: '${dirPath}'`);
    try {
        const resolvedPath = path.resolve(dirPath);
        if (!fs.existsSync(resolvedPath)) {
            return `Error: Path '${dirPath}' does not exist.`;
        }

        const stats = fs.statSync(resolvedPath);
        if (!stats.isDirectory()) {
            return `Error: '${dirPath}' is not a directory.`;
        }

        const items = [];
        const dirItems = fs.readdirSync(resolvedPath).sort();

        for (const item of dirItems) {
            if (!showHidden && item.startsWith('.')) continue;

            const itemPath = path.join(resolvedPath, item);
            try {
                const itemStats = fs.statSync(itemPath);
                const itemType = itemStats.isDirectory() ? "DIR" : "FILE";
                const size = itemStats.isFile() ? itemStats.size : "-";
                items.push(`${itemType.padEnd(6)} ${String(size).padStart(12)} ${item}`);
            } catch (e) {
                items.push(`${"?".padEnd(6)} ${"?".padStart(12)} ${item}`);
            }
        }

        if (items.length === 0) {
            return `Directory '${dirPath}' is empty.`;
        }

        const header = `Contents of ${dirPath}:\n${"TYPE".padEnd(6)} ${"SIZE".padStart(12)} NAME\n${"-".repeat(50)}`;
        return header + '\n' + items.join('\n');
    } catch (e) {
        return `Error listing directory: ${e.message}`;
    }
}

async function get_file_info(filePath) {
    console.log(`[Tool] Executing get_file_info on: '${filePath}'`);
    try {
        const resolvedPath = path.resolve(filePath);

        if (!fs.existsSync(resolvedPath)) {
            return `Error: Path '${filePath}' does not exist.`;
        }

        const stats = fs.statSync(resolvedPath);
        const info = [
            `Path: ${resolvedPath}`,
            `Type: ${stats.isDirectory() ? 'Directory' : 'File'}`,
            `Size: ${stats.size} bytes`,
            `Modified: ${stats.mtime}`,
            `Permissions: ${(stats.mode & parseInt('777', 8)).toString(8)}`,
        ];

        if (stats.isFile()) {
            try {
                const content = fs.readFileSync(resolvedPath, 'utf-8');
                const lines = content.split('\n').length;
                info.push(`Lines: ${lines}`);
            } catch (e) {
                // Skip if file can't be read
            }
        }

        return info.join('\n');
    } catch (e) {
        return `Error getting file info: ${e.message}`;
    }
}

async function build_project(buildCommand = null) {
    console.log(`[Tool] Executing build_project with command: '${buildCommand}'`);
    try {
        if (!buildCommand) {
            // Auto-detect build command
            if (fs.existsSync("package.json")) {
                buildCommand = "npm run build";
            } else if (fs.existsSync("Makefile")) {
                buildCommand = "make";
            } else if (fs.existsSync("setup.py")) {
                buildCommand = "python setup.py build";
            } else {
                return "Error: Could not auto-detect build command. Please specify a build command.";
            }
        }

        try {
            const { stdout, stderr } = await execAsync(buildCommand, {
                timeout: 600000 // 10 minutes
            });

            const output = [];
            if (stdout) output.push(stdout.slice(-5000)); // Last 5000 chars
            if (stderr) output.push(stderr.slice(-5000));
            output.push("\nBuild Status: SUCCESS");

            return output.join('\n');
        } catch (e) {
            if (e.killed) {
                return "Error: Build timed out after 10 minutes.";
            }

            const output = [];
            if (e.stdout) output.push(e.stdout.slice(-5000));
            if (e.stderr) output.push(e.stderr.slice(-5000));
            output.push("\nBuild Status: FAILED");

            return output.join('\n');
        }
    } catch (e) {
        return `Error building project: ${e.message}`;
    }
}

// ============================================================================
// BROWSER AUTOMATION TOOLS (QA Testing)
// ============================================================================

// Global browser instance for reuse across tool calls
let _browserInstance = null;
let _browserPage = null;

async function _getBrowser() {
    if (_browserInstance === null) {
        try {
            const { chromium } = await import('playwright');
            // Check environment variable for headless mode (defaults to true)
            const headless = ['true', '1', 'yes'].includes((process.env.BROWSER_HEADLESS || 'true').toLowerCase());
            _browserInstance = await chromium.launch({ headless });
            _browserPage = await _browserInstance.newPage();
        } catch (e) {
            return [null, "Error: Playwright not installed. Install with: npm install playwright && npx playwright install"];
        }
    }
    return [_browserPage, null];
}

async function browser_navigate(url, waitUntil = "load") {
    console.log(`[Tool] Executing browser_navigate to: "${url}"`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        await page.goto(url, { waitUntil, timeout: 30000 });
        const title = await page.title();

        return `Successfully navigated to ${url}\nPage title: ${title}`;
    } catch (e) {
        return `Error navigating to ${url}: ${e.message}`;
    }
}

async function browser_screenshot(filename = "screenshot.png", fullPage = false) {
    console.log(`[Tool] Executing browser_screenshot to: "${filename}"`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        await page.screenshot({ path: filename, fullPage });

        return `Screenshot saved to ${filename}`;
    } catch (e) {
        return `Error taking screenshot: ${e.message}`;
    }
}

async function browser_click(selector, timeout = 30) {
    console.log(`[Tool] Executing browser_click on: "${selector}"`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        await page.click(selector, { timeout: timeout * 1000 });

        return `Successfully clicked element: ${selector}`;
    } catch (e) {
        return `Error clicking ${selector}: ${e.message}`;
    }
}

async function browser_type(selector, text, timeout = 30) {
    console.log(`[Tool] Executing browser_type on: "${selector}"`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        await page.fill(selector, text, { timeout: timeout * 1000 });

        return `Successfully typed text into: ${selector}`;
    } catch (e) {
        return `Error typing into ${selector}: ${e.message}`;
    }
}

async function browser_get_text(selector, timeout = 30) {
    console.log(`[Tool] Executing browser_get_text from: "${selector}"`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        const element = await page.waitForSelector(selector, { timeout: timeout * 1000 });
        const text = await element.textContent();

        return `Text from ${selector}: ${text}`;
    } catch (e) {
        return `Error getting text from ${selector}: ${e.message}`;
    }
}

async function browser_evaluate(javascriptCode) {
    console.log(`[Tool] Executing browser_evaluate`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        const result = await page.evaluate(javascriptCode);

        return `JavaScript result: ${JSON.stringify(result, null, 2)}`;
    } catch (e) {
        return `Error evaluating JavaScript: ${e.message}`;
    }
}

async function browser_wait_for(selector, state = "visible", timeout = 30) {
    console.log(`[Tool] Executing browser_wait_for: "${selector}" to be "${state}"`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        await page.waitForSelector(selector, { state, timeout: timeout * 1000 });

        return `Element ${selector} is now ${state}`;
    } catch (e) {
        return `Error waiting for ${selector}: ${e.message}`;
    }
}

async function browser_fill_form(formData) {
    console.log(`[Tool] Executing browser_fill_form`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        const data = JSON.parse(formData);
        const results = [];

        for (const [selector, value] of Object.entries(data)) {
            await page.fill(selector, value);
            results.push(`${selector} = ${value}`);
        }

        return `Successfully filled form fields:\n${results.join('\n')}`;
    } catch (e) {
        return `Error filling form: ${e.message}`;
    }
}

async function browser_get_url() {
    console.log(`[Tool] Executing browser_get_url`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        const url = page.url();

        return `Current URL: ${url}`;
    } catch (e) {
        return `Error getting URL: ${e.message}`;
    }
}

async function browser_go_back() {
    console.log(`[Tool] Executing browser_go_back`);
    try {
        const [page, error] = await _getBrowser();
        if (error) return error;

        await page.goBack();

        return `Navigated back to: ${page.url()}`;
    } catch (e) {
        return `Error going back: ${e.message}`;
    }
}

async function browser_close() {
    console.log(`[Tool] Executing browser_close`);
    try {
        if (_browserInstance) {
            await _browserInstance.close();
            _browserInstance = null;
            _browserPage = null;
        }

        return "Browser closed successfully";
    } catch (e) {
        return `Error closing browser: ${e.message}`;
    }
}

// --- Tool Manifest ---
// This object maps tool names to their implementation and definition for the LLM.
export const TOOLS = {
    web_search: {
        // The `execute` function is what our agent will run.
        execute: web_search,
        // The `definition` must match the schema expected by the LLM provider.
        // This includes a 'type' and a nested 'function' object.
        definition: {
            "type": "function",
            "function": {
                name: "web_search",
                description: "Fetches real-time information from the internet using a search query.",
                parameters: {
                    type: "object",
                    properties: {
                        query: { type: "string", description: "The search query to execute." },
                    },
                    required: ["query"],
                },
            },
        },
    },
    calculator: {
        execute: calculator,
        definition: {
            "type": "function",
            "function": {
                name: "calculator",
                description: "Solves mathematical expressions and equations. Can handle advanced math.",
                parameters: {
                    type: "object",
                    properties: {
                        expression: { type: "string", description: "The mathematical expression to evaluate (e.g., 'sqrt(529)', '12 * 4')." },
                    },
                    required: ["expression"],
                },
            },
        },
    },
    explore_project: {
        execute: explore_project,
        definition: {
            "type": "function",
            "function": {
                name: "explore_project",
                description: "Explores and returns the directory structure of a project. Useful for understanding codebase organization.",
                parameters: {
                    type: "object",
                    properties: {
                        path: { type: "string", description: "The directory path to explore. Defaults to current directory '.'" },
                    },
                    required: [],
                },
            },
        },
    },
    read_file: {
        execute: read_file,
        definition: {
            "type": "function",
            "function": {
                name: "read_file",
                description: "Reads and returns the contents of a file. Cannot read sensitive files like .env or private keys.",
                parameters: {
                    type: "object",
                    properties: {
                        file_path: { type: "string", description: "The path to the file to read." },
                        max_lines: { type: "integer", description: "Maximum number of lines to read (default: 500)." },
                    },
                    required: ["file_path"],
                },
            },
        },
    },
    write_file: {
        execute: write_file,
        definition: {
            "type": "function",
            "function": {
                name: "write_file",
                description: "Writes content to a file. Creates new file or overwrites existing one. Creates parent directories if needed.",
                parameters: {
                    type: "object",
                    properties: {
                        file_path: { type: "string", description: "The path to the file to write." },
                        content: { type: "string", description: "The content to write to the file." },
                    },
                    required: ["file_path", "content"],
                },
            },
        },
    },
    bash_command: {
        execute: bash_command,
        definition: {
            "type": "function",
            "function": {
                name: "bash_command",
                description: "Executes a bash command and returns the output. Has security restrictions to prevent dangerous operations.",
                parameters: {
                    type: "object",
                    properties: {
                        command: { type: "string", description: "The bash command to execute." },
                        timeout: { type: "integer", description: "Maximum execution time in seconds (default: 30)." },
                    },
                    required: ["command"],
                },
            },
        },
    },
    bash_script: {
        execute: bash_script,
        definition: {
            "type": "function",
            "function": {
                name: "bash_script",
                description: "Executes a multi-line bash script and returns the output. Script is written to temp file and executed.",
                parameters: {
                    type: "object",
                    properties: {
                        script_content: { type: "string", description: "The bash script content to execute." },
                        timeout: { type: "integer", description: "Maximum execution time in seconds (default: 60)." },
                    },
                    required: ["script_content"],
                },
            },
        },
    },
    // === Phase 1 Tools ===
    search_code: {
        execute: search_code,
        definition: {
            type: "function",
            function: {
                name: "search_code",
                description: "Searches for a pattern across files using regex. Returns file paths, line numbers, and matching lines.",
                parameters: {
                    type: "object",
                    properties: {
                        pattern: { type: "string", description: "The regex pattern to search for." },
                        path: { type: "string", description: "The directory to search in (default: '.')." },
                        file_pattern: { type: "string", description: "File pattern to filter (default: '*')." },
                        max_results: { type: "integer", description: "Maximum number of matches to return (default: 50)." },
                    },
                    required: ["pattern"],
                },
            },
        },
    },
    edit_file: {
        execute: edit_file,
        definition: {
            type: "function",
            function: {
                name: "edit_file",
                description: "Edits a file by replacing old_text with new_text. More efficient than rewriting entire file.",
                parameters: {
                    type: "object",
                    properties: {
                        file_path: { type: "string", description: "The path to the file to edit." },
                        old_text: { type: "string", description: "The text to be replaced." },
                        new_text: { type: "string", description: "The replacement text." },
                    },
                    required: ["file_path", "old_text", "new_text"],
                },
            },
        },
    },
    find_files: {
        execute: find_files,
        definition: {
            type: "function",
            function: {
                name: "find_files",
                description: "Finds files matching a pattern (glob or regex). Returns list of matching file paths.",
                parameters: {
                    type: "object",
                    properties: {
                        pattern: { type: "string", description: "The pattern to match (glob like '*.py' or regex)." },
                        path: { type: "string", description: "The directory to search in (default: '.')." },
                        max_results: { type: "integer", description: "Maximum number of results (default: 100)." },
                    },
                    required: ["pattern"],
                },
            },
        },
    },
    git_status: {
        execute: git_status,
        definition: {
            type: "function",
            function: {
                name: "git_status",
                description: "Returns the git status of a repository showing staged/unstaged changes.",
                parameters: {
                    type: "object",
                    properties: {
                        repo_path: { type: "string", description: "Path to the git repository (default: '.')." },
                    },
                    required: [],
                },
            },
        },
    },
    git_diff: {
        execute: git_diff,
        definition: {
            type: "function",
            function: {
                name: "git_diff",
                description: "Shows git diff for repository or specific file.",
                parameters: {
                    type: "object",
                    properties: {
                        repo_path: { type: "string", description: "Path to the git repository (default: '.')." },
                        file_path: { type: "string", description: "Specific file to diff (optional)." },
                    },
                    required: [],
                },
            },
        },
    },
    git_commit: {
        execute: git_commit,
        definition: {
            type: "function",
            function: {
                name: "git_commit",
                description: "Creates a git commit with the specified message. Requires staged changes.",
                parameters: {
                    type: "object",
                    properties: {
                        message: { type: "string", description: "The commit message." },
                        repo_path: { type: "string", description: "Path to the git repository (default: '.')." },
                    },
                    required: ["message"],
                },
            },
        },
    },
    git_add: {
        execute: git_add,
        definition: {
            type: "function",
            function: {
                name: "git_add",
                description: "Stages files for commit. Can stage multiple files separated by spaces.",
                parameters: {
                    type: "object",
                    properties: {
                        file_paths: { type: "string", description: "File paths to stage, space-separated." },
                        repo_path: { type: "string", description: "Path to the git repository (default: '.')." },
                    },
                    required: ["file_paths"],
                },
            },
        },
    },
    git_log: {
        execute: git_log,
        definition: {
            type: "function",
            function: {
                name: "git_log",
                description: "Shows git commit history.",
                parameters: {
                    type: "object",
                    properties: {
                        repo_path: { type: "string", description: "Path to the git repository (default: '.')." },
                        max_count: { type: "integer", description: "Maximum number of commits to show (default: 10)." },
                    },
                    required: [],
                },
            },
        },
    },
    git_branch: {
        execute: git_branch,
        definition: {
            type: "function",
            function: {
                name: "git_branch",
                description: "Git branch operations: list, create, or switch branches.",
                parameters: {
                    type: "object",
                    properties: {
                        repo_path: { type: "string", description: "Path to the git repository (default: '.')." },
                        action: { type: "string", description: "Action to perform: 'list', 'create', or 'switch' (default: 'list')." },
                        branch_name: { type: "string", description: "Branch name for create/switch actions." },
                    },
                    required: [],
                },
            },
        },
    },
    // === Phase 2 Tools ===
    search_and_replace: {
        execute: search_and_replace,
        definition: {
            type: "function",
            function: {
                name: "search_and_replace",
                description: "Find and replace text across multiple files using regex. Supports dry-run mode.",
                parameters: {
                    type: "object",
                    properties: {
                        pattern: { type: "string", description: "The regex pattern to search for." },
                        replacement: { type: "string", description: "The replacement text." },
                        path: { type: "string", description: "Directory to search in (default: '.')." },
                        file_pattern: { type: "string", description: "File pattern filter (default: '*')." },
                        dry_run: { type: "boolean", description: "If true, shows what would change without making changes (default: true)." },
                    },
                    required: ["pattern", "replacement"],
                },
            },
        },
    },
    copy_file: {
        execute: copy_file,
        definition: {
            type: "function",
            function: {
                name: "copy_file",
                description: "Copies a file or directory from source to destination.",
                parameters: {
                    type: "object",
                    properties: {
                        source: { type: "string", description: "Source file or directory path." },
                        destination: { type: "string", description: "Destination path." },
                    },
                    required: ["source", "destination"],
                },
            },
        },
    },
    move_file: {
        execute: move_file,
        definition: {
            type: "function",
            function: {
                name: "move_file",
                description: "Moves or renames a file or directory.",
                parameters: {
                    type: "object",
                    properties: {
                        source: { type: "string", description: "Source file or directory path." },
                        destination: { type: "string", description: "Destination path." },
                    },
                    required: ["source", "destination"],
                },
            },
        },
    },
    delete_file: {
        execute: delete_file,
        definition: {
            type: "function",
            function: {
                name: "delete_file",
                description: "Deletes a file or directory. Requires confirm=True for safety.",
                parameters: {
                    type: "object",
                    properties: {
                        path: { type: "string", description: "Path to delete." },
                        confirm: { type: "boolean", description: "Must be true to confirm deletion (safety measure)." },
                    },
                    required: ["path", "confirm"],
                },
            },
        },
    },
    install_package: {
        execute: install_package,
        definition: {
            type: "function",
            function: {
                name: "install_package",
                description: "Installs a package using npm, pip, or yarn. Auto-detects package manager.",
                parameters: {
                    type: "object",
                    properties: {
                        package_name: { type: "string", description: "Name of the package to install." },
                        package_manager: { type: "string", description: "Package manager: 'npm', 'pip', 'yarn', or 'auto' (default: 'auto')." },
                    },
                    required: ["package_name"],
                },
            },
        },
    },
    run_tests: {
        execute: run_tests,
        definition: {
            type: "function",
            function: {
                name: "run_tests",
                description: "Runs tests using pytest, jest, or npm test. Auto-detects test framework.",
                parameters: {
                    type: "object",
                    properties: {
                        test_path: { type: "string", description: "Path to tests (default: '.')." },
                        framework: { type: "string", description: "Test framework: 'pytest', 'jest', 'npm', or 'auto' (default: 'auto')." },
                    },
                    required: [],
                },
            },
        },
    },
    http_request: {
        execute: http_request,
        definition: {
            type: "function",
            function: {
                name: "http_request",
                description: "Makes an HTTP request and returns the response. Supports GET, POST, PUT, DELETE.",
                parameters: {
                    type: "object",
                    properties: {
                        url: { type: "string", description: "The URL to request." },
                        method: { type: "string", description: "HTTP method: GET, POST, PUT, DELETE (default: 'GET')." },
                        headers: { type: "string", description: "JSON string of headers, e.g. '{\"Content-Type\": \"application/json\"}' (optional)." },
                        body: { type: "string", description: "Request body for POST/PUT (optional)." },
                    },
                    required: ["url"],
                },
            },
        },
    },
    // === Phase 3 Tools ===
    lint_code: {
        execute: lint_code,
        definition: {
            type: "function",
            function: {
                name: "lint_code",
                description: "Runs a code linter (eslint, pylint, flake8). Auto-detects linter based on project.",
                parameters: {
                    type: "object",
                    properties: {
                        file_path: { type: "string", description: "Path to file or directory to lint (default: '.')." },
                        linter: { type: "string", description: "Linter to use: 'eslint', 'pylint', 'flake8', or 'auto' (default: 'auto')." },
                    },
                    required: [],
                },
            },
        },
    },
    format_code: {
        execute: format_code,
        definition: {
            type: "function",
            function: {
                name: "format_code",
                description: "Formats code using prettier or black. Auto-detects formatter based on file type.",
                parameters: {
                    type: "object",
                    properties: {
                        file_path: { type: "string", description: "Path to file to format (default: '.')." },
                        formatter: { type: "string", description: "Formatter: 'prettier', 'black', or 'auto' (default: 'auto')." },
                    },
                    required: [],
                },
            },
        },
    },
    list_directory: {
        execute: list_directory,
        definition: {
            type: "function",
            function: {
                name: "list_directory",
                description: "Lists contents of a directory with file sizes and types.",
                parameters: {
                    type: "object",
                    properties: {
                        path: { type: "string", description: "Directory path (default: '.')." },
                        show_hidden: { type: "boolean", description: "Show hidden files (default: false)." },
                    },
                    required: [],
                },
            },
        },
    },
    get_file_info: {
        execute: get_file_info,
        definition: {
            type: "function",
            function: {
                name: "get_file_info",
                description: "Gets metadata about a file: size, modified date, permissions, line count.",
                parameters: {
                    type: "object",
                    properties: {
                        file_path: { type: "string", description: "Path to the file." },
                    },
                    required: ["file_path"],
                },
            },
        },
    },
    build_project: {
        execute: build_project,
        definition: {
            type: "function",
            function: {
                name: "build_project",
                description: "Runs a build command for the project. Auto-detects build command if not specified.",
                parameters: {
                    type: "object",
                    properties: {
                        build_command: { type: "string", description: "Build command to run (optional, auto-detects)." },
                    },
                    required: [],
                },
            },
        },
    },
    // === Browser Automation Tools ===
    browser_navigate: {
        execute: browser_navigate,
        definition: {
            type: "function",
            function: {
                name: "browser_navigate",
                description: "Navigate browser to a URL for testing web applications.",
                parameters: {
                    type: "object",
                    properties: {
                        url: { type: "string", description: "The URL to navigate to." },
                        wait_until: { type: "string", description: "When to consider navigation complete: 'load', 'domcontentloaded', 'networkidle' (default: 'load')." },
                    },
                    required: ["url"],
                },
            },
        },
    },
    browser_screenshot: {
        execute: browser_screenshot,
        definition: {
            type: "function",
            function: {
                name: "browser_screenshot",
                description: "Take a screenshot of the current browser page.",
                parameters: {
                    type: "object",
                    properties: {
                        filename: { type: "string", description: "Filename for the screenshot (default: 'screenshot.png')." },
                        full_page: { type: "boolean", description: "Capture full scrollable page (default: false)." },
                    },
                    required: [],
                },
            },
        },
    },
    browser_click: {
        execute: browser_click,
        definition: {
            type: "function",
            function: {
                name: "browser_click",
                description: "Click an element on the page using CSS selector.",
                parameters: {
                    type: "object",
                    properties: {
                        selector: { type: "string", description: "CSS selector for the element to click (e.g., '#button-id', '.class-name')." },
                        timeout: { type: "integer", description: "Maximum wait time in seconds (default: 30)." },
                    },
                    required: ["selector"],
                },
            },
        },
    },
    browser_type: {
        execute: browser_type,
        definition: {
            type: "function",
            function: {
                name: "browser_type",
                description: "Type text into an input field using CSS selector.",
                parameters: {
                    type: "object",
                    properties: {
                        selector: { type: "string", description: "CSS selector for the input field." },
                        text: { type: "string", description: "Text to type into the field." },
                        timeout: { type: "integer", description: "Maximum wait time in seconds (default: 30)." },
                    },
                    required: ["selector", "text"],
                },
            },
        },
    },
    browser_get_text: {
        execute: browser_get_text,
        definition: {
            type: "function",
            function: {
                name: "browser_get_text",
                description: "Get text content from an element using CSS selector.",
                parameters: {
                    type: "object",
                    properties: {
                        selector: { type: "string", description: "CSS selector for the element." },
                        timeout: { type: "integer", description: "Maximum wait time in seconds (default: 30)." },
                    },
                    required: ["selector"],
                },
            },
        },
    },
    browser_evaluate: {
        execute: browser_evaluate,
        definition: {
            type: "function",
            function: {
                name: "browser_evaluate",
                description: "Execute JavaScript code in the browser context and return the result.",
                parameters: {
                    type: "object",
                    properties: {
                        javascript_code: { type: "string", description: "JavaScript code to execute in the browser." },
                    },
                    required: ["javascript_code"],
                },
            },
        },
    },
    browser_wait_for: {
        execute: browser_wait_for,
        definition: {
            type: "function",
            function: {
                name: "browser_wait_for",
                description: "Wait for an element to reach a specific state.",
                parameters: {
                    type: "object",
                    properties: {
                        selector: { type: "string", description: "CSS selector for the element." },
                        state: { type: "string", description: "State to wait for: 'attached', 'detached', 'visible', 'hidden' (default: 'visible')." },
                        timeout: { type: "integer", description: "Maximum wait time in seconds (default: 30)." },
                    },
                    required: ["selector"],
                },
            },
        },
    },
    browser_fill_form: {
        execute: browser_fill_form,
        definition: {
            type: "function",
            function: {
                name: "browser_fill_form",
                description: "Fill multiple form fields at once using a JSON mapping of selectors to values.",
                parameters: {
                    type: "object",
                    properties: {
                        form_data: { type: "string", description: "JSON string mapping CSS selectors to values, e.g. '{\"#username\": \"user\", \"#password\": \"pass\"}'." },
                    },
                    required: ["form_data"],
                },
            },
        },
    },
    browser_get_url: {
        execute: browser_get_url,
        definition: {
            type: "function",
            function: {
                name: "browser_get_url",
                description: "Get the current page URL.",
                parameters: {
                    type: "object",
                    properties: {},
                    required: [],
                },
            },
        },
    },
    browser_go_back: {
        execute: browser_go_back,
        definition: {
            type: "function",
            function: {
                name: "browser_go_back",
                description: "Navigate back in browser history.",
                parameters: {
                    type: "object",
                    properties: {},
                    required: [],
                },
            },
        },
    },
    browser_close: {
        execute: browser_close,
        definition: {
            type: "function",
            function: {
                name: "browser_close",
                description: "Close the browser instance and free resources.",
                parameters: {
                    type: "object",
                    properties: {},
                    required: [],
                },
            },
        },
    },
};

/**
 * Returns a dictionary of tools, filtered by an allowed list.
 * @param {string[] | null} allowedTools - A list of tool names to allow.
 * @returns {Object} The filtered tools object.
 */
export function getFilteredTools(allowedTools = null) {
    if (!allowedTools) {
        return TOOLS;
    }
    return Object.fromEntries(
        Object.entries(TOOLS).filter(([name]) => allowedTools.includes(name))
    );
}

/**
 * Returns the definitions of all available tools.
 * @param {Object} tools - The tools object to get definitions from.
 * @returns {Array<Object>} A list of tool definitions for the LLM.
 */
export function getToolDefinitions(tools) {
    return Object.values(tools).map(tool => tool.definition);
}