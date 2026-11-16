"""Restrict application-owned log files using the platform's access controls."""
import os


def make_private(path, *, directory=False):
    if os.name != 'nt':
        os.chmod(path, 0o700 if directory else 0o600)
        return
    import ctypes as c
    from ctypes import wintypes as w
    advapi = c.WinDLL('advapi32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = w.BOOL
    advapi.GetSecurityDescriptorDacl.argtypes = [c.c_void_p, c.POINTER(w.BOOL), c.POINTER(c.c_void_p), c.POINTER(w.BOOL)]
    advapi.GetSecurityDescriptorDacl.restype = w.BOOL
    advapi.SetNamedSecurityInfoW.argtypes = [w.LPWSTR, c.c_int, w.DWORD, c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p]
    advapi.SetNamedSecurityInfoW.restype = w.DWORD
    kernel.LocalFree.argtypes = [c.c_void_p]
    kernel.LocalFree.restype = c.c_void_p
    # Protected DACL: only the object's owner and LocalSystem. Directory ACEs
    # inherit to new logs; existing files are explicitly secured before writing.
    inheritance = 'OICI' if directory else ''
    sddl = 'D:P(A;'+inheritance+';FA;;;OW)(A;'+inheritance+';FA;;;SY)'
    descriptor = c.c_void_p()
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, c.byref(descriptor), None):
        raise c.WinError(c.get_last_error())
    try:
        present, defaulted, acl = w.BOOL(), w.BOOL(), c.c_void_p()
        if not advapi.GetSecurityDescriptorDacl(descriptor, c.byref(present), c.byref(acl), c.byref(defaulted)):
            raise c.WinError(c.get_last_error())
        if not present or not acl:
            raise OSError('Private DACL was not constructed')
        result = advapi.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, acl, None)
        if result:
            raise c.WinError(result)
    finally:
        kernel.LocalFree(descriptor)
