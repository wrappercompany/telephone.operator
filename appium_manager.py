#!/usr/bin/env python3

# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "flask==3.0.2",
#   "appium-python-client==3.1.1",
#   "requests==2.31.0"
# ]
# ///

import os
import sys
import subprocess
import time
import signal
import platform
import json
from typing import Optional, List, Dict
from datetime import datetime
from flask import Flask, jsonify, request
from appium.webdriver.webdriver import WebDriver
from appium.options.ios import XCUITestOptions

app = Flask(__name__)

class AppiumManager:
    def __init__(self):
        if platform.system() != 'Darwin':
            print("Error: This tool only supports macOS for iOS device testing")
            sys.exit(1)
            
        self.port = 4723
        self.web_port = 8080  # Changed from 5000 to 8080
        self.appium_home = os.path.expanduser('~/.appium')
        self.log_dir = os.path.join(self.appium_home, 'logs')
        self.log_file = os.path.join(self.log_dir, f'appium_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        self.connected_devices = []
        self.selected_device = None
        self.appium_process = None
        self.driver = None

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
            if platform.system() == 'Darwin':
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
            'appium driver install xcuitest',  # for iOS only
        ]

        for cmd in commands:
            print(f"Running: {cmd}")
            code, out, err = self.run_command(cmd)
            if code != 0:
                print(f"Error running {cmd}:")
                print(err)
                return False
        return True

    def check_ios_dependencies(self) -> bool:
        """Check if all required iOS dependencies are installed."""
        # Required dependencies
        required_dependencies = {
            'Xcode': lambda: self.run_command('xcode-select -p')[0] == 0,
            'libimobiledevice': lambda: self.check_command_exists('idevice_id')
        }
        
        # Optional dependencies
        optional_dependencies = {
            'Carthage': lambda: self.check_command_exists('carthage')
        }
        
        # Check required dependencies
        missing_required = []
        for dep, check in required_dependencies.items():
            if not check():
                missing_required.append(dep)
        
        # Check optional dependencies
        missing_optional = []
        for dep, check in optional_dependencies.items():
            if not check():
                missing_optional.append(dep)
        
        if missing_required:
            print("\nMissing required dependencies:")
            if 'Xcode' in missing_required:
                print("- Xcode: Install from the App Store")
            if 'libimobiledevice' in missing_required:
                print("- libimobiledevice: Run 'brew install libimobiledevice'")
            return False
            
        if missing_optional:
            print("\nMissing optional dependencies (not required for basic functionality):")
            if 'Carthage' in missing_optional:
                print("- Carthage: Run 'brew install carthage' if needed for advanced features")
            
        return True

    def check_port_in_use(self) -> Optional[int]:
        """Check if Appium port is in use and return the PID if it is."""
        code, out, _ = self.run_command(f'lsof -ti :{self.port}')
        return int(out) if code == 0 and out else None

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
        
        if not self.check_ios_dependencies():
            print("\nPlease install the missing dependencies and try again.")
            sys.exit(1)
        
        # Create Appium home and log directories if they don't exist
        os.makedirs(self.log_dir, exist_ok=True)

    def detect_ios_devices(self) -> List[Dict[str, str]]:
        """Detect connected iOS devices using multiple methods."""
        devices = []
        
        # Try xcrun first (preferred method)
        code, out, _ = self.run_command('xcrun xctrace list devices')
        if code == 0:
            lines = out.split('\n')
            current_os = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is an OS version line
                if line.startswith('== '):
                    current_os = line.strip('= ').strip()
                    continue
                
                # Skip Unavailable devices
                if 'Unavailable' in line:
                    continue
                    
                # Check for device line
                if '(' in line and ')' in line:
                    try:
                        # Split into name and identifier parts
                        name_part = line.split('(')[0].strip()
                        identifier_part = line.split('(')[1].split(')')[0].strip()
                        
                        # Skip if it's not a device line we're interested in
                        if not any(x in line.lower() for x in ['mac', 'iphone', 'ipad', 'ipod']):
                            continue
                            
                        # Determine device type and status
                        is_mac = 'mac' in line.lower()
                        is_simulator = 'simulator' in line.lower()
                        device_type = 'Mac' if is_mac else 'iOS'
                        
                        # For physical iOS devices, get the version using ideviceinfo
                        version = ''
                        if device_type == 'iOS' and not is_simulator:
                            if self.check_command_exists('ideviceinfo'):
                                _, dev_version, _ = self.run_command(f'ideviceinfo -u {identifier_part} -k ProductVersion')
                                if dev_version:
                                    version = dev_version
                        # For simulators, version is usually in the identifier
                        elif is_simulator:
                            version = identifier_part
                        # For Mac, use the current OS version
                        elif device_type == 'Mac':
                            version = current_os if current_os else ''
                        
                        device = {
                            'name': name_part,
                            'udid': identifier_part,
                            'platform': device_type.lower(),
                            'type': device_type,
                            'version': version,
                            'is_simulator': is_simulator
                        }
                        
                        # Only add the device if we haven't seen it before
                        if not any(d['udid'] == device['udid'] for d in devices):
                            devices.append(device)
                            
                    except Exception as e:
                        print(f"Error parsing device line: {line}")
                        print(f"Error: {str(e)}")
                        continue
        
        # If no physical devices found, try idevice_id as backup
        if not any(not d['is_simulator'] for d in devices):
            if self.check_command_exists('idevice_id'):
                code, out, _ = self.run_command('idevice_id -l')
                if code == 0:
                    for udid in out.split('\n'):
                        if udid.strip():
                            device_info = {'name': 'iOS Device', 'version': '', 'type': 'iOS'}
                            
                            # Get device name
                            if self.check_command_exists('idevicename'):
                                _, name, _ = self.run_command(f'idevicename -u {udid}')
                                if name:
                                    device_info['name'] = name
                            
                            # Get iOS version
                            if self.check_command_exists('ideviceinfo'):
                                _, version, _ = self.run_command(f'ideviceinfo -u {udid} -k ProductVersion')
                                if version:
                                    device_info['version'] = version
                            
                            devices.append({
                                **device_info,
                                'udid': udid.strip(),
                                'platform': 'ios',
                                'is_simulator': False
                            })
        
        return devices

    def detect_connected_devices(self):
        """Detect connected devices."""
        print("Detecting connected devices...")
        
        self.connected_devices = self.detect_ios_devices()
        
        if self.connected_devices:
            print("\nFound connected devices:")
            
            # Group devices by type
            real_devices = [d for d in self.connected_devices if not d['is_simulator']]
            simulators = [d for d in self.connected_devices if d['is_simulator']]
            
            # Print real devices first
            if real_devices:
                print("\nPhysical Devices:")
                for device in real_devices:
                    device_info = [
                        f"- {device['name']}",
                        f"Type: {device['type']}"
                    ]
                    
                    if device['version']:
                        if device['type'] == 'iOS':
                            device_info.append(f"iOS: {device['version']}")
                        else:
                            device_info.append(f"Version: {device['version']}")
                    
                    device_info.append(f"UDID: {device['udid']}")
                    print(" | ".join(device_info))
            
            # Then print simulators if any
            if simulators:
                print("\nSimulators:")
                for device in simulators:
                    device_info = [
                        f"- {device['name']}",
                        f"iOS: {device['version']}"
                    ]
                    print(" | ".join(device_info))
        else:
            print("No devices detected")
        print()

    def start_server(self):
        """Start the Appium server."""
        # Check and kill existing process
        pid = self.check_port_in_use()
        if pid:
            print(f"Port {self.port} is in use. Killing existing process...")
            self.kill_existing_process(pid)

        # Detect connected devices before starting server
        self.detect_connected_devices()

        print(f"\nStarting Appium server on port {self.port}...")
        print(f"Logs will be written to: {self.log_file}")
        print("Only errors will be displayed here.")
        print("-" * 40)

        # Prepare Appium command
        cmd = [
            'appium',
            '--allow-insecure', 'chromedriver_autodownload',
            '--base-path', '/',
            '--relaxed-security',
            '--log-timestamp',
            '--local-timezone',
            '--no-perms-check',
            '--log-level', 'debug',  # Log everything to file
            '--log', self.log_file,  # Write logs to file
            '--debug-log-spacing',   # Better log formatting
        ]

        # Start Appium server
        try:
            self.appium_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            time.sleep(2)  # Wait for server to start
            
        except Exception as e:
            print(f"\nError starting Appium server: {e}")
            sys.exit(1)

    def select_device(self, udid: str) -> bool:
        """Select a device by UDID and create an Appium session."""
        device = next((d for d in self.connected_devices if d['udid'] == udid), None)
        if not device:
            return False

        if self.driver:
            self.driver.quit()
            self.driver = None

        options = XCUITestOptions()
        options.platformName = 'iOS'
        options.automationName = 'XCUITest'
        options.udid = device['udid']
        options.deviceName = device['name']
        options.xcodeOrgId = os.getenv('TEAM_ID', '')
        options.xcodeSigningId = 'iPhone Developer'

        try:
            self.driver = WebDriver(
                command_executor=f'http://localhost:{self.port}',
                options=options
            )
            self.selected_device = device
            return True
        except Exception as e:
            print(f"Error creating Appium session: {e}")
            return False

    def stop_server(self):
        """Stop the Appium server and cleanup."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            
        if self.appium_process:
            self.appium_process.terminate()
            try:
                self.appium_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.appium_process.kill()
            print("Appium server stopped")

# Flask routes
@app.route('/devices', methods=['GET'])
def get_devices():
    """Get list of connected devices."""
    manager.detect_connected_devices()
    return jsonify(manager.connected_devices)

@app.route('/device/select', methods=['POST'])
def select_device():
    """Select a device by UDID."""
    data = request.get_json()
    if not data or 'udid' not in data:
        return jsonify({'error': 'UDID is required'}), 400
        
    if manager.select_device(data['udid']):
        return jsonify({'success': True, 'device': manager.selected_device})
    else:
        return jsonify({'error': 'Failed to select device'}), 400

@app.route('/device/current', methods=['GET'])
def get_current_device():
    """Get currently selected device."""
    if manager.selected_device:
        return jsonify(manager.selected_device)
    else:
        return jsonify({'error': 'No device selected'}), 404

def main():
    global manager
    manager = AppiumManager()
    try:
        manager.setup()
        manager.start_server()
        # Start Flask server
        app.run(host='0.0.0.0', port=manager.web_port)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        manager.stop_server()
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        manager.stop_server()
        sys.exit(1)

if __name__ == '__main__':
    main() 