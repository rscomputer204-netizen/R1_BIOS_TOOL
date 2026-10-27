from .base_brand import BaseBrand


class MicrosoftBrandPlugin(BaseBrand):
    """
    Microsoft brand plugin.
    Detected by: 'Microsoft', 'Surface'

    When Microsoft BIOS is dropped:
      - btn_smart_me_fix -> "MICROSOFT ME CLEAN"
      - btn_extract_dmi  -> "MICROSOFT DMI EX"
    """

    BRAND_NAME = "Microsoft"
    SUPPORTED_BRANDS = [
        "MICROSOFT",
        "SURFACE",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        """
        Microsoft-specific sidebar buttons.
        Add Microsoft-specific buttons here when required.
        """
        return []
