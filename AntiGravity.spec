# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('G:/Ai/Sinhala Subtitle Translator/anti_gravity/data', 'anti_gravity/data')]
binaries = []
hiddenimports = ['regex', 'regex._regex_core', 'chardet', 'psutil', 'pynvml', 'sentencepiece', 'safetensors', 'huggingface_hub']
datas += collect_data_files('transformers')
datas += collect_data_files('bitsandbytes')
datas += collect_data_files('accelerate')
datas += collect_data_files('pysrt')
datas += collect_data_files('pynvml')
hiddenimports += collect_submodules('anti_gravity')
tmp_ret = collect_all('torch')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['G:/Ai/Sinhala Subtitle Translator/main.py'],
    pathex=['G:/Ai/Sinhala Subtitle Translator'],
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
    name='AntiGravity',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AntiGravity',
)
