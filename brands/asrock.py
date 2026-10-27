from .base_brand import BaseBrand


class AsrockBrandPlugin(BaseBrand):
    """
    ASRock brand plugin.
    Detected by: 'ASRock'

    When ASRock BIOS is dropped:
      - btn_smart_me_fix -> "ASROCK ME CLEAN"
      - btn_extract_dmi  -> "ASROCK DMI EX"
    """

    BRAND_NAME = "ASRock"
    SUPPORTED_BRANDS = [
        "ASROCK",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        """
        ASRock-specific sidebar buttons.
        Add ASRock-specific buttons here when required.
        """
        return []
