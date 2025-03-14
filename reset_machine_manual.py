import hashlib
import os
import sys
import json
import platform
import uuid
import sqlite3
import shutil
import subprocess
import tempfile
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
    "WARNING": "⚠️",
    "INFO": "ℹ️",
    "RESET": "🔄",
}

def get_machine_id_paths(translator=None, appimage_dir=None) -> Tuple[str, str]:
    """Get paths to machine ID related files"""
    system = platform.system()
    
    if appimage_dir and system == "Linux":
        # For AppImage, paths are relative to extracted directory
        app_dir = os.path.join(appimage_dir, "resources", "app")
        return (
            os.path.join(app_dir, "package.json"),
            os.path.join(app_dir, "out", "main.js")
        )

    home = os.path.expanduser("~")
    if system == "Darwin":
        cursor_config_dir = os.path.join(home, "Library", "Application Support", "cursor")
        package_path = "/Applications/Cursor.app/Contents/Resources/app/package.json"
        main_path = "/Applications/Cursor.app/Contents/Resources/app/out/main.js"
    elif system == "Windows":
        cursor_config_dir = os.path.join(os.getenv("APPDATA"), "cursor")
        package_path = os.path.join(os.getenv("LOCALAPPDATA"), "Programs", "Cursor", "resources", "app", "package.json")
        main_path = os.path.join(os.getenv("LOCALAPPDATA"), "Programs", "Cursor", "resources", "app", "out", "main.js")
    elif system == "Linux":
        for base in ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app"]:
            if os.path.exists(os.path.join(base, "package.json")):
                return (
                    os.path.join(base, "package.json"),
                    os.path.join(base, "out", "main.js")
                )
        raise OSError(translator.get('reset.linux_path_not_found') if translator else "在 Linux 系统上未找到 Cursor 安装路径")
    else:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")

    return (package_path, main_path)

def get_config_paths() -> Tuple[str, str, str]:
    """Get paths to configuration files"""
    system = platform.system()
    home = os.path.expanduser("~")
    
    if system == "Darwin":
        cursor_config_dir = os.path.join(home, "Library", "Application Support", "cursor")
    elif system == "Windows":
        cursor_config_dir = os.path.join(os.getenv("APPDATA"), "cursor")
    elif system == "Linux":
        cursor_config_dir = os.path.join(home, ".config", "Cursor")
    else:
        raise OSError(f"Unsupported operating system: {system}")
        
    return (
        os.path.join(cursor_config_dir, "User", "globalStorage", "storage.json"),
        os.path.join(cursor_config_dir, "User", "globalStorage", "state.vscdb"),
        os.path.join(cursor_config_dir, "machineId")
    )

