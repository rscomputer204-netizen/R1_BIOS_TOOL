from .base_brand import BaseBrand


class MsiBrandPlugin(BaseBrand):
    """
    MSI brand plugin.
    Detected by: 'MSI', 'Micro-Star', 'Micro Star'

    When MSI BIOS is dropped:
      - btn_smart_me_fix -> "MSI ME CLEAN"
      - btn_extract_dmi  -> "MSI DMI EX"
    """

    BRAND_NAME = "MSI"
    SUPPORTED_BRANDS = [
        "MSI",
        "MICRO-STAR",
        "MICRO STAR",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        """
        MSI-specific sidebar buttons.
        Add MSI-specific buttons here when required.
        """
        return []
