import os
import sys
import json
import shutil
import platform
import re
import tempfile
import subprocess
from colorama import Fore, Style, init
from typing import Tuple

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅", 
    "ERROR": "❌",
    "INFO": "ℹ️",
}

def get_cursor_paths(translator=None, appimage_dir=None) -> Tuple[str, str]:
    """ Get Cursor related paths"""
    system = platform.system()

    # If we're using an extracted AppImage directory, use that instead of system paths
    if appimage_dir and system == "Linux":
        # Define possible app directory paths for different versions
        possible_paths = [
            os.path.join(appimage_dir, "resources", "app"),  # Legacy path
            os.path.join(appimage_dir, "usr", "share", "cursor", "resources", "app")  # New path
        ]
        
        # Try each possible path
        for app_dir in possible_paths:
            pkg_path = os.path.join(app_dir, "package.json")
            if os.path.exists(pkg_path):
                return (
                    pkg_path,
                    os.path.join(app_dir, "out", "main.js")
                )
                
        # If no valid paths found, raise error with checked paths
        paths_tried = "\n - " + "\n - ".join(possible_paths)
        raise OSError(f"Could not find package.json in any of these locations:{paths_tried}")

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
            "bases": ["/resources/app"],  # Relative to extracted AppImage directory
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

def get_workbench_cursor_path(translator=None, appimage_dir=None) -> str:
    """Get Cursor workbench.desktop.main.js path"""
    system = platform.system()
    
    if appimage_dir and system == "Linux":
        # Define possible workbench paths for different AppImage versions
        possible_paths = [
            os.path.join(appimage_dir, "resources", "app", "out/vs/workbench/workbench.desktop.main.js"),  # Legacy path
            os.path.join(appimage_dir, "usr", "share", "cursor", "resources", "app", "out/vs/workbench/workbench.desktop.main.js")  # New path
        ]
        
        # Try each possible path
        for workbench_path in possible_paths:
            if os.path.exists(workbench_path):
                return workbench_path
                
        # If no valid paths found, raise error with checked paths
        paths_tried = "\n - " + "\n - ".join(possible_paths)
        raise OSError(translator.get('patch.workbench_not_found') if translator else f"Workbench file not found in any of these locations:{paths_tried}")
    
    paths_map = {
        "Darwin": {
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
        raise OSError(translator.get('reset.file_not_found', path=main_path) if translator else f"File not found: {main_path}")
        
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
                
            # Save original permissions and ownership
            original_stat = os.stat(appimage_path)
            
            # Replace original with new version
            shutil.move(new_appimage, appimage_path)
            
            # Restore original permissions including executable bit
            os.chmod(appimage_path, original_stat.st_mode)
            if os.name != 'nt':  # Not Windows
                try:
                    os.chown(appimage_path, original_stat.st_uid, original_stat.st_gid)
                except PermissionError:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} Could not restore original ownership, but file permissions were preserved{Style.RESET_ALL}")
            
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.appimage_rebuilt')}{Style.RESET_ALL}")
            return True
            
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.appimagetool_not_found')}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}To install appimagetool:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1. Download from: https://github.com/AppImage/AppImageKit/releases{Style.RESET_ALL}")
        print(f"{Fore.WHITE}2. Make it executable: chmod +x appimagetool-*.AppImage{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Move to path: sudo mv appimagetool-*.AppImage /usr/local/bin/appimagetool{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 60}{Style.RESET_ALL}")
        return False
            
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.rebuild_failed', error=str(e))}{Style.RESET_ALL}")
        return False

def modify_workbench_js(file_path: str, translator=None, extracted_dir=None) -> bool:
    """Modify workbench.desktop.main.js content"""
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

            # Pattern based on platform
            if sys.platform == "linux":
                CButton_old_pattern = r'([$\(]k,E\(Ks,{title:"Upgrade to Pro",size:"small",get codicon\(\){return F\.rocket},get onClick\(\){return [^}]+}}),null\)'
                CButton_new_pattern = r'$(k,E(Ks,{title:"yeongpin GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)'
            else:
                CButton_old_pattern = r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'$(k,E(Ks,{title:"yeongpin GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/yeongpin/cursor-free-vip","_blank")}}}),null)'

            CBadge_old_pattern = r'<div>Pro Trial'
            CBadge_new_pattern = r'<div>Pro'

            CToast_old_pattern = r'notifications-toasts'
            CToast_new_pattern = r'notifications-toasts hidden'

            # Replace content
            content = re.sub(CButton_old_pattern, CButton_new_pattern, content)
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

def patch_cursor(translator, app_image_path=None) -> bool:
    """Patch Cursor app"""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('patch.start_patching')}...{Style.RESET_ALL}")
        
        extracted_dir = None
        
        # Handle AppImage if provided
        if app_image_path:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('patch.processing_appimage', path=app_image_path)}{Style.RESET_ALL}")
            extracted_dir = extract_appimage(app_image_path, translator)
            if not extracted_dir:
                return False
        
        try:
            # Get paths (either from system or extracted AppImage)
            pkg_path, main_path = get_cursor_paths(translator, extracted_dir)
            
            # Check version
            with open(pkg_path, "r", encoding="utf-8") as f:
                version = json.load(f)["version"]
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('patch.current_version', version=version)}{Style.RESET_ALL}")
            
            if not version_check(version, min_version="0.45.0", translator=translator):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('patch.version_not_supported')}{Style.RESET_ALL}")
                return False

            # Modify main.js
            if not modify_main_js(main_path, translator):
                return False
            
            # Get and modify workbench path
            try:
                workbench_path = get_workbench_cursor_path(translator, extracted_dir)
                if not modify_workbench_js(workbench_path, translator, extracted_dir):
                    return False
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('patch.workbench_error', error=str(e))}{Style.RESET_ALL}")
                return False

            # If we're working with an AppImage, rebuild it
            if extracted_dir:
                if not rebuild_appimage(app_image_path, extracted_dir, translator):
                    return False

            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('patch.completed')}{Style.RESET_ALL}")
            return True

        finally:
            # Clean up extracted directory if it exists
            if extracted_dir and os.path.exists(os.path.dirname(extracted_dir)):
                print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('patch.cleaning_temp_files')}...{Style.RESET_ALL}")
                try:
                    shutil.rmtree(os.path.dirname(extracted_dir), ignore_errors=True)
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('patch.cleanup_error', error=str(e))}{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('patch.failed', error=str(e))}{Style.RESET_ALL}")
        return False

def run(translator=None, app_image_path=None):
    """Main function to patch the app"""
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('patch.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    # Verify app_image_path on Linux
    if platform.system() == "Linux":
        if not app_image_path:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('patch.no_appimage_linux')}{Style.RESET_ALL}")
            return False
        app_image_path = os.path.abspath(os.path.expanduser(app_image_path))
        if not os.path.isfile(app_image_path):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('patch.invalid_appimage', path=app_image_path)}{Style.RESET_ALL}")
            return False

    success = patch_cursor(translator, app_image_path)

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('patch.press_enter')}...")
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
    
    run(main_translator, app_image_path)