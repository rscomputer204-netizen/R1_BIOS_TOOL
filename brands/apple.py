from .base_brand import BaseBrand


class AppleBrandPlugin(BaseBrand):
    """
    Apple brand plugin.
    Detected by: 'Apple', 'MacBook', 'iMac', 'Mac Mini'

    When Apple BIOS is dropped:
      - btn_smart_me_fix -> "APPLE ME CLEAN"
      - btn_extract_dmi  -> "APPLE DMI EX"
    """

    BRAND_NAME = "Apple"
    SUPPORTED_BRANDS = [
        "APPLE",
        "MACBOOK",
        "IMAC",
        "MAC MINI",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        """
        Apple-specific sidebar buttons.
        Add Apple-specific buttons here when required.
        """
        return []
