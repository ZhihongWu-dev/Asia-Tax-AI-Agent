import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'database/tools'))
spec = importlib.util.spec_from_file_location('library_builder_office', ROOT / 'database/tools/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.fixture
def conversion(tmp_path, monkeypatch):
    exe = tmp_path / 'converter.exe'
    exe.write_bytes(b'test executable placeholder')
    monkeypatch.setattr(build, 'SOFFICE', str(exe))
    conv = tmp_path / 'laws 中文'
    conv.mkdir()
    source = tmp_path / 'original.rtf'
    source.write_bytes(b'original unchanged')
    return conv, [(source, 'rtf', 'law')]


@pytest.mark.parametrize('failure', ['nonzero', 'missing', 'empty'])
def test_failed_conversion_cannot_reuse_stale_output(conversion, monkeypatch, failure):
    conv, jobs = conversion
    old = conv / 'law.txt'
    old.write_bytes(b'previous output')
    def run(args, **kwargs):
        output = Path(args[args.index('--outdir') + 1]) / 'law.txt'
        if failure == 'empty': output.write_bytes(b'')
        return SimpleNamespace(returncode=1 if failure == 'nonzero' else 0)
    monkeypatch.setattr(build.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match='LibreOffice'):
        build.soffice_convert(jobs, conv)
    assert old.read_bytes() == b'previous output'
    assert jobs[0][0].read_bytes() == b'original unchanged'


def test_conversion_uses_encoded_profile_and_publishes_verified_result(conversion, monkeypatch):
    conv, jobs = conversion
    def run(args, **kwargs):
        profile = next(a.split('=', 1)[1] for a in args if a.startswith('-env:UserInstallation='))
        assert profile == (conv / 'lo_profile').resolve().as_uri()
        assert '%20' in profile and '中文' not in profile
        output = Path(args[args.index('--outdir') + 1])
        assert output != conv and output.is_relative_to(conv)
        (output / 'law.txt').write_text('converted law', encoding='utf-8')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(build.subprocess, 'run', run)
    build.soffice_convert(jobs, conv)
    assert (conv / 'law.txt').read_text(encoding='utf-8') == 'converted law'
    assert not list(conv.glob('converted_*'))


def test_partial_batch_does_not_publish_any_result(conversion, monkeypatch):
    conv, jobs = conversion
    jobs.append((jobs[0][0], 'rtf', 'second'))
    def run(args, **kwargs):
        (Path(args[args.index('--outdir') + 1]) / 'law.txt').write_bytes(b'only first output')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(build.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match='every expected output'):
        build.soffice_convert(jobs, conv)
    assert not (conv / 'law.txt').exists()
