from typing import List
from PySide6.QtWidgets import QPushButton

class BaseBrand:
    """
    Base class for brand-specific logic plugins.
    All brand modules in the brands/ directory should subclass this or implement a similar interface.
    """
    
    SUPPORTED_BRANDS: List[str] = []
    
    @classmethod
    def supports(cls, dmi_brand: str) -> bool:
        """
        Check if this plugin supports the given DMI brand string.
        """
        if not dmi_brand:
            return False
            
        dmi_brand = dmi_brand.upper()
        for brand in cls.SUPPORTED_BRANDS:
            if brand.upper() in dmi_brand or dmi_brand in brand.upper():
                return True
        return False
        
    @classmethod
    def get_ui_buttons(cls, main_window) -> List[QPushButton]:
        """
        Return a list of PySide6 QPushButtons that provide brand-specific actions.
        The buttons should be connected to their respective handler functions.
        'main_window' gives access to the main application state (terminal, workspace, etc.).
        """
        return []
