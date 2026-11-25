"""
PyInstaller Build Script for Anti Gravity Subtitle Translator.
Packages the desktop application into a standalone Windows executable.
"""
import sys
import os
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def build():
    print(f"Building Anti Gravity standalone Windows executable...")
    python_exe = sys.executable

    cmd = [
        python_exe,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name=AntiGravity",
        "--windowed",
        "--onedir",
        f"--paths={PROJECT_ROOT}",

        # ── Core application modules ──
        "--collect-submodules=anti_gravity",

        # ── Data files (glossary, few-shots, etc.) ──
        f"--add-data={os.path.join(PROJECT_ROOT, 'anti_gravity', 'data')}{os.pathsep}anti_gravity/data",

        # ── PyTorch & CUDA runtime DLLs ──
        "--collect-all=torch",

        # ── Transformers & quantization ──
        "--collect-data=transformers",
        "--collect-data=bitsandbytes",
        "--collect-data=accelerate",

        # ── Subtitle parsing ──
        "--collect-data=pysrt",

        # ── GPU monitoring ──
        "--collect-data=pynvml",

        # ── Hidden imports that PyInstaller misses ──
        "--hidden-import=regex",
        "--hidden-import=regex._regex_core",
        "--hidden-import=chardet",
        "--hidden-import=psutil",
        "--hidden-import=pynvml",
        "--hidden-import=sentencepiece",
        "--hidden-import=safetensors",
        "--hidden-import=huggingface_hub",

        # ── Entry point ──
        os.path.join(PROJECT_ROOT, "main.py")
    ]

    print("Executing command:")
    print("  " + " \\\n    ".join(cmd))
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if res.returncode == 0:
        print("\n✓ Build Successful! Executable located in dist/AntiGravity/AntiGravity.exe")
        print("\nNOTE: To reduce bundle size, consider using --collect-binaries=torch")
        print("instead of --collect-all=torch and manually adding only needed DLLs.")
    else:
        print(f"\n❌ Build failed with exit code: {res.returncode}")

if __name__ == "__main__":
    build()
