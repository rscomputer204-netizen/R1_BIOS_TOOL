import re

def parse_mea_output(output_text):
    """
    Parses the terminal output of ME Analyzer to extract version, family, SKU, and chipset.
    """
    metadata = {
        "version":  "",
        "family":   "",
        "sku":      "",
        "chipset":  "",
        "stepping": "",
        "release":  "",
        "type":     "",
        "fs_state": ""
    }
    
    # Regex patterns for common MEA output fields (handles ':', '|', '║', '│')
    patterns = {
        "version":  r"(?:Version|Ver)\s*[:|║│]\s*([\d\.]+)",
        "family":   r"Family\s*[:|║│]\s*([^\n\r\|║│/]+)",
        "sku":      r"SKU\s*[:|║│]\s*([^\n\r\|/║│]+)",
        "chipset":  r"Chipset\s*[^a-zA-Z0-9\s]*\s*([^\n\r\|║│]+)",
        "stepping": r"Stepping\s*[:|║│]\s*([^\n\r\|/║│]+)",
        "release":  r"Release\s*[:|║│]\s*([^\n\r\|/║│]+)",
        "type":     r"Type\s*[:|║│]\s*([^\n\r\|/║│]+)",
        "fs_state": r"(?:File\s*System\s*State|FS\s*State)\s*[:|║│]\s*([^\n\r\|/║│]+)"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, output_text, re.IGNORECASE)
        if match:
            metadata[key] = str(match.group(1)).strip()
            
    # CRITICAL FALLBACK: If version is still missing, try to find it in the 'Family' line
    # Many MEA versions report: "Family | CSME 15.0.35.1952"
    if not metadata["version"]:
        family_text = metadata.get("family", "")
        if family_text:
            ver_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", family_text)
            if ver_match:
                metadata["version"] = ver_match.group(1)

    # SECOND FALLBACK: Search for any version-like string near 'CSME' or 'ME'
    if not metadata["version"]:
        ver_match = re.search(r"(?:CS)?ME\s+([\d\.]+)", output_text, re.IGNORECASE)
        if ver_match:
            metadata["version"] = ver_match.group(1)
            
    # Refine SKU and Family if they contain extra symbols like '|' from MEA table
    for key in ("sku", "family", "chipset"):
        val = metadata.get(key)
        if val and isinstance(val, str):
            metadata[key] = val.split('|')[0].strip()
        
    return metadata
