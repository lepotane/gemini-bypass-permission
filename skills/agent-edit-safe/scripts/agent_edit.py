#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_edit.py - geri donus garantili dosya duzenleyici.

Her yazma oncesi yedek alir, atomik olarak yazar, dogrular ve dogrulama
basarisizsa otomatik olarak eski haline geri yukler.

EXIT CODES
  0  degisiklik yapildi ve dogrulama basarili
  1  dogrulama basarisiz -> DEGISIKLIK GERI ALINDI
  2  hicbir sey degismedi (arguman hatasi / eslesme yok / dosya yok)
  3  yedekleme basarisiz -> hicbir sey yazilmadi
"""

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_ROOT = os.path.join(os.path.dirname(TOOL_DIR), "backups")

# Dogrulama zorunlu olan dosya kaliplari
CRITICAL_EXT = {
    ".cmake", ".pem", ".key", ".pfx", ".p12", ".sln", ".vcxproj",
    ".vcxproj.filters", ".env", ".gitignore", ".gitattributes",
}
CRITICAL_NAMES = {
    "cmakelists.txt", "makefile", "package.json", "version",
    "cargo.toml", "go.mod", "requirements.txt", "dockerfile",
}


# ---------------------------------------------------------------- yardimcilar

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_critical(path):
    name = os.path.basename(path).lower()
    ext = os.path.splitext(path)[1].lower()
    return name in CRITICAL_NAMES or ext in CRITICAL_EXT


def path_is_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".ico", ".exe", ".dll", ".zip",
               ".7z", ".pdf", ".bin", ".obj", ".lib", ".pdb", ".so", ".dylib",
               ".ttf", ".otf", ".wav", ".mp3", ".ico", ".icns"):
        return False
    return True


def find_project_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def project_key(root):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(root.rstrip("\\/")))
    h = hashlib.sha1(root.encode("utf-8")).hexdigest()[:8]
    return "%s-%s" % (safe or "proje", h)


def backup_dir_for(root):
    return os.path.join(BACKUP_ROOT, project_key(root))


# ------------------------------------------------------------------ yedekleme

def create_backup(path, root):
    """Tek dosya icin yedek olusturur, backup_id dondurur."""
    bdir = backup_dir_for(root)
    os.makedirs(bdir, exist_ok=True)

    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    n = 1
    while True:
        bid = "%s_%03d" % (stamp, n)
        bpath = os.path.join(bdir, bid)
        if not os.path.exists(bpath):
            break
        n += 1
        time.sleep(0.05)

    files_dir = os.path.join(bpath, "files")
    os.makedirs(files_dir, exist_ok=True)

    rel = os.path.relpath(os.path.abspath(path), root)
    # windows'ta guvenli ad
    dest = os.path.join(files_dir, rel.replace(":", "_"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    existed = os.path.isfile(path)
    if existed:
        shutil.copy2(path, dest)

    manifest = {
        "id": bid,
        "project_root": root,
        "path": os.path.abspath(path),
        "rel": rel,
        "existed": existed,
        "created": now.isoformat(timespec="seconds"),
        "hash_before": sha256(path) if existed else None,
    }
    with open(os.path.join(bpath, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return bid, bpath


def restore_backup(bid, root, expect_hash=True):
    """Yedegi geri yukler. False donerse dosya ustunde ariza vardir."""
    bpath = os.path.join(backup_dir_for(root), bid)
    mpath = os.path.join(bpath, "manifest.json")
    if not os.path.isfile(mpath):
        raise FileNotFoundError("yedek bulunamadi: %s" % bid)

    with open(mpath, "r", encoding="utf-8") as f:
        m = json.load(f)

    target = m["path"]

    if not m["existed"]:
        # dosya yoktu -> oluşturulmuştu, sil
        if os.path.isfile(target):
            if expect_hash and m.get("hash_after") and sha256(target) != m["hash_after"]:
                raise RuntimeError(
                    "DOSYA DEGISTIRILMIS - otomatik silinmedi: %s" % target)
            os.remove(target)
        return "silindi (dosya yoktu)"

    src = os.path.join(bpath, "files", m["rel"].replace(":", "_"))
    if not os.path.isfile(src):
        raise FileNotFoundError("yedek dosyasi eksik: %s" % src)
    shutil.copy2(src, target)
    return "geri yuklendi"


def list_backups(root):
    bdir = backup_dir_for(root)
    if not os.path.isdir(bdir):
        return []
    out = []
    for bid in sorted(os.listdir(bdir), reverse=True):
        mpath = os.path.join(bdir, bid, "manifest.json")
        if os.path.isfile(mpath):
            try:
                with open(mpath, "r", encoding="utf-8") as f:
                    m = json.load(f)
                out.append((bid, m))
            except Exception:
                pass
    return out


def prune_backups(root, keep):
    entries = list_backups(root)
    removed = 0
    for bid, _ in entries[keep:]:
        p = os.path.join(backup_dir_for(root), bid)
        try:
            shutil.rmtree(p)
            removed += 1
        except Exception:
            pass
    return removed


# ------------------------------------------------------------------ dogrulama

def verify_static(path, text):
    """Metin uzerinden hizli dogrulama. (True, '') veya (False, hata)."""
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path).lower()
    try:
        if ext == ".py":
            ast.parse(text)
        elif ext == ".json":
            json.loads(text)
        elif ext == ".jsonc":
            json.loads(re.sub(r"//.*", "", text))
        elif ext == ".md":
            pass
        elif ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            if text.count("{") != text.count("}"):
                return False, "süslü parantez dengesiz"
            if text.count("(") != text.count(")"):
                return False, "parantez dengesiz"
            if text.count("[") != text.count("]"):
                return False, "köşeli parantez dengesiz"
        elif ext in (".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hxx", ".m", ".mm"):
            if text.count("{") != text.count("}"):
                return False, "süslü parantez dengesiz"
            if text.count("(") != text.count(")"):
                return False, "parantez dengesiz"
        elif name == "cmakelists.txt" or ext == ".cmake":
            if text.count("(") != text.count(")"):
                return False, "cmake parantez dengesiz"
            if not text.rstrip().endswith((")", ")", "endif", "endfunction", "endmacro")) \
                    and "cmake_minimum_required" in text:
                return False, "cmake dosyasi yarim kalmis olabilir"
        elif name in ("makefile", "dockerfile"):
            if not text.endswith("\n"):
                return False, "son satirda satir sonu yok"
        else:
            if not text.strip():
                return False, "dosya bos"
    except SyntaxError as e:
        return False, "syntax hatasi: %s (satir %s)" % (e.msg, e.lineno)
    except Exception as e:
        return False, "dogrulama hatasi: %s" % e
    return True, ""


def verify_cmd(cmd, cwd, timeout=1800):
    try:
        p = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, errors="replace", timeout=timeout,
        )
        out = ((p.stdout or "") + (p.stderr or ""))[-3000:]
        return p.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "dogrulama komutu zaman asimina ugradi (%ss)" % timeout
    except Exception as e:
        return False, "dogrulama komutu hatasi: %s" % e


# --------------------------------------------------------------------- yazma

# --------------------------------------------------------- encoding / EOL

BOM_UTF8 = b"\xef\xbb\xbf"
BOM_UTF16LE = b"\xff\xfe"
BOM_UTF16BE = b"\xfe\xff"


def detect_encoding(path):
    """Dosyanin BOM ve ic kodlamasini belirler. (codec, bom_bytes, eol)"""
    with open(path, "rb") as f:
        head = f.read(4)
        f.seek(0)
        raw = f.read()

    if head.startswith(BOM_UTF8):
        return "utf-8-sig", BOM_UTF8, detect_eol(raw[3:])
    if head.startswith(BOM_UTF16LE):
        return "utf-16", BOM_UTF16LE, detect_eol(raw[2:])
    if head.startswith(BOM_UTF16BE):
        return "utf-16-be", BOM_UTF16BE, detect_eol(raw[2:])

    # BOM yoksa UTF-8 dene, degmezse cp1254 ( Turkce Windows )
    try:
        raw.decode("utf-8")
        return "utf-8", b"", detect_eol(raw)
    except UnicodeDecodeError:
        return "cp1254", b"", detect_eol(raw)


def detect_eol(raw):
    """Dosyada baskin satir sonunu bulur.混 default '\\r\\n' (Windows)."""
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    cr = raw.count(b"\r") - crlf
    if crlf == 0 and lf == 0 and cr == 0:
        return None
    if lf > crlf and lf > cr:
        return "\n"
    if cr > crlf and cr > lf:
        return "\r"
    return "\r\n"


def read_file_raw(path):
    """Dosyayi BOM ve satir sonlarina DOKUNMADAN okur.

    newline="" yoksa Python text mode CRLF -> LF cevirir ve yazarken
    dosyanin tum satir sonlari degisir. Bu yasak.
    """
    enc, bom, _ = detect_encoding(path)
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(bom):
        raw = raw[len(bom):]
    return raw.decode(enc, errors="surrogateescape")


def write_atomic(path, text, enc="utf-8", bom=b"", eol=None):
    """Atomik yazar. text icinde satir sonlari zaten dogru formattadir;
    bu yuzden newline='' ile YAZARIZ ama text'i degistirmeyiz."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "." + os.path.basename(path) + ".agent_edit.tmp")
    with open(tmp, "wb") as f:
        if bom:
            f.write(bom)
        f.write(text.encode(enc, errors="surrogateescape"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_text(path):
    """Uyumluluk fonksiyonu - EOL korumali."""
    return read_file_raw(path)


# ---------------------------------------------------------------------- main

def normalize_argv(argv):
    """'-' ile baslayan degerleri --opt=deger bicimine cevirir.

    argparse '--replace -\\1' degerini gormez, secenek sanir.
    '--replace=-\\1' calisir. Burada otomatik duzeltiyoruz.
    """
    out = []
    takes_value = {"--path", "--content-file", "--find", "--replace",
                   "--gsub", "--count", "--verify-cmd", "--project-root",
                   "--rollback", "--prune"}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in takes_value and i + 1 < len(argv):
            nxt = argv[i + 1]
            if nxt.startswith("-") and not nxt.startswith("--") \
                    and a not in ("--count", "--prune"):
                out.append("%s=%s" % (a, nxt))
                i += 2
                continue
            out.extend([a, nxt])
            i += 2
            continue
        out.append(a)
        i += 1
    return out


def build_parser():
    p = argparse.ArgumentParser(
        prog="agent_edit.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Geri donus garantili dosya duzenleyici.",
    )
    p.add_argument("--path", help="duzenlenecek dosya")
    p.add_argument("--content-file", help="tam yeni icerik bu dosyadan")
    p.add_argument("--stdin", action="store_true",
                   help="tam yeni icerigi STDIN'den oku ( tirnak kacisi sorunu yok )")
    p.add_argument("--patch-file", help="JSON dosya: toplu find/replay deseni")
    p.add_argument("--find", help="aranacek metin")
    p.add_argument("--replace", help="degistirilecek metin")
    p.add_argument("--gsub", help="regex deseni")
    p.add_argument("--all", action="store_true", help="tum eslesmeleri degistir")
    p.add_argument("--count", type=int, default=0, help="sadece ilk N eslesme")
    p.add_argument("--create", action="store_true", help="dosya yoksa olustur")
    p.add_argument("--verify-cmd", help="yazma sonrasi calistirilacak dogrulama komutu")
    p.add_argument("--skip-verify", action="store_true", help="statik dogrulamayi atla")
    p.add_argument("--project-root", help="proje kokunu elle ver")
    p.add_argument("--rollback", help="yedek id ile geri al")
    p.add_argument("--rollback-list", action="store_true", help="yedekleri listele")
    p.add_argument("--prune", type=int, metavar="N", help="en son N yedegi birak")
    return p


def main():
    args = build_parser().parse_args(normalize_argv(sys.argv[1:]))

    # ---------------------------------------------------- geri alma modu
    if args.rollback_list:
        root = args.project_root or os.getcwd()
        entries = list_backups(find_project_root(root))
        if not entries:
            print("Yedek bulunamadi (%s)" % backup_dir_for(find_project_root(root)))
            return 0
        print("Yedekler (%d):" % len(entries))
        for bid, m in entries:
            print("  %s  %s  %s" % (bid, m.get("created", "?"), m.get("rel", "?")))
        return 0

    if args.rollback:
        root = find_project_root(args.project_root or os.getcwd())
        try:
            res = restore_backup(args.rollback, root)
            print("Geri alindi [%s]: %s -> %s" % (args.rollback, res, args.rollback))
            print("Geri alinan dosya: %s" % args.rollback)
            return 0
        except Exception as e:
            print("Geri alma BASARISIZ: %s" % e, file=sys.stderr)
            return 3

    if args.prune is not None:
        root = find_project_root(args.project_root or os.getcwd())
        print("Silinen yedek: %d" % prune_backups(root, max(1, args.prune)))
        return 0

    if not args.path:
        print("HATA: --path gerekli", file=sys.stderr)
        return 2

    path = os.path.abspath(args.path)
    root = find_project_root(args.project_root or os.path.dirname(path) or os.getcwd())

    if not os.path.isfile(path):
        if not args.create:
            print("HATA: dosya yok: %s (yeni dosya icin --create kullan)" % path,
                  file=sys.stderr)
            return 2
        old_text = ""
        enc, bom, eol = "utf-8", b"", None
    else:
        enc, bom, eol = detect_encoding(path)
        old_text = read_file_raw(path)
        if eol is None:
            eol = "\r\n" if path_is_text(path) else "\n"

    # ------------------------------------------------------ yeni icerik
    if args.stdin:
        # Tirnak / backslash kacisi sorunu YOK: shell hicbir sey gormez.
        data = sys.stdin.buffer.read()
        if data.startswith(BOM_UTF8):
            data = data[len(BOM_UTF8):]
        new_text = data.decode(enc if enc != "utf-8-sig" else "utf-8",
                               errors="surrogateescape")
        action = "stdin ile tam yazma"

    elif args.patch_file:
        if not os.path.isfile(args.patch_file):
            print("HATA: --patch-file bulunamadi: %s" % args.patch_file,
                  file=sys.stderr)
            return 2
        try:
            with open(args.patch_file, "r", encoding="utf-8") as f:
                ops = json.load(f)
        except Exception as e:
            print("HATA: --patch-file okunamadi: %s" % e, file=sys.stderr)
            return 2
        if isinstance(ops, dict):
            ops = [ops]
        new_text = old_text
        applied = 0
        for idx, op in enumerate(ops):
            pattern = op.get("find")
            repl = op.get("replace", "")
            if pattern is None:
                print("HATA: patch[%d] icinde 'find' eksik" % idx, file=sys.stderr)
                return 2
            if repl is None:
                repl = ""
            if op.get("regex"):
                try:
                    rx = re.compile(pattern, re.MULTILINE)
                except re.error as e:
                    print("HATA: patch[%d] gecersiz regex: %s" % (idx, e),
                          file=sys.stderr)
                    return 2
                if not rx.search(new_text):
                    print("HATA: patch[%d] deseni eslesmedi: %r" % (idx, pattern),
                          file=sys.stderr)
                    return 2
                limit = 0 if op.get("all") else (op.get("count") or 1)
                new_text, k = rx.subn(repl, new_text, count=limit)
            else:
                n = new_text.count(pattern)
                if n == 0:
                    print("HATA: patch[%d] deseni eslesmedi: %r" % (idx, pattern),
                          file=sys.stderr)
                    return 2
                if op.get("all"):
                    new_text = new_text.replace(pattern, repl)
                    k = n
                else:
                    new_text = new_text.replace(pattern, repl, op.get("count") or 1)
                    k = min(n, op.get("count") or 1)
            applied += k
        action = "patch dosyasi (%d degisiklik)" % applied

    elif args.content_file:
        if not os.path.isfile(args.content_file):
            print("HATA: --content-file bulunamadi: %s" % args.content_file,
                  file=sys.stderr)
            return 2
        nf_enc, _, _ = detect_encoding(args.content_file)
        with open(args.content_file, "rb") as f:
            nb = f.read()
        if nb.startswith(BOM_UTF8):
            nb = nb[len(BOM_UTF8):]
        new_text = nb.decode(nf_enc if nf_enc != "utf-8-sig" else "utf-8",
                             errors="surrogateescape")
        action = "tam yazma"

    elif args.gsub:
        if args.replace is None:
            print("HATA: --gsub ile --replacement birlikte kullanilir", file=sys.stderr)
            return 2
        try:
            rx = re.compile(args.gsub, re.MULTILINE)
        except re.error as e:
            print("HATA: gecersiz regex: %s" % e, file=sys.stderr)
            return 2
        n = 0
        limit = len(old_text) if args.all else (args.count or 1)
        out = []
        pos = 0
        for m in rx.finditer(old_text):
            if n >= limit:
                break
            out.append(old_text[pos:m.start()])
            out.append(m.expand(args.replace) if "\\" in args.replace
                       else args.replace)
            pos = m.end()
            n += 1
        out.append(old_text[pos:])
        if n == 0:
            print("HATA: --gsub eslesmedi: %s" % args.gsub, file=sys.stderr)
            return 2
        new_text = "".join(out)
        action = "regex (%d eslesme)" % n

    elif args.find:
        if args.replace is None:
            print("HATA: --find ile --replacement birlikte kullanilir", file=sys.stderr)
            return 2
        cnt = old_text.count(args.find)
        if cnt == 0:
            print("HATA: --find eslesmedi: %r" % args.find, file=sys.stderr)
            return 2
        limit = cnt if args.all else min(args.count or 1, cnt)
        new_text = old_text.replace(args.find, args.replace, limit)
        action = "find/replace (%d/%d)" % (limit, cnt)

    else:
        print("HATA: --content-file, --find veya --gsub gerekli", file=sys.stderr)
        return 2

    if new_text == old_text:
        print("HATA: yeni icerik eskisiyle ayni, degisiklik yok", file=sys.stderr)
        return 2

    # --------------------------------------------------------- yedekle
    try:
        bid, bpath = create_backup(path, root)
    except Exception as e:
        print("HATA: yedekleme basarisiz, HICBIR SEY YAZILMADI: %s" % e,
              file=sys.stderr)
        return 3

    # ------------------------------------------------------------- yaz
    try:
        write_atomic(path, new_text, enc=enc, bom=bom, eol=eol)
    except Exception as e:
        try:
            restore_backup(bid, root)
        except Exception:
            pass
        print("HATA: yazma basarisiz, geri alindi: %s" % e, file=sys.stderr)
        return 3

    # ------------------------------------------------------- dogrulama
    problems = []

    if not args.skip_verify:
        ok, msg = verify_static(path, new_text)
        if not ok:
            problems.append("statik: " + msg)

    if args.verify_cmd:
        ok, out = verify_cmd(args.verify_cmd, root)
        if not ok:
            problems.append("verify-cmd basarisiz:\n" + out)

    if problems:
        try:
            restore_backup(bid, root)
            print("DOGRULAMA BASARISIZ - DEGISIKLIK GERI ALINDI")
            for p in problems:
                print("  - " + p)
            print("Yedek id: %s (bu yedek artik kullanilamiyor, dosya eski halinde)"
                  % bid)
            return 1
        except Exception as e:
            print("DOGRULAMA BASARISIZ VE GERI ALINAMADI: %s" % e, file=sys.stderr)
            for p in problems:
                print("  - " + p)
            print("Yedek id: %s" % bid)
            return 3

    # basari
    if is_critical(path):
        print("DIKKAT: kritik dosya dogrulandi ama gozden gecir: %s" % path)

    print("OK  %s  ->  %s" % (action, path))
    print("    %d -> %d byte" % (len(old_text.encode("utf-8")),
                                len(new_text.encode("utf-8"))))
    print("    Yedek id: %s" % bid)
    print("    Geri almak icin: --rollback %s" % bid)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print("BEKLENMEYEN HATA: %s" % e, file=sys.stderr)
        sys.exit(3)
