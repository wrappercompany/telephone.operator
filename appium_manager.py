#!/usr/bin/env python3

import os
import sys
import subprocess
import time
import signal
import platform
from typing import Optional

class AppiumManager:
    def __init__(self):
        self.port = 4723
        self.is_mac = platform.system() == 'Darwin'
        self.node_min_version = '12.0.0'
        self.appium_home = os.path.expanduser('~/.appium')

    def run_command(self, command: str, shell: bool = False) -> tuple[int, str, str]:
        """Run a command and return returncode, stdout, stderr."""
        process = subprocess.Popen(
            command if shell else command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell
        )
        stdout, stderr = process.communicate()
        return (
            process.returncode,
            stdout.decode('utf-8').strip(),
            stderr.decode('utf-8').strip()
        )

    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists in the system."""
        return self.run_command(f'which {command}')[0] == 0

    def install_node_mac(self):
        """Install Node.js on macOS using Homebrew."""
        print("Installing Node.js...")
        if not self.check_command_exists('brew'):
            print("Installing Homebrew...")
            install_cmd = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            self.run_command(install_cmd, shell=True)
        self.run_command('brew install node')

    def install_node(self):
        """Install Node.js based on the operating system."""
        if not self.check_command_exists('node'):
            if self.is_mac:
                self.install_node_mac()
            else:
                print("Please install Node.js manually for your operating system")
                print("Visit: https://nodejs.org/")
                sys.exit(1)

    def install_appium(self):
        """Install Appium and its dependencies."""
        print("Installing Appium and dependencies...")
        commands = [
            'npm install -g appium',
            'npm install -g appium-doctor',
            'appium driver install xcuitest',  # for iOS
            'appium driver install uiautomator2'  # for Android
        ]

        for cmd in commands:
            print(f"Running: {cmd}")
            code, out, err = self.run_command(cmd)
            if code != 0:
                print(f"Error running {cmd}:")
                print(err)
                return False
        return True

    def check_port_in_use(self) -> Optional[int]:
        """Check if Appium port is in use and return the PID if it is."""
        if self.is_mac:
            code, out, _ = self.run_command(f'lsof -ti :{self.port}')
            return int(out) if code == 0 and out else None
        return None

    def kill_existing_process(self, pid: int):
        """Kill an existing process by PID."""
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)  # Give it a moment to terminate gracefully
            if self.check_port_in_use():  # If still running
                os.kill(pid, signal.SIGKILL)  # Force kill
            print(f"Killed existing process on port {self.port}")
        except ProcessLookupError:
            pass

    def setup(self):
        """Perform initial setup if needed."""
        self.install_node()
        
        if not self.check_command_exists('appium'):
            if not self.install_appium():
                print("Failed to install Appium. Please check the errors above.")
                sys.exit(1)
        
        # Create Appium home directory if it doesn't exist
        os.makedirs(self.appium_home, exist_ok=True)

    def start_server(self):
        """Start the Appium server."""
        # Check and kill existing process
        pid = self.check_port_in_use()
        if pid:
            print(f"Port {self.port} is in use. Killing existing process...")
            self.kill_existing_process(pid)

        print(f"\nStarting Appium server on port {self.port}...")
        print("Logs will appear below. Press Ctrl+C to stop the server.")
        print("-" * 40)

        # Prepare Appium command
        cmd = [
            'appium',
            '--allow-insecure', 'chromedriver_autodownload',
            '--base-path', '/',
            '--relaxed-security',
            '--log-timestamp',
            '--local-timezone',
            '--no-perms-check'
        ]

        # Start Appium server
        try:
            process = subprocess.Popen(cmd)
            process.wait()
        except KeyboardInterrupt:
            print("\nStopping Appium server...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            print("Appium server stopped")

def main():
    manager = AppiumManager()
    try:
        manager.setup()
        manager.start_server()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 