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
        self.screenshot_dir = os.path.join(os.getcwd(), 'screenshots')
        os.makedirs(self.screenshot_dir, exist_ok=True)

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
        
        # First check if npm is available
        if not self.check_command_exists('npm'):
            print("npm not found. Installing Node.js first...")
            self.install_node()
            
        # Install or update Appium
        print("\nInstalling/Updating Appium...")
        commands = [
            'npm install -g appium@latest',
            'npm install -g appium-doctor',
        ]

        for cmd in commands:
            print(f"\nRunning: {cmd}")
            code, out, err = self.run_command(cmd)
            if code != 0:
                print(f"Error running {cmd}:")
                print(err)
                return False
                
        # Install XCUITest driver
        print("\nInstalling XCUITest driver...")
        code, out, err = self.run_command('appium driver install xcuitest')
        if code != 0:
            print("Error installing XCUITest driver:")
            print(err)
            return False
            
        # Run appium-doctor to check setup
        print("\nChecking Appium setup with appium-doctor...")
        self.run_command('appium-doctor --ios')
        
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
        print("Setting up Appium environment...")
        
        # Install Node.js if needed
        if not self.check_command_exists('node'):
            self.install_node()
        
        # Install/Update Appium and drivers
        if not self.check_command_exists('appium') or not self.check_command_exists('appium-doctor'):
            if not self.install_appium():
                print("Failed to install Appium. Please check the errors above.")
                sys.exit(1)
        
        # Check iOS dependencies
        if not self.check_ios_dependencies():
            print("\nPlease install the missing dependencies and try again.")
            sys.exit(1)
        
        # Create Appium home and log directories
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        print("\nSetup completed successfully!")

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
            print(f"Device with UDID {udid} not found")
            return False

        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Warning: Error quitting previous driver: {e}")
            self.driver = None

        print(f"\nSetting up Appium session for device: {device['name']} ({device['udid']})")
        
        # Verify Appium installation
        _, appium_version, _ = self.run_command('appium --version')
        print(f"Appium version: {appium_version}")
        
        # Check XCUITest driver
        _, drivers, _ = self.run_command('appium driver list --installed')
        print(f"Installed drivers: {drivers}")
        
        if 'xcuitest' not in drivers.lower():
            print("Installing XCUITest driver...")
            self.run_command('appium driver install xcuitest')

        options = XCUITestOptions()
        options.platformName = 'iOS'
        options.automationName = 'XCUITest'
        options.udid = device['udid']
        options.deviceName = device['name']
        options.xcodeOrgId = os.getenv('TEAM_ID', '')
        options.xcodeSigningId = 'iPhone Developer'
        
        # Additional capabilities for better session creation
        if device['is_simulator']:
            options.platformVersion = device['version']
        else:
            options.platformVersion = device.get('version', '')
            options.usePrebuiltWda = True
            options.useXctestrunFile = False
            options.skipLogCapture = True
            options.wdaLaunchTimeout = 120000
            options.wdaConnectionTimeout = 120000
            options.webDriverAgentUrl = None

        print("\nAppium capabilities:")
        print(json.dumps(options.capabilities, indent=2))

        try:
            print("\nCreating Appium session...")
            self.driver = WebDriver(
                command_executor=f'http://localhost:{self.port}',
                options=options
            )
            print("Session created successfully")
            self.selected_device = device
            return True
        except Exception as e:
            print(f"\nError creating Appium session:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("\nPlease check:")
            print("1. WebDriverAgent is properly set up")
            print("2. Device is unlocked and trusted")
            print("3. Xcode and iOS development certificates are properly configured")
            print("4. TEAM_ID environment variable is set correctly")
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

    def check_session(self) -> bool:
        """Check if there's an active Appium session and device selected."""
        if not self.driver or not self.selected_device:
            return False
        try:
            # Try to get device time to verify session is active
            self.driver.get_device_time()
            return True
        except:
            return False

    def get_device_info(self) -> Dict:
        """Get detailed information about the currently selected device."""
        if not self.check_session():
            raise Exception("No active device session")

        try:
            info = {
                'device': self.selected_device,
                'battery': self.driver.get_battery_info(),
                'time': self.driver.get_device_time(),
                'orientation': self.driver.orientation,
            }
            
            # Get additional device info using ideviceinfo if available
            if not self.selected_device['is_simulator'] and self.check_command_exists('ideviceinfo'):
                udid = self.selected_device['udid']
                properties = [
                    'ProductType', 'ProductVersion', 'BuildVersion',
                    'DeviceName', 'DeviceClass', 'CPUArchitecture'
                ]
                for prop in properties:
                    _, value, _ = self.run_command(f'ideviceinfo -u {udid} -k {prop}')
                    if value:
                        info[prop.lower()] = value.strip()
                        
            return info
        except Exception as e:
            raise Exception(f"Failed to get device info: {str(e)}")

    def take_screenshot(self) -> str:
        """Take a screenshot of the device and return the file path."""
        if not self.check_session():
            raise Exception("No active device session")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            self.driver.get_screenshot_as_file(filepath)
            return filepath
        except Exception as e:
            raise Exception(f"Failed to take screenshot: {str(e)}")

    def set_orientation(self, orientation: str) -> str:
        """Set the device orientation (PORTRAIT or LANDSCAPE)."""
        if not self.check_session():
            raise Exception("No active device session")
            
        orientation = orientation.upper()
        if orientation not in ['PORTRAIT', 'LANDSCAPE']:
            raise ValueError("Orientation must be either 'PORTRAIT' or 'LANDSCAPE'")
            
        try:
            self.driver.orientation = orientation
            return self.driver.orientation
        except Exception as e:
            raise Exception(f"Failed to set orientation: {str(e)}")

    def lock_device(self) -> bool:
        """Lock the device screen."""
        if not self.check_session():
            raise Exception("No active device session")
            
        try:
            self.driver.lock()
            return True
        except Exception as e:
            raise Exception(f"Failed to lock device: {str(e)}")

    def unlock_device(self) -> bool:
        """Unlock the device screen."""
        if not self.check_session():
            raise Exception("No active device session")
            
        try:
            self.driver.unlock()
            return True
        except Exception as e:
            raise Exception(f"Failed to unlock device: {str(e)}")

    def press_home(self) -> bool:
        """Press the home button."""
        if not self.check_session():
            raise Exception("No active device session")
            
        try:
            # Using mobile: pressButton command for iOS
            self.driver.execute_script('mobile: pressButton', {'name': 'home'})
            return True
        except Exception as e:
            raise Exception(f"Failed to press home button: {str(e)}")

    def launch_app(self, bundle_id: str) -> bool:
        """Launch an application by bundle ID."""
        if not self.check_session():
            raise Exception("No active device session")
            
        try:
            self.driver.activate_app(bundle_id)
            return True
        except Exception as e:
            raise Exception(f"Failed to launch app: {str(e)}")

    def close_app(self, bundle_id: str) -> bool:
        """Close an application by bundle ID."""
        if not self.check_session():
            raise Exception("No active device session")
            
        try:
            self.driver.terminate_app(bundle_id)
            return True
        except Exception as e:
            raise Exception(f"Failed to close app: {str(e)}")

    def is_app_installed(self, bundle_id: str) -> bool:
        """Check if an application is installed."""
        if not self.check_session():
            raise Exception("No active device session")
            
        try:
            return self.driver.is_app_installed(bundle_id)
        except Exception as e:
            raise Exception(f"Failed to check app installation: {str(e)}")

    def install_app(self, app_path: str) -> bool:
        """Install an application from .ipa file."""
        if not self.check_session():
            raise Exception("No active device session")
            
        if not os.path.exists(app_path):
            raise FileNotFoundError(f"App file not found: {app_path}")
            
        try:
            self.driver.install_app(app_path)
            return True
        except Exception as e:
            raise Exception(f"Failed to install app: {str(e)}")

    def uninstall_app(self, bundle_id: str) -> bool:
        """Uninstall an application by bundle ID."""
        if not self.check_session():
            raise Exception("No active device session")
            
        try:
            self.driver.remove_app(bundle_id)
            return True
        except Exception as e:
            raise Exception(f"Failed to uninstall app: {str(e)}")

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

@app.route('/device/info', methods=['GET'])
def get_device_info():
    """Get detailed information about the current device."""
    try:
        info = manager.get_device_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/device/screenshot', methods=['GET'])
def take_screenshot():
    """Take a screenshot of the current device."""
    try:
        filepath = manager.take_screenshot()
        return jsonify({
            'success': True,
            'filepath': filepath,
            'filename': os.path.basename(filepath)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/device/orientation', methods=['GET', 'POST'])
def device_orientation():
    """Get or set device orientation."""
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data or 'orientation' not in data:
                return jsonify({'error': 'Orientation is required'}), 400
            orientation = manager.set_orientation(data['orientation'])
            return jsonify({'success': True, 'orientation': orientation})
        else:
            info = manager.get_device_info()
            return jsonify({'orientation': info['orientation']})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/device/lock', methods=['POST'])
def lock_device():
    """Lock the device screen."""
    try:
        success = manager.lock_device()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/device/unlock', methods=['POST'])
def unlock_device():
    """Unlock the device screen."""
    try:
        success = manager.unlock_device()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/device/home', methods=['POST'])
def press_home():
    """Press the home button."""
    try:
        success = manager.press_home()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/app/launch', methods=['POST'])
def launch_app():
    """Launch an application by bundle ID."""
    data = request.get_json()
    if not data or 'bundle_id' not in data:
        return jsonify({'error': 'Bundle ID is required'}), 400
        
    try:
        success = manager.launch_app(data['bundle_id'])
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/app/close', methods=['POST'])
def close_app():
    """Close an application by bundle ID."""
    data = request.get_json()
    if not data or 'bundle_id' not in data:
        return jsonify({'error': 'Bundle ID is required'}), 400
        
    try:
        success = manager.close_app(data['bundle_id'])
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/app/installed', methods=['GET'])
def is_app_installed():
    """Check if an application is installed."""
    bundle_id = request.args.get('bundle_id')
    if not bundle_id:
        return jsonify({'error': 'Bundle ID is required'}), 400
        
    try:
        is_installed = manager.is_app_installed(bundle_id)
        return jsonify({'installed': is_installed})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/app/install', methods=['POST'])
def install_app():
    """Install an application from .ipa file."""
    data = request.get_json()
    if not data or 'app_path' not in data:
        return jsonify({'error': 'App path is required'}), 400
        
    try:
        success = manager.install_app(data['app_path'])
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/app/uninstall', methods=['POST'])
def uninstall_app():
    """Uninstall an application by bundle ID."""
    data = request.get_json()
    if not data or 'bundle_id' not in data:
        return jsonify({'error': 'Bundle ID is required'}), 400
        
    try:
        success = manager.uninstall_app(data['bundle_id'])
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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