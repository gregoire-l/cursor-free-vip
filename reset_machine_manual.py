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
        cursor_config_dir = os.path.join(home, ".config", "cursor")
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
        os.path.join(cursor_config_dir, "User", "settings.json"),
        os.path.join(cursor_config_dir, "User", "globalStorage", "state.vscdb"),
        os.path.join(cursor_config_dir, "User", "machineId")
    )

def update_system_machine_id(translator=None) -> bool:
    """Update system-level machine IDs"""
    try:
        system = platform.system()
        new_id = str(uuid.uuid4())
        
        if system == "Windows":
            try:
                # Update Windows registry
                import winreg
                key_path = r"SOFTWARE\Microsoft\Cryptography"
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_id)
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
                cmd = ["sudo", "nvram", f"platform-uuid={new_id.upper()}"]
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
                        temp_file.write(new_id.replace("-", ""))
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

def update_sqlite_machine_id(db_path: str, translator=None) -> bool:
    """Update machine ID in SQLite database"""
    if not os.path.exists(db_path):
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth.db_not_found', path=db_path) if translator else f'Database not found: {db_path}'}{Style.RESET_ALL}")
        return False
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth.connected_to_database') if translator else 'Connected to database'}{Style.RESET_ALL}")
        
        new_id = str(uuid.uuid4())
        cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'telemetry.machineId'", (new_id,))
        cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'workbench.deviceId'", (new_id,))
        
        conn.commit()
        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('auth.database_updated_successfully') if translator else 'Database updated successfully'}{Style.RESET_ALL}")
        
        return True
    except sqlite3.Error as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('auth.db_connection_error', error=str(e)) if translator else f'Database error: {e}'}{Style.RESET_ALL}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('auth.database_connection_closed') if translator else 'Database connection closed'}{Style.RESET_ALL}")

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
            new_machine_id = str(uuid.uuid4())
            
            # Update JSON config
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r+") as f:
                        config = json.load(f)
                        config["machine-id"] = new_machine_id
                        f.seek(0)
                        json.dump(config, f, indent=2)
                        f.truncate()
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.success') if translator else 'Machine ID reset successfully'}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.process_error', error=str(e)) if translator else f'Reset process error: {str(e)}'}{Style.RESET_ALL}")
                    success = False
            else:
                print(f"{Fore.YELLOW}{EMOJI['WARNING']} {translator.get('reset.not_found', path=json_path) if translator else f'File not found: {json_path}'}{Style.RESET_ALL}")
               
            
            # Update SQLite database
            if os.path.exists(sqlite_path):
                if not update_sqlite_machine_id(sqlite_path, translator):
                    success = False
            else:
                print(f"{Fore.RED}{EMOJI['WARNING']} {translator.get('reset.not_found', path=sqlite_path) if translator else f'File not found: {sqlite_path}'}{Style.RESET_ALL}")
            
            # Update local machine ID
            if os.path.exists(localMachineId_path):
                try:
                    with open(localMachineId_path, "w") as f:
                        f.write(new_machine_id)
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.localMachineId_completed') if translator else 'Machine ID reset successfully'}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.localMachineId_failed', error=str(e)) if translator else f'Reset process error: {str(e)}'}{Style.RESET_ALL}")
                    success = False
            else:
                print(f"{Fore.RED}{EMOJI['WARNING']} {translator.get('reset.not_found', path=localMachineId_path) if translator else f'File not found: {localMachineId_path}'}{Style.RESET_ALL}")

            # Update system machine ID
            if not update_system_machine_id(translator):
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