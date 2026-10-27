from .base_brand import BaseBrand


class SamsungBrandPlugin(BaseBrand):
    """
    Samsung brand plugin.
    Detected by: 'Samsung'

    When Samsung BIOS is dropped:
      - btn_smart_me_fix -> "SAMSUNG ME CLEAN"
      - btn_extract_dmi  -> "SAMSUNG DMI EX"
    """

    BRAND_NAME = "Samsung"
    SUPPORTED_BRANDS = [
        "SAMSUNG",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        """
        Samsung-specific sidebar buttons.
        Add Samsung-specific buttons here when required.
        """
        return []
