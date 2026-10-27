import os
import sys

def get_app_root():
    """
    Returns the ROOT directory of the application (where the .exe lives).
    Use this for: external runtime folders (FIT_WORKSPACE, WORKSPACE, etc.)
    that sit NEXT to the .exe and are NOT bundled inside.
    Works for both standard Python execution and PyInstaller (onedir/onefile).
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller compiled: sys.executable is the .exe file
        return os.path.dirname(sys.executable)
    else:
        # Standard Python execution
        return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """
    Returns the absolute path to a BUNDLED resource (assets, translations, etc.).
    Use this for: files that are packaged INSIDE the compiled exe via --add-data.

    In PyInstaller onedir mode, bundled data goes into _internal/ subfolder.
    sys._MEIPASS points to that _internal/ folder.
    In dev mode, resources live next to the script (same as get_app_root()).
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller sets sys._MEIPASS to the _internal/ extraction folder
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def get_python_cmd():
    """
    Returns the command to run a Python script.
    In a frozen app, we use our bundled pyrunner.exe so target PCs
    do not require Python to be installed at all.
    """
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
        pyrunner = os.path.join(app_dir, "pyrunner.exe")
        if os.path.isfile(pyrunner):
            return pyrunner
        return "python"
    return sys.executable

def get_script_cmd(script_path):
    """
    Returns the base command list to execute a script.
    If the script is an .exe, it returns [script_path].
    If it's a .py or anything else, it returns [get_python_cmd(), script_path].
    Use this to replace [sys.executable, script_path] for PyInstaller compatibility.
    """
    script_str = str(script_path)
    if script_str.lower().endswith('.exe'):
        return [script_str]
    return [get_python_cmd(), script_str]

def get_subprocess_env():
    """
    Returns an environment dictionary containing PYTHONPATH pointing to
    the project root and .venv/Lib/site-packages so spawned tools (MEA, MCE, etc.)
    always have access to dependencies even if launched from different environments.
    """
    env = os.environ.copy()
    root = get_app_root()
    venv_site = os.path.join(root, ".venv", "Lib", "site-packages")
    pythonpath = env.get("PYTHONPATH", "")
    paths_to_add = [
        root,
        venv_site,
        os.path.join(root, "ME Analyzer", "_deps"),
        os.path.join(root, "external", "MEAnalyzer", "_deps"),
        os.path.join(root, "MCExtractor"),
    ]
    new_paths = [p for p in paths_to_add if os.path.exists(p) and p not in pythonpath]
    if new_paths:
        env["PYTHONPATH"] = os.pathsep.join(new_paths + ([pythonpath] if pythonpath else []))
    return env
