from .base_brand import BaseBrand


class GigabyteBrandPlugin(BaseBrand):
    """
    Gigabyte brand plugin.
    Detected by: 'Gigabyte', 'AORUS'

    When Gigabyte BIOS is dropped:
      - btn_smart_me_fix -> "GIGABYTE ME CLEAN"
      - btn_extract_dmi  -> "GIGABYTE DMI EX"
    """

    BRAND_NAME = "Gigabyte"
    SUPPORTED_BRANDS = [
        "GIGABYTE",
        "AORUS",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        """
        Gigabyte-specific sidebar buttons.
        Add Gigabyte-specific buttons here when required.
        """
        return []
