#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Path to the main.py python script
const mainPyPath = path.join(__dirname, '..', 'main.py');

// Function to find the available python executable
function getPythonCommand() {
    // Check python inside agent_env first if it exists
    const localPythonWin = path.join(__dirname, '..', 'agent_env', 'Scripts', 'python.exe');
    const localPythonUnix = path.join(__dirname, '..', 'agent_env', 'bin', 'python');
    
    if (fs.existsSync(localPythonWin)) return localPythonWin;
    if (fs.existsSync(localPythonUnix)) return localPythonUnix;
    
    // Fallback to system python
    return process.platform === 'win32' ? 'python' : 'python3';
}

const pythonCmd = getPythonCommand();
const args = [mainPyPath, ...process.argv.slice(2)];

console.log(`[Heal Agent CLI] Launching agent using: ${pythonCmd}`);

// Spawn the Python process forwarding all inputs, outputs, and errors
const pythonProcess = spawn(pythonCmd, args, {
    stdio: 'inherit',
    shell: true
});

pythonProcess.on('error', (err) => {
    console.error(`[Error] Failed to start Python process: ${err.message}`);
    console.error(`Please ensure Python is installed and in your system PATH.`);
    process.exit(1);
});

pythonProcess.on('exit', (code) => {
    process.exit(code);
});
