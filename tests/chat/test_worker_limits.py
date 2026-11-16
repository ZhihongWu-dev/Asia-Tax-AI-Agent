"""Exercise OS limits in disposable children, never in the pytest process."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object behavior')
def test_windows_memory_limit_rejects_oversized_allocation():
    script = '''
from packages.chat.worker_limits import apply_worker_limits
apply_worker_limits(5, 128)
try:
    data = bytearray(256 * 1024 * 1024)
except MemoryError:
    print('bounded')
else:
    raise AssertionError('memory allocation escaped job limit')
'''
    result = subprocess.run([sys.executable, '-X', 'utf8', '-c', script], cwd=ROOT,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'bounded'


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object behavior')
def test_windows_cpu_limit_terminates_busy_worker():
    script = '''
from packages.chat.worker_limits import apply_worker_limits
apply_worker_limits(1, 128)
print('ready', flush=True)
while True:
    pass
'''
    result = subprocess.run([sys.executable, '-X', 'utf8', '-c', script], cwd=ROOT,
                            capture_output=True, text=True, timeout=15)
    assert result.stdout.strip() == 'ready', result.stderr
    assert result.returncode != 0


@pytest.mark.skipif(os.name != 'nt', reason='Windows Job Object behavior')
def test_terminating_worker_also_terminates_its_child():
    import ctypes as c
    from ctypes import wintypes as w
    script = '''
import subprocess,sys,time
from packages.chat.worker_limits import apply_worker_limits
apply_worker_limits(5, 128)
child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(60)'], stdout=subprocess.DEVNULL)
print(child.pid, flush=True)
time.sleep(60)
'''
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    kernel.WaitForSingleObject.restype = w.DWORD
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CloseHandle.restype = w.BOOL
    worker = subprocess.Popen([sys.executable, '-X', 'utf8', '-c', script], cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    handle = None
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            line = pool.submit(worker.stdout.readline)
            try:
                child_pid = int(line.result(timeout=10).strip())
            except BaseException:
                worker.kill()
                raise
        handle = kernel.OpenProcess(0x100000, False, child_pid)
        assert handle, c.get_last_error()
        assert kernel.WaitForSingleObject(handle, 0) == 258  # still running
        worker.kill()
        worker.wait(timeout=10)
        assert kernel.WaitForSingleObject(handle, 10000) == 0
    finally:
        if worker.poll() is None:
            worker.kill()
        worker.communicate(timeout=10)
        if handle:
            kernel.CloseHandle(handle)
