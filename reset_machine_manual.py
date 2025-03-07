import os
import sys
import json
import uuid
import hashlib
import shutil
import sqlite3
import platform
import re
import tempfile
import subprocess
from colorama import Fore, Style, init
from typing import Tuple, Optional

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
}

def get_cursor_paths(translator=None, appimage_dir=None) -> Tuple[str, str]:
    """ Get Cursor related paths"""
    system = platform.system()

    # If we're using an extracted AppImage directory, use that instead of system paths
    if appimage_dir and system == "Linux":
        # AppImage structure - paths are relative to the extracted directory
        app_dir = os.path.join(appimage_dir, "resources", "app")
        return (
            os.path.join(app_dir, "package.json"),
            os.path.join(app_dir, "out", "main.js")
        )

    paths_map = {
        "Darwin": {
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "package": "package.json",
            "main": "out/main.js",
        },
        "Windows": {
            "base": os.path.join(
                os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"
            ),
            "package": "package.json",
            "main": "out/main.js",
        },
        "Linux": {
            "bases": ["/resources/app"], # Relative to extracted AppImage directory
            "package": "package.json",
            "main": "out/main.js",
        },
    }

    if system not in paths_map:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")

    if system == "Linux":
        for base in paths_map["Linux"]["bases"]:
            pkg_path = os.path.join(base, paths_map["Linux"]["package"])
            if os.path.exists(pkg_path):
                return (pkg_path, os.path.join(base, paths_map["Linux"]["main"]))
        raise OSError(translator.get('reset.linux_path_not_found') if translator else "在 Linux 系统上未找到 Cursor 安装路径")

    base_path = paths_map[system]["base"]
    return (
        os.path.join(base_path, paths_map[system]["package"]),
        os.path.join(base_path, paths_map[system]["main"]),
    )

def get_cursor_machine_id_path(translator=None) -> str:
    """
    Get Cursor machineId file path based on operating system
    Returns:
        str: Path to machineId file
    """
    if sys.platform == "win32":  # Windows
        return os.path.join(os.getenv("APPDATA"), "Cursor", "machineId")
    elif sys.platform == "linux":  # Linux
        return os.path.expanduser("~/.config/Cursor/machineId")
    elif sys.platform == "darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/Cursor/machineId")
    else:
        raise OSError(f"Unsupported operating system: {sys.platform}")