def update_system_machine_id(new_machine_id: str, translator=None) -> bool:
    """Update system-level machine IDs"""
    try:
        system = platform.system()
        
        if system == "Windows":
            try:
                # Update Windows registry
                import winreg
                key_path = r"SOFTWARE\Microsoft\Cryptography"
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_machine_id)
                winreg.CloseKey(key)
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.windows_guid_updated') if translator else 'Windows GUID updated successfully'}{Style.RESET_ALL}")
                return True
            except PermissionError:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.windows_permission_denied') if translator else 'Windows permission denied'}{Style.RESET_ALL}")
                return False
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.windows_guid_update_failed') if translator else 'Windows GUID update failed'}: {e}{Style.RESET_ALL}")
                return False
                
        elif system == "Darwin":
            try:
                # Update macOS system UUID using system_profiler
                cmd = ["sudo", "nvram", f"platform-uuid={new_machine_id.upper()}"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.macos_uuid_updated') if translator else 'macOS UUID updated successfully'}{Style.RESET_ALL}")
                    return True
                else:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.macos_uuid_update_failed') if translator else 'macOS UUID update failed'}{Style.RESET_ALL}")
                    return False
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.macos_uuid_update_failed') if translator else 'macOS UUID update failed'}: {e}{Style.RESET_ALL}")
                return False
                
        elif system == "Linux":
            try:
                machine_id_path = "/etc/machine-id"
                if os.path.exists(machine_id_path):
                    # Write new ID to a temporary file
                    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                        temp_file.write(new_machine_id.replace("-", ""))
                        temp_path = temp_file.name
                    
                    # Use sudo to copy the temporary file to /etc/machine-id
                    cmd = ["sudo", "cp", temp_path, machine_id_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    # Clean up temporary file
                    os.unlink(temp_path)
                    
                    if result.returncode == 0:
                        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.system_ids_updated') if translator else 'System IDs updated successfully'}{Style.RESET_ALL}")
                        return True
                    else:
                        error_msg = result.stderr or "Permission denied or sudo required"
                        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.system_ids_update_failed') if translator else 'System IDs update failed'}: {error_msg}{Style.RESET_ALL}")
                        return False
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.system_ids_update_failed') if translator else 'System IDs update failed'}: {e}{Style.RESET_ALL}")
                return False
                
        return True
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.system_ids_update_failed') if translator else 'System IDs update failed'}: {e}{Style.RESET_ALL}")
        return False
    
def generate_new_ids():
    """Generate new machine ID"""
    # Generate new UUIDw
    dev_device_id = str(uuid.uuid4())

    # Generate new machineId (64 characters of hexadecimal)
    machine_id = hashlib.sha256(os.urandom(32)).hexdigest()

    # Generate new macMachineId (128 characters of hexadecimal)
    mac_machine_id = hashlib.sha512(os.urandom(64)).hexdigest()

    # Generate new sqmId
    sqm_id = "{" + str(uuid.uuid4()).upper() + "}"

    return {
        "telemetry.devDeviceId": dev_device_id,
        "telemetry.macMachineId": mac_machine_id,
        "telemetry.machineId": machine_id,
        "telemetry.sqmId": sqm_id,
        "storage.serviceMachineId": dev_device_id,  # Add storage.serviceMachineId
    }

def update_sqlite_db(translator, sqlite_path, new_ids):
        """Update machine ID in SQLite database"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.updating_sqlite')}...{Style.RESET_ALL}")
            
            conn = sqlite3.connect(sqlite_path)
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
                print(f"{EMOJI['INFO']} {Fore.CYAN} {translator.get('reset.updating_pair')}: {key}{Style.RESET_ALL}")

            conn.commit()
            conn.close()
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.sqlite_success')}{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.sqlite_error', error=str(e))}{Style.RESET_ALL}")
            return False

def update_storage_json(translator, storage_json_path, new_ids):    
    """Update machine ID in storage.json"""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.updating_storage')}...{Style.RESET_ALL}")
        
        with open(storage_json_path, "r") as f:
            storage = json.load(f)

        storage.update(new_ids)
        
        # create backup of storage.json
        backup_path = storage_json_path + ".bak"
        shutil.copy(storage_json_path, backup_path)
        print(f"{Fore.GREEN}{EMOJI['BACKUP']} {translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")

        with open(storage_json_path, "w") as f:
            json.dump(storage, f, indent=2)
        
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.storage_success')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.storage_error', error=str(e))}{Style.RESET_ALL}")
        return False

def update_machine_id_file(translator, local_machine_id_file_path, new_machine_id):
    """Update machine ID in machineId file"""
    try:
        with open(local_machine_id_file_path, "w") as f:
            f.write(new_machine_id)
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.localMachineId_completed') if translator else 'Machine ID reset successfully'}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.localMachineId_failed', error=str(e)) if translator else f'Reset process error: {str(e)}'}{Style.RESET_ALL}")
        return False


def reset_machine_id(translator=None) -> bool:
    """Reset machine ID in all locations"""
    try:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.title') if translator else 'Cursor Machine ID Reset Tool'}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

        success = True
        
        try:
            # Get configuration paths
            json_path, sqlite_path, localMachineId_path = get_config_paths()
            
            # Generate new machine ID
            ids = generate_new_ids()

            # Update storage.json
            if os.path.exists(json_path):
                if not update_storage_json(translator, json_path, ids):
                    success = False
            else:
                print(f"{Fore.RED}{EMOJI['WARNING']} {translator.get('reset.not_found', path=json_path) if translator else f'File not found: {json_path}'}{Style.RESET_ALL}")
            

            # Update SQLite database
            if os.path.exists(sqlite_path):
                if not update_sqlite_db(translator, sqlite_path, ids):
                    success = False
            else:
                print(f"{Fore.RED}{EMOJI['WARNING']} {translator.get('reset.not_found', path=sqlite_path) if translator else f'File not found: {sqlite_path}'}{Style.RESET_ALL}")
            
            # Update local machine ID
            if os.path.exists(localMachineId_path):
                if not update_machine_id_file(translator, localMachineId_path, ids["telemetry.devDeviceId"]):
                    success = False
            else:
                print(f"{Fore.RED}{EMOJI['WARNING']} {translator.get('reset.not_found', path=localMachineId_path) if translator else f'File not found: {localMachineId_path}'}{Style.RESET_ALL}")

            # Update system machine ID
            if not update_system_machine_id(ids["telemetry.machineId"],translator):
                success = False
            
            return success

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.process_error', error=str(e)) if translator else f'Reset process error: {str(e)}'}{Style.RESET_ALL}")
            return False

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.process_error', error=str(e)) if translator else f'Reset process error: {str(e)}'}{Style.RESET_ALL}")
        return False

def run(translator=None):
    """Main function to reset machine ID"""
    success = reset_machine_id(translator)
    
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('reset.press_enter') if translator else 'Press Enter to exit...'}...")
    return success

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
    
    run(main_translator)