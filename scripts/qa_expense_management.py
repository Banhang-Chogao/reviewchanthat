#!/usr/bin/env python3
"""QA checks for Expense Management."""

import hashlib, os, re, sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []
def e(m): errors.append(m); print(f"  FAIL: {m}")
def o(m): print(f"  OK: {m}")

def rf(p):
    try:
        with open(p,"rb") as f: r=f.read()
        return r.decode("utf-8") if r else None
    except: return None

def check_plaintext_code():
    for base in ["public","static","layouts","assets"]:
        b=os.path.join(ROOT,base)
        if not os.path.isdir(b): continue
        for root,dirs,files in os.walk(b):
            for fn in files:
                p=os.path.join(root,fn); ext=os.path.splitext(fn)[1]
                if ext in(".py",".md",".css",".gitignore",".toml",".json",".lock"): continue
                c=rf(p)
                if c and "9898" in c: e(f"Plaintext '9898' found in {p}"); return
    o("No plaintext '9898'")

def check_no_secrets():
    pats=["private_key","github_token","ghp_"]
    for base in ["public","static","layouts","assets","data"]:
        b=os.path.join(ROOT,base)
        if not os.path.isdir(b): continue
        for root,dirs,files in os.walk(b):
            for fn in files:
                c=rf(os.path.join(root,fn))
                if c:
                    for pat in pats:
                        if pat in c: e(f"Secret '{pat}' in {os.path.join(root,fn)}"); return
    o("No secrets")

def check_no_expense_in_sitemap():
    s=rf(os.path.join(ROOT,"public","sitemap.xml"))
    if s and "expense-management" in s: e("expense-management in sitemap")
    else: o("NOT in sitemap")
    r=rf(os.path.join(ROOT,"public","index.xml"))
    if r and "expense-management" in r: e("expense-management in RSS")
    else: o("NOT in RSS")

def check_front_matter():
    p=os.path.join(ROOT,"content","doi-song","expense-management","_index.md")
    c=rf(p)
    if not c: e("_index.md not found"); return
    if "+++" not in c: e("Must be TOML"); return
    try: fm=tomllib.loads(c.split("+++")[1].strip())
    except: e("Cannot parse TOML"); return
    if fm.get("title")!="Expense Management": e("wrong title")
    else: o("title OK")
    if fm.get("robots")!="noindex,nofollow": e("wrong robots")
    else: o("robots OK")
    if fm.get("layout")!="expense-management": e("wrong layout")
    else: o("layout OK")
    ds=str(fm.get("date",""))
    if "+07:00" not in ds: e(f"date missing +07:00: {ds}")
    else: o("date OK")

def check_files():
    req=["content/doi-song/expense-management/_index.md","layouts/doi-song/expense-management.html","assets/css/expense-management.css","static/js/expense-management.js","static/js/expense-insights-engine.js","static/data/expense-management-schema.json","scripts/qa_expense_management.py","docs/expense-management.md"]
    for r in req:
        if os.path.isfile(os.path.join(ROOT,r)): o(f"Exists: {r}")
        else: e(f"Missing: {r}")

def check_gitignore():
    c=rf(os.path.join(ROOT,".gitignore"))
    for p in ["private-data/","data/private-expense-management","static/private-expense-management","*.expense-management.private.json"]:
        if p in c: o(f"gitignore: {p}")
        else: e(f"gitignore missing {p}")

def check_access_hash():
    c=rf(os.path.join(ROOT,"static/js/expense-management.js"))
    if not c: e("JS not found"); return
    h=hashlib.sha256(b"9898").hexdigest()
    if h in c: o("Access hash OK")
    else: e("Access hash mismatch")
    if "9898" in c.replace(h,""):
        for i,ln in enumerate(c.split("\n"),1):
            if "9898" in ln and h not in ln: e(f"Plaintext 9898 at line {i}"); return
    o("No plaintext 9898")

def main():
    print("=== Expense Management QA ===")
    check_files(); check_front_matter(); check_plaintext_code()
    check_no_secrets(); check_no_expense_in_sitemap()
    check_gitignore(); check_access_hash()
    print(f"\nResults: {len(errors)} errors")
    for err in errors: print(f"  - {err}")
    sys.exit(1 if errors else 0)

if __name__=="__main__": main()
