import re

def replace_in_file(filepath, pattern, replacement):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if "get_script_cmd" not in new_content:
        new_content = "from path_utils import get_script_cmd\n" + new_content

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

replace_in_file('advanced_smart_repair.py', r'\[sys\.executable,\s*str\(mea_py\),\s*str\(file_path\)\]', 'get_script_cmd(mea_py) + [str(file_path)]')

replace_in_file('analysis_engine.py', r'\[\s*sys\.executable,\s*self\.mea_path,\s*self\.bios_path\s*\]', 'get_script_cmd(self.mea_path) + [self.bios_path]')

replace_in_file('automated_repair_worker.py', r'\[sys\.executable,\s*str\(mea_py\),\s*str\(bios_path\)\]', 'get_script_cmd(mea_py) + [str(bios_path)]')

replace_in_file('auto_repair_hp.py', r'\[sys\.executable,\s*str\(MEA_PY\),\s*str\(TARGET_PATH\)', 'get_script_cmd(MEA_PY) + [str(TARGET_PATH)')