def get_workbench_cursor_path(translator=None) -> str:
    """Get Cursor workbench.desktop.main.js path"""
    system = platform.system()
    
    paths_map = {
        "Darwin": {  # macOS
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {
            "base": os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"),
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Linux": {
            "bases": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app"],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }

    if system not in paths_map:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")

    if system == "Linux":
        for base in paths_map["Linux"]["bases"]:
            main_path = os.path.join(base, paths_map["Linux"]["main"])
            if os.path.exists(main_path):
                return main_path
        raise OSError(translator.get('reset.linux_path_not_found') if translator else "在 Linux 系统上未找到 Cursor 安装路径")

    base_path = paths_map[system]["base"]
    main_path = os.path.join(base_path, paths_map[system]["main"])
    
    if not os.path.exists(main_path):
        raise OSError(translator.get('reset.file_not_found', path=main_path) if translator else f"未找到 Cursor main.js 文件: {main_path}")
        
    return main_path

def version_check(version: str, min_version: str = "", max_version: str = "", translator=None) -> bool:
    """Version number check"""
    version_pattern = r"^\d+\.\d+\.\d+$"
    try:
        if not re.match(version_pattern, version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version)}{Style.RESET_ALL}")
            return False

        def parse_version(ver: str) -> Tuple[int, ...]:
            return tuple(map(int, ver.split(".")))

        current = parse_version(version)

        if min_version and current < parse_version(min_version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_too_low', version=version, min_version=min_version)}{Style.RESET_ALL}")
            return False

        if max_version and current > parse_version(max_version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_too_high', version=version, max_version=max_version)}{Style.RESET_ALL}")
            return False

        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_check_error', error=str(e))}{Style.RESET_ALL}")
        return False

def extract_appimage(appimage_path, translator):
    """Extract AppImage to a temporary directory"""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.extracting_appimage')}...{Style.RESET_ALL}")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="cursor_appimage_")
        
        # Check if the AppImage file exists
        if not os.path.isfile(appimage_path):
            raise FileNotFoundError(f"AppImage file not found: {appimage_path}")
            
        # Make sure AppImage is executable
        os.chmod(appimage_path, os.stat(appimage_path).st_mode | 0o100)
        
        # Extract AppImage (using --appimage-extract)
        cmd = [appimage_path, "--appimage-extract"]
        result = subprocess.run(cmd, cwd=temp_dir, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        
        if result.returncode != 0:
            error = result.stderr.decode('utf-8', errors='ignore')
            raise Exception(f"Failed to extract AppImage: {error}")
            
        extracted_dir = os.path.join(temp_dir, "squashfs-root")
        if not os.path.isdir(extracted_dir):
            raise Exception("Extraction directory not found after extraction")
            
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.appimage_extracted')}: {temp_dir}{Style.RESET_ALL}")
        return extracted_dir
        
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.extract_failed', error=str(e))}{Style.RESET_ALL}")
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None

def rebuild_appimage(appimage_path, extracted_dir, translator):
    """Rebuild AppImage after modifications"""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.rebuilding_appimage')}...{Style.RESET_ALL}")
        
        # Create backup of original AppImage
        backup_path = f"{appimage_path}.bak"
        if not os.path.exists(backup_path):
            print(f"{Fore.CYAN}{EMOJI['BACKUP']} {translator.get('reset.creating_appimage_backup')}...{Style.RESET_ALL}")
            shutil.copy2(appimage_path, backup_path)
        
        # Get directory containing the AppImage
        appimage_dir = os.path.dirname(appimage_path)
        appimage_name = os.path.basename(appimage_path)
        
        # If appimagetool is available, use it to rebuild
        appimagetool_paths = [
            "appimagetool",  # If in PATH
            "/usr/local/bin/appimagetool",
            "/usr/bin/appimagetool",
            os.path.expanduser("~/bin/appimagetool"),
            os.path.expanduser("~/.local/bin/appimagetool")
        ]
        
        appimagetool_path = None
        for path in appimagetool_paths:
            try:
                subprocess.run([path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                appimagetool_path = path
                break
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        if appimagetool_path:
            # Use appimagetool to rebuild
            new_appimage = os.path.join(appimage_dir, f"{appimage_name}.new")
            cmd = [appimagetool_path, extracted_dir, new_appimage]
            print(f"{Fore.CYAN}{EMOJI['INFO']} Running: {' '.join(cmd)}{Style.RESET_ALL}")
            
            result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            
            if result.returncode != 0:
                error = result.stderr.decode('utf-8', errors='ignore')
                raise Exception(f"Failed to rebuild AppImage: {error}")
                
            # Replace original with new version
            shutil.move(new_appimage, appimage_path)
            os.chmod(appimage_path, os.stat(backup_path).st_mode)  # Copy permissions
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.appimage_rebuilt')}{Style.RESET_ALL}")
            return True
        else:
            # If appimagetool not found, provide detailed instructions
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.appimagetool_not_found')}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'─' * 60}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}To install appimagetool:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}1. Download from: https://github.com/AppImage/AppImageKit/releases{Style.RESET_ALL}")
            print(f"{Fore.WHITE}2. Make it executable: chmod +x appimagetool-*.AppImage{Style.RESET_ALL}")
            print(f"{Fore.WHITE}3. Move to path: sudo mv appimagetool-*.AppImage /usr/local/bin/appimagetool{Style.RESET_ALL}")
            print(f"{Fore.WHITE}Or with wget: wget -O appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage && chmod +x appimagetool && sudo mv appimagetool /usr/local/bin/{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'─' * 60}{Style.RESET_ALL}")
            
            # Provide command for manual rebuilding
            rebuild_cmd = f"appimagetool {extracted_dir} {appimage_path}"
            print(f"{Fore.WHITE}To manually rebuild:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{rebuild_cmd}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'─' * 60}{Style.RESET_ALL}")
            
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.manual_rebuild_instructions', extracted=extracted_dir)}{Style.RESET_ALL}")
            
            # Return False but don't display error, since we've given instructions
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.rebuild_appimage_failed')}{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.rebuild_failed', error=str(e))}{Style.RESET_ALL}")
        return False
    finally:
        # Cleanup is handled elsewhere
        pass

def check_cursor_version(translator, appimage_dir=None) -> bool:
    """Check Cursor version"""
    try:
        pkg_path, _ = get_cursor_paths(translator, appimage_dir)
        with open(pkg_path, "r", encoding="utf-8") as f:
            version = json.load(f)["version"]
        return version_check(version, min_version="0.45.0", translator=translator)
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.check_version_failed', error=str(e))}{Style.RESET_ALL}")
        return False

def modify_workbench_js(file_path: str, translator=None) -> bool:
    """
    Modify file content
    """
    try:
        # Save original file permissions
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False) as tmp_file:
            # Read original content
            with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                content = main_file.read()

            if sys.platform == "win32":
                # Define replacement patterns
                CButton_old_pattern = r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'$(k,E(Ks,{title:"yeongpin GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)'
            elif sys.platform == "linux":
                CButton_old_pattern = r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'$(k,E(Ks,{title:"yeongpin GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)'
            elif sys.platform == "darwin":
                CButton_old_pattern = r'M(x,I(as,{title:"Upgrade to Pro",size:"small",get codicon(){return $.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'M(x,I(as,{title:"yeongpin GitHub",size:"small",get codicon(){return $.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)'

            CBadge_old_pattern = r'<div>Pro Trial'
            CBadge_new_pattern = r'<div>Pro'

            CToast_old_pattern = r'notifications-toasts'
            CToast_new_pattern = r'notifications-toasts hidden'

            # Replace content
            content = content.replace(CButton_old_pattern, CButton_new_pattern)
            content = content.replace(CBadge_old_pattern, CBadge_new_pattern)
            content = content.replace(CToast_old_pattern, CToast_new_pattern)

            # Write to temporary file
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Backup original file
        backup_path = file_path + ".backup"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        shutil.copy2(file_path, backup_path)
        
        # Move temporary file to original position
        if os.path.exists(file_path):
            os.remove(file_path)
        shutil.move(tmp_path, file_path)

        # Restore original permissions
        os.chmod(file_path, original_mode)
        if os.name != "nt":  # Not Windows
            os.chown(file_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        return False

def modify_main_js(main_path: str, translator) -> bool:
    """Modify main.js file"""
    try:
        original_stat = os.stat(main_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            with open(main_path, "r", encoding="utf-8") as main_file:
                content = main_file.read()

            patterns = {
                r"async getMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMachineId(){return \1}",
                r"async getMacMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMacMachineId(){return \1}",
            }

            for pattern, replacement in patterns.items():
                content = re.sub(pattern, replacement, content)

            tmp_file.write(content)
            tmp_path = tmp_file.name

        shutil.copy2(main_path, main_path + ".old")
        shutil.move(tmp_path, main_path)

        os.chmod(main_path, original_mode)
        if os.name != "nt":
            os.chown(main_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            os.unlink(tmp_path)
        return False

def handle_appimage_patching(app_image_path, translator) -> bool:
    """Handle patching of Cursor AppImage file"""
    if not app_image_path:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_appimage_path')}{Style.RESET_ALL}")
        return False
        
    # Convert relative path to absolute path
    app_image_path = os.path.abspath(os.path.expanduser(app_image_path))
    
    # Check if AppImage exists
    if not os.path.isfile(app_image_path):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.appimage_not_found', path=app_image_path)}{Style.RESET_ALL}")
        return False
        
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.processing_appimage', path=app_image_path)}{Style.RESET_ALL}")
    
    try:
        # Extract AppImage contents
        extracted_dir = extract_appimage(app_image_path, translator)
        if not extracted_dir:
            return False
            
        # Get paths within extracted AppImage
        pkg_path, main_path = get_cursor_paths(translator, extracted_dir)
        
        # Check version
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.checking_appimage_version')}...{Style.RESET_ALL}")
        if not check_cursor_version(translator, extracted_dir):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.appimage_version_not_supported')}{Style.RESET_ALL}")
            return False
            
        # Backup and modify main.js in the extracted directory
        if not modify_main_js(main_path, translator):
            return False
            
        # Rebuild AppImage
        if not rebuild_appimage(app_image_path, extracted_dir, translator):
            return False
            
        return True
    finally:
        # Clean up temporary directory if it exists
        if 'extracted_dir' in locals() and extracted_dir and os.path.exists(os.path.dirname(extracted_dir)):
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.cleaning_temp_files')}...{Style.RESET_ALL}")
            shutil.rmtree(os.path.dirname(extracted_dir), ignore_errors=True)
    
    return False

def patch_cursor_get_machine_id(translator, app_image_path=None) -> bool:
    """Patch Cursor getMachineId function"""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.start_patching')}...{Style.RESET_ALL}")
        
        # If we're on Linux and an AppImage path is provided, use AppImage patching
        if platform.system() == "Linux" and app_image_path:
            return handle_appimage_patching(app_image_path, translator)
        
        # Get paths
        pkg_path, main_path = get_cursor_paths(translator)
        
        # Check file permissions
        for file_path in [pkg_path, main_path]:
            if not os.path.isfile(file_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.file_not_found', path=file_path)}{Style.RESET_ALL}")
                return False
            if not os.access(file_path, os.W_OK):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_write_permission', path=file_path)}{Style.RESET_ALL}")
                return False

        # Get version number
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                version = json.load(f)["version"]
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.current_version', version=version)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.read_version_failed', error=str(e))}{Style.RESET_ALL}")
            return False

        # Check version
        if not version_check(version, min_version="0.45.0", translator=translator):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_not_supported')}{Style.RESET_ALL}")
            return False

        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.version_check_passed')}{Style.RESET_ALL}")

        # Backup file
        backup_path = main_path + ".bak"
        if not os.path.exists(backup_path):
            shutil.copy2(main_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")

        # Modify file
        if not modify_main_js(main_path, translator):
            return False

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.patch_completed')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed', error=str(e))}{Style.RESET_ALL}")
        return False

class MachineIDResetter:
    def __init__(self, translator=None):
        self.translator = translator

        # Check operating system
        if sys.platform == "win32":  # Windows
            appdata = os.getenv("APPDATA")
            if appdata is None:
                raise EnvironmentError("APPDATA Environment Variable Not Set")
            self.db_path = os.path.join(
                appdata, "Cursor", "User", "globalStorage", "storage.json"
            )
            self.sqlite_path = os.path.join(
                appdata, "Cursor", "User", "globalStorage", "state.vscdb"
            )
        elif sys.platform == "darwin":  # macOS
            self.db_path = os.path.abspath(os.path.expanduser(
                "~/Library/Application Support/Cursor/User/globalStorage/storage.json"
            ))
            self.sqlite_path = os.path.abspath(os.path.expanduser(
                "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
            ))
        elif sys.platform == "linux":  # Linux
            # 获取实际用户的主目录
            sudo_user = os.environ.get('SUDO_USER')
            if sudo_user:
                actual_home = f"/home/{sudo_user}"
            else:
                actual_home = os.path.expanduser("~")
                
            self.db_path = os.path.abspath(os.path.join(
                actual_home,
                ".config/Cursor/User/globalStorage/storage.json"
            ))
            self.sqlite_path = os.path.abspath(os.path.join(
                actual_home,
                ".config/Cursor/User/globalStorage/state.vscdb"
            ))
        else:
            raise NotImplementedError(f"Not Supported OS: {sys.platform}")

    def generate_new_ids(self):
        """Generate new machine ID"""
        # Generate new UUID
        dev_device_id = str(uuid.uuid4())

        # Generate new machineId (64 characters of hexadecimal)
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()

        # Generate new macMachineId (128 characters of hexadecimal)
        mac_machine_id = hashlib.sha512(os.urandom(64)).hexdigest()

        # Generate new sqmId
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}"

        self.update_machine_id_file(dev_device_id)

        return {
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.macMachineId": mac_machine_id,
            "telemetry.machineId": machine_id,
            "telemetry.sqmId": sqm_id,
            "storage.serviceMachineId": dev_device_id,  # Add storage.serviceMachineId
        }

    def update_sqlite_db(self, new_ids):
        """Update machine ID in SQLite database"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_sqlite')}...{Style.RESET_ALL}")
            
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            updates = [
                (key, value) for key, value in new_ids.items()
            ]

            for key, value in updates:
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value) 
                    VALUES (?, ?)
                """, (key, value))
                print(f"{EMOJI['INFO']} {Fore.CYAN} {self.translator.get('reset.updating_pair')}: {key}{Style.RESET_ALL}")

            conn.commit()
            conn.close()
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.sqlite_success')}{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def update_system_ids(self, new_ids):
        """Update system-level IDs"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_system_ids')}...{Style.RESET_ALL}")
            
            if sys.platform.startswith("win"):
                self._update_windows_machine_guid()
            elif sys.platform == "darwin":
                self._update_macos_platform_uuid(new_ids)
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.system_ids_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.system_ids_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def _update_windows_machine_guid(self):
        """Update Windows MachineGuid"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Cryptography",
                0,
                winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
            )
            new_guid = str(uuid.uuid4())
            winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_guid)
            winreg.CloseKey(key)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.windows_machine_guid_updated')}{Style.RESET_ALL}")
        except PermissionError:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied')}{Style.RESET_ALL}")
            raise
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_machine_guid_failed', error=str(e))}{Style.RESET_ALL}")
            raise

    def _update_macos_platform_uuid(self, new_ids):
        """Update macOS Platform UUID"""
        try:
            uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist"
            if os.path.exists(uuid_file):
                # Use sudo to execute plutil command
                cmd = f'sudo plutil -replace "UUID" -string "{new_ids["telemetry.macMachineId"]}" "{uuid_file}"'
                result = os.system(cmd)
                if result == 0:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.macos_platform_uuid_updated')}{Style.RESET_ALL}")
                else:
                    raise Exception(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.failed_to_execute_plutil_command')}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_macos_platform_uuid_failed', error=str(e))}{Style.RESET_ALL}")
            raise

    def reset_machine_ids(self, app_image_path=None):
        """Reset machine ID and backup original file"""
        extracted_dir = None
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.checking')}...{Style.RESET_ALL}")

            # If AppImage path is provided, extract it first
            if app_image_path and os.path.isfile(app_image_path):
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.processing_appimage', path=app_image_path)}{Style.RESET_ALL}")
                extracted_dir = extract_appimage(app_image_path, self.translator)
                if not extracted_dir:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.appimage_extract_failed')}{Style.RESET_ALL}")
                    return False

            if not os.path.exists(self.db_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.not_found')}: {self.db_path}{Style.RESET_ALL}")
                return False

            if not os.access(self.db_path, os.R_OK | os.W_OK):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.no_permission')}{Style.RESET_ALL}")
                return False

            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.reading')}...{Style.RESET_ALL}")
            with open(self.db_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            backup_path = self.db_path + ".bak"
            if not os.path.exists(backup_path):
                print(f"{Fore.YELLOW}{EMOJI['BACKUP']} {self.translator.get('reset.creating_backup')}: {backup_path}{Style.RESET_ALL}")
                shutil.copy2(self.db_path, backup_path)
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.backup_exists')}{Style.RESET_ALL}")

            print(f"{Fore.CYAN}{EMOJI['RESET']} {self.translator.get('reset.generating')}...{Style.RESET_ALL}")
            new_ids = self.generate_new_ids()

            # Update configuration file
            config.update(new_ids)

            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.saving_json')}...{Style.RESET_ALL}")
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            # Update SQLite database
            self.update_sqlite_db(new_ids)

            # Update system IDs
            self.update_system_ids(new_ids)

            # Modify workbench.desktop.main.js
            workbench_path = get_workbench_cursor_path(self.translator)
            modify_workbench_js(workbench_path, self.translator)

            # Check Cursor version and perform corresponding actions
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.checking_cursor_version')}...{Style.RESET_ALL}")
            greater_than_0_45 = check_cursor_version(self.translator, extracted_dir)  # Pass extracted_dir here
            
            if (greater_than_0_45):
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.detecting_version')} >= 0.45.0，{self.translator.get('reset.patching_getmachineid')}{Style.RESET_ALL}")
                
                if app_image_path and os.path.isfile(app_image_path):
                    # If we have an AppImage, use extracted_dir for patching
                    if extracted_dir:
                        # Get main.js path in extracted AppImage
                        _, main_path = get_cursor_paths(self.translator, extracted_dir)
                        
                        # Patch main.js in extracted directory
                        if modify_main_js(main_path, self.translator):
                            # Rebuild AppImage with modified contents
                            if not rebuild_appimage(app_image_path, extracted_dir, self.translator):
                                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.rebuild_appimage_failed')}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.no_extracted_dir')}{Style.RESET_ALL}")
                else:
                    # Regular patching for non-AppImage installations
                    patch_cursor_get_machine_id(self.translator)
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.version_less_than_0_45')}{Style.RESET_ALL}")

            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.success')}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}{self.translator.get('reset.new_id')}:{Style.RESET_ALL}")
            for key, value in new_ids.items():
                print(f"{EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")

            return True

        except PermissionError as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_error', error=str(e))}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.run_as_admin')}{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.process_error', error=str(e))}{Style.RESET_ALL}")
            return False
        finally:
            # Clean up the extracted directory if it exists
            if extracted_dir and os.path.exists(os.path.dirname(extracted_dir)):
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.cleaning_temp_files')}...{Style.RESET_ALL}")
                try:
                    shutil.rmtree(os.path.dirname(extracted_dir), ignore_errors=True)
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.cleanup_error', error=str(e))}{Style.RESET_ALL}")

    def update_machine_id_file(self, machine_id: str) -> bool:
        """
        Update machineId file with new machine_id
        Args:
            machine_id (str): New machine ID to write
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the machineId file path
            machine_id_path = get_cursor_machine_id_path()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)

            # Create backup if file exists
            if os.path.exists(machine_id_path):
                backup_path = machine_id_path + ".backup"
                try:
                    shutil.copy2(machine_id_path, backup_path)
                    print(f"{Fore.GREEN}{EMOJI['INFO']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created at: {backup_path}'}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.backup_creation_failed', error=str(e)) if self.translator else f'Could not create backup: {str(e)}'}{Style.RESET_ALL}")

            # Write new machine ID to file
            with open(machine_id_path, "w", encoding="utf-8") as f:
                f.write(machine_id)

            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.update_success') if self.translator else 'Successfully updated machineId file'}{Style.RESET_ALL}")
            return True

        except Exception as e:
            error_msg = f"Failed to update machineId file: {str(e)}"
            if self.translator:
                error_msg = self.translator.get('reset.update_failed', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return False


def run(translator=None):
    """Convenient function for directly calling the reset function"""
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    # We can keep this message but don't need to normalize the path again
    if app_image_path:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.using_appimage', path=app_image_path)}{Style.RESET_ALL}")

    resetter = MachineIDResetter(translator)
    resetter.reset_machine_ids(app_image_path)

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('reset.press_enter')}...")

if __name__ == "__main__":
    from main import translator as main_translator
    # Get AppImage path from command line arguments if provided
    app_image_path = None
    if len(sys.argv) > 1 and '--appImage' in sys.argv:
        try:
            app_image_index = sys.argv.index('--appImage') + 1
            if app_image_index < len(sys.argv):
                app_image_path = sys.argv[app_image_index]
        except:
            pass
    
    run(main_translator, app_image_path)