# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('translations', 'translations'), ('BIOSUtilities', 'BIOSUtilities'), ('BIOSUtilities/biosutilities', 'biosutilities'), ('brands', 'brands'), ('rg_engine', 'rg_engine')]
binaries = []
hiddenimports = ['biosutilities', 'biosutilities.common', 'biosutilities.common.templates', 'biosutilities.common.checksums', 'biosutilities.common.compression', 'biosutilities.common.paths', 'biosutilities.common.patterns', 'biosutilities.common.structs', 'biosutilities.common.system', 'biosutilities.common.texts', 'biosutilities.ami_pfat_extract', 'biosutilities.ami_ucp_extract', 'biosutilities.apple_efi_id', 'biosutilities.apple_efi_im4p', 'biosutilities.apple_efi_pbzx', 'biosutilities.apple_efi_pkg', 'biosutilities.award_bios_extract', 'biosutilities.dell_pfs_extract', 'biosutilities.fujitsu_sfx_extract', 'biosutilities.fujitsu_upc_extract', 'biosutilities.insyde_ifd_extract', 'biosutilities.panasonic_bios_extract', 'biosutilities.phoenix_tdk_extract', 'biosutilities.portwell_efi_extract', 'biosutilities.toshiba_com_extract', 'biosutilities.vaio_package_extract', 'rg_engine', 'rg_engine.extractor', 'rg_engine.replacer', 'rg_engine.ui', 'rg_engine.validator', 'programmer_guard', 'license_manager', 'security_gate', 'hp_dmi_extractor', 'dell_dmi_extractor', 'lenovo_dmi_extractor', 'acer_dmi_extractor', 'dmi_extractor', 'dmi_injector', 'password_unlock_engine', 'password_remover_dialog', 'acer_dmi_extractor', 'advanced_extractor', 'advanced_smart_repair', 'analysis_engine', 'analysis_suite', 'analysis_ui', 'asus_dmi_extractor', 'automated_repair_worker', 'automated_workflow', 'auto_repair_hp', 'benchmark_unlock', 'bios_client', 'bios_decompiler', 'bios_parser', 'bios_recompiler', 'bios_region_fixer', 'body_viewer', 'carve_tgl_parts', 'chat_saver', 'check_perms', 'compare_fixer', 'core_workspace', 'dell_dmi_extractor', 'dmi_extractor', 'dmi_injector', 'dmi_migrator', 'error_manager', 'extractor_dialog', 'extract_me_diag', 'final_automated_repair', 'firmware_confirm_dialog', 'firmware_matcher', 'firmware_organizer', 'fit_automator', 'fix_label', 'fix_mea', 'hp_dmi_extractor', 'hp_repair_tool', 'key_generator_ui', 'language_manager', 'lenovo_dmi_extractor', 'license_manager', 'mea_parser', 'merge_dialog', 'me_cleaner', 'me_clean_advanced', 'network_manager', 'parse_desc', 'password_remover_dialog', 'password_unlock_engine', 'path_utils', 'performance_tracker', 'programmer_guard', 'push_to_github', 'pyrunner', 'repair_edb41_final', 'repair_edb41_v2', 'repair_workflow', 'report_settings_ui', 'requirement', 'security_gate', 'smart_repair_engine', 'splash_screen', 'surgical_repair', 'updater', 'update_manager', 'v13_rebuild_edb41', 'v15_rebuild_l3520', 'BGScriptTool.big_script_tool', 'brands.acer', 'brands.apple', 'brands.asrock', 'brands.asus', 'brands.base_brand', 'brands.dell', 'brands.gigabyte', 'brands.hp', 'brands.lenovo', 'brands.manager', 'brands.microsoft', 'brands.msi', 'brands.samsung', 'brands.toshiba', 'brands.__init__', 'MCExtractor.MCE', 'RESEARCH_LAB.acer_catalog_scanner', 'RESEARCH_LAB.acer_knowledge_builder', 'RESEARCH_LAB.asus_catalog_scanner', 'RESEARCH_LAB.bios_diff_analyzer', 'RESEARCH_LAB.dell_asus_knowledge_builder', 'RESEARCH_LAB.dell_catalog_scanner', 'RESEARCH_LAB.hp_auto_unlocker', 'RESEARCH_LAB.hp_catalog_scanner', 'RESEARCH_LAB.hp_knowledge_builder', 'RESEARCH_LAB.lenovo_catalog_scanner', 'RESEARCH_LAB.lenovo_knowledge_builder', 'rg_engine.extractor', 'rg_engine.replacer', 'rg_engine.ui', 'rg_engine.validator', 'rg_engine.__init__', 'scripts.migrate_fw_repo', 'scripts.regen', 'utils.archiver']
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('shiboken6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=['BIOSUtilities', 'd:/BIOS_-TOOL'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='R1_BIOS_TOOL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='R1_BIOS_TOOL',
)
