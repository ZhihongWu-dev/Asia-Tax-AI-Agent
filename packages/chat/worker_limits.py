"""Resource bounds for disposable document workers (not the API process)."""
import os
import sys

# The worker owns this non-inheritable handle for its entire lifetime. Windows
# closes it on process termination, also killing descendants in the job.
_job_handle = None


def apply_worker_limits(cpu_seconds: int, memory_mb: int):
    if os.name == 'nt':
        _windows_limits(cpu_seconds, memory_mb)
    else:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        if sys.platform == 'linux':
            resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024 * 1024,) * 2)


def _windows_limits(cpu_seconds, memory_mb):
    import ctypes as c
    from ctypes import wintypes as w
    global _job_handle
    if _job_handle is not None:
        raise RuntimeError('worker_limits_already_set')

    class Basic(c.Structure):
        _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong),
                    ('flags', w.DWORD), ('min_working_set', c.c_size_t),
                    ('max_working_set', c.c_size_t), ('active_processes', w.DWORD),
                    ('affinity', c.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]

    class IO(c.Structure):
        _fields_ = [(name, c.c_ulonglong) for name in
                    ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]

    class Extended(c.Structure):
        _fields_ = [('basic', Basic), ('io', IO), ('process_memory', c.c_size_t),
                    ('job_memory', c.c_size_t), ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]

    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
    kernel.SetInformationJobObject.restype = w.BOOL
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    kernel.AssignProcessToJobObject.restype = w.BOOL
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CloseHandle.restype = w.BOOL
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise c.WinError(c.get_last_error())
    try:
        info = Extended()
        # JOB_TIME | JOB_MEMORY | KILL_ON_JOB_CLOSE. No breakaway allowed.
        info.basic.flags = 0x4 | 0x200 | 0x2000
        info.basic.job_time = cpu_seconds * 10_000_000
        info.job_memory = memory_mb * 1024 * 1024
        if not kernel.SetInformationJobObject(handle, 9, c.byref(info), c.sizeof(info)):
            raise c.WinError(c.get_last_error())
        if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
            raise c.WinError(c.get_last_error())
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    _job_handle = handle


async def terminate_worker(proc, *, process_group=False):
    if proc.returncode is not None:
        return
    try:
        if os.name != 'nt' and process_group:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except ProcessLookupError:
        pass
    await proc.wait()
