import json
import os
import stat

import pytest

from bionexus.provenance import (
    ProvenanceLog,
    make_read_only,
    sha256_file,
    verify_unchanged,
)
from bionexus.records import Outcome

# SHA-256 of the three bytes b"abc" (FIPS 180 test vector)
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def write(p, data: bytes):
    p.write_bytes(data)
    return p


def test_known_hash(tmp_path):
    assert sha256_file(write(tmp_path / "a.txt", b"abc")) == ABC_SHA256


def test_empty_file_hash(tmp_path):
    assert sha256_file(write(tmp_path / "e.txt", b"")) == EMPTY_SHA256


def test_chunked_equals_single(tmp_path):
    data = b"x" * (3 * 1024 * 1024 + 7)
    p = write(tmp_path / "big.bin", data)
    import hashlib

    assert sha256_file(p) == hashlib.sha256(data).hexdigest()


def test_same_file_twice(tmp_path):
    p = write(tmp_path / "a.txt", b"hello")
    assert sha256_file(p) == sha256_file(p)


def test_one_byte_change(tmp_path):
    a = write(tmp_path / "a.txt", b"hello world")
    b = write(tmp_path / "b.txt", b"hello worle")
    assert sha256_file(a) != sha256_file(b)


def test_derived_file_leaves_input_identical(tmp_path):
    inp = write(tmp_path / "in.tsv", b"g\ts1\nA\t1\n")
    before = sha256_file(inp)
    write(tmp_path / "in.derived.tsv", b"different")
    assert sha256_file(inp) == before


def test_make_read_only_keeps_content_and_blocks_write(tmp_path):
    p = write(tmp_path / "ro.txt", b"abc")
    make_read_only(p)
    try:
        assert sha256_file(p) == ABC_SHA256
        assert not os.access(p, os.W_OK)
    finally:
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)


def test_log_round_trip(tmp_path):
    inp = write(tmp_path / "in.tsv", b"abc")
    out = write(tmp_path / "out.tsv", b"abcd")
    log = ProvenanceLog()
    log.add_input(inp)
    log.add_step(
        "G-02", "0.1", {"delimiter": "tab"}, [str(inp)], [str(out)]
    )
    text = log.to_json()
    data = json.loads(text)
    assert json.loads(json.dumps(data)) == data
    assert data["inputs"][0]["sha256"] == ABC_SHA256
    step = data["steps"][0]
    assert step["rule_id"] == "G-02"
    assert step["rule_version"] == "0.1"
    assert step["parameters"] == {"delimiter": "tab"}
    assert step["outputs"][0]["sha256"] == sha256_file(out)
    assert step["inputs"] == [str(inp)]
    sv = data["software_versions"]
    assert set(sv) == {"bionexus", "python", "pandas", "numpy"}
    assert all(isinstance(v, str) and v for v in sv.values())

    dest = tmp_path / "prov.json"
    log.write(dest)
    assert json.loads(dest.read_text(encoding="utf-8")) == data


def test_software_versions_per_output(tmp_path):
    out = write(tmp_path / "o.txt", b"abc")
    log = ProvenanceLog()
    log.add_step("V-02", "0.1", {}, [], [str(out)])
    entry = json.loads(log.to_json())["steps"][0]["outputs"][0]
    assert entry["sha256"] == ABC_SHA256
    assert set(entry["software_versions"]) == {"bionexus", "python", "pandas", "numpy"}


def test_verify_unchanged_pass(tmp_path):
    p = write(tmp_path / "a.txt", b"abc")
    r = verify_unchanged(p, ABC_SHA256)
    assert r.outcome is Outcome.PASS
    assert r.rule_id == "G-04"


def test_verify_unchanged_blocked_after_tamper(tmp_path):
    p = write(tmp_path / "a.txt", b"abc")
    h = sha256_file(p)
    p.write_bytes(b"abd")
    r = verify_unchanged(p, h)
    assert r.outcome is Outcome.BLOCKED
    assert r.rule_id == "G-04"
    json.dumps(r.to_dict())


def test_verify_unchanged_missing_file_blocked(tmp_path):
    r = verify_unchanged(tmp_path / "nope.txt", ABC_SHA256)
    assert r.outcome is Outcome.BLOCKED
