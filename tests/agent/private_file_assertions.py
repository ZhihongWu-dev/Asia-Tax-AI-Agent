import os


def assert_private(path):
    if os.name != 'nt':
        assert path.stat().st_mode & 0o077 == 0
        return
    import ctypes as c
    from ctypes import wintypes as w
    advapi=c.WinDLL('advapi32',use_last_error=True)
    kernel=c.WinDLL('kernel32',use_last_error=True)
    advapi.GetNamedSecurityInfoW.argtypes=[w.LPWSTR,c.c_int,w.DWORD,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p,c.POINTER(c.c_void_p)]
    advapi.GetNamedSecurityInfoW.restype=w.DWORD
    advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes=[c.c_void_p,w.DWORD,w.DWORD,c.POINTER(c.c_void_p),c.c_void_p]
    advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype=w.BOOL
    kernel.LocalFree.argtypes=[c.c_void_p];kernel.LocalFree.restype=c.c_void_p
    descriptor, text=c.c_void_p(),c.c_void_p()
    result=advapi.GetNamedSecurityInfoW(str(path),1,4,None,None,None,None,c.byref(descriptor))
    assert result==0,result
    try:
        assert advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor,1,4,c.byref(text),None)
        sddl=c.wstring_at(text)
        assert sddl.startswith('D:P'),sddl
        import re
        aces=re.findall(r'\(([^)]+)\)',sddl)
        assert len(aces)==2,sddl
        assert {a.split(';')[-1] for a in aces}=={'OW','SY'},sddl
        assert all(a.split(';')[0]=='A' and a.split(';')[2]=='FA' for a in aces),sddl
    finally:
        if text: kernel.LocalFree(text)
        kernel.LocalFree(descriptor)
