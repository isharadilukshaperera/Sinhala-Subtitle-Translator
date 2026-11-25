"""
System resource monitoring module for Anti Gravity.
Polls CPU, RAM, and NVIDIA GPU (RTX 3060) metrics in real time.
"""
from dataclasses import dataclass
from typing import Optional
import warnings
import psutil
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    import pynvml
    HAS_NVML = True
except Exception:
    HAS_NVML = False

try:
    import torch
    HAS_TORCH = True
except Exception:
    HAS_TORCH = False


@dataclass
class SystemMetrics:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    gpu_available: bool = False
    gpu_name: str = "N/A"
    vram_used_mb: int = 0
    vram_total_mb: int = 0
    vram_percent: float = 0.0
    gpu_util_percent: float = 0.0
    gpu_temp_c: int = 0


def get_gpu_display_name() -> str:
    """Return the user-facing GPU name, e.g. 'NVIDIA GeForce RTX 4070'.

    Tries pynvml first, then torch.cuda, then returns a generic fallback.
    Safe to call at import time — never raises.
    """
    if HAS_NVML:
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            pynvml.nvmlShutdown()
            return name if isinstance(name, str) else name.decode("utf-8")
        except Exception:
            pass
    if HAS_TORCH:
        try:
            if torch.cuda.is_available():
                return torch.cuda.get_device_name(0)
        except Exception:
            pass
    return "GPU"


class SystemMonitor(QObject):
    """Periodically queries hardware resource metrics and emits them via Qt signals."""
    metrics_updated = pyqtSignal(object)

    def __init__(self, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.interval_ms = interval_ms
        self._nvml_initialized = False
        self._nvml_handle = None
        self._gpu_name = "NVIDIA GPU"
        self._vram_total_mb = 12288  # RTX 3060 default fallback

        self._init_nvml()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.poll_metrics)

    def _init_nvml(self):
        if not HAS_NVML:
            return
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                name = pynvml.nvmlDeviceGetName(self._nvml_handle)
                self._gpu_name = name if isinstance(name, str) else name.decode("utf-8")
                mem = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                self._vram_total_mb = mem.total // (1024 * 1024)
                self._nvml_initialized = True
        except Exception:
            self._nvml_initialized = False

    def start(self):
        self._timer.start(self.interval_ms)
        self.poll_metrics()

    def stop(self):
        self._timer.stop()
        if self._nvml_initialized:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml_initialized = False

    def get_hardware_summary(self) -> str:
        """Returns brief string for header badge."""
        if self._nvml_initialized:
            return f"{self._gpu_name} • {round(self._vram_total_mb / 1024, 1)}GB VRAM"
        elif HAS_TORCH and torch.cuda.is_available():
            return f"{torch.cuda.get_device_name(0)} (CUDA)"
        return "CPU Mode (No GPU Detected)"

    def poll_metrics(self):
        metrics = SystemMetrics()

        # CPU & RAM
        try:
            metrics.cpu_percent = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            metrics.ram_percent = mem.percent
            metrics.ram_used_gb = round(mem.used / (1024 ** 3), 1)
            metrics.ram_total_gb = round(mem.total / (1024 ** 3), 1)
        except Exception:
            pass

        # NVIDIA GPU
        if self._nvml_initialized and self._nvml_handle:
            try:
                metrics.gpu_available = True
                metrics.gpu_name = self._gpu_name
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                metrics.vram_used_mb = mem_info.used // (1024 * 1024)
                metrics.vram_total_mb = mem_info.total // (1024 * 1024)
                if metrics.vram_total_mb > 0:
                    metrics.vram_percent = round((metrics.vram_used_mb / metrics.vram_total_mb) * 100, 1)

                util_info = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                metrics.gpu_util_percent = float(util_info.gpu)

                try:
                    metrics.gpu_temp_c = pynvml.nvmlDeviceGetTemperature(self._nvml_handle, pynvml.NVML_TEMPERATURE_GPU)
                except Exception:
                    metrics.gpu_temp_c = 0
            except Exception:
                # If NVML fails during runtime, attempt fallback via torch
                self._fallback_torch_metrics(metrics)
        else:
            self._fallback_torch_metrics(metrics)

        self.metrics_updated.emit(metrics)

    def _fallback_torch_metrics(self, metrics: SystemMetrics):
        if HAS_TORCH and torch.cuda.is_available():
            try:
                metrics.gpu_available = True
                metrics.gpu_name = torch.cuda.get_device_name(0)
                allocated = torch.cuda.memory_allocated(0) // (1024 * 1024)
                total = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
                metrics.vram_used_mb = allocated
                metrics.vram_total_mb = total
                if total > 0:
                    metrics.vram_percent = round((allocated / total) * 100, 1)
            except Exception:
                pass
