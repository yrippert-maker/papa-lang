#!/usr/bin/env python3
# papa-lang std/infra/deploy.py
import subprocess, sys, os, time
from datetime import datetime

R="[0;31m";G="[0;32m";Y="[1;33m";B="[0;34m";C="[0;36m";N="[0m"

def say(m,c=N): print(f"{c}[{datetime.now().strftime('%H:%M:%S')}] {m}{N}")
def run(cmd):
    r=subprocess.run(cmd,shell=True,capture_output=True,text=True)
    return r.returncode==0, r.stdout.strip()+r.stderr.strip()
def stream(cmd):
    p=subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    o=[]
    for l in p.stdout:
        l=l.rstrip()
        if l: print(f"  {C}{l}{N}"); o.append(l)
    p.wait(); return p.returncode==0,"
".join(o)

SVC={
  "papa-frontend":{"container":"papa-frontend-prod","image":"papa-ecosystem-frontend:latest","port":"3000:3000","build":"/opt/papa-ecosystem","env":"/opt/papa-ecosystem-new/.env.production","net":"papa-ecosystem_papa-network","url":"https://app.papa-ai.ae","extra":{"NODE_ENV":"production","NEXTAUTH_URL":"https://app.papa-ai.ae"}},
  "papa-api":{"container":"papa-api-prod","image":"papa-ecosystem-api:latest","port":"8000:8000","build":None,"env":"/opt/papa-ecosystem-new/.env.production","net":"papa-ecosystem_papa-network","url":"http://localhost:8000/health","extra":{"NODE_ENV":"production"}}
}

def deploy(name, skip_build=False):
    if name not in SVC: say(f"Unknown: {name}. Use: {list(SVC.keys())}",R); return False
    c=SVC[name]; t=time.time()
    say(f"Deploy: {name}",B)
    if not skip_build and c.get("build"):
        say("Building...",B)
        ok,_=stream(f"cd {c['build']} && docker build -t {c['image']} .")
        if not ok: say("Build failed!",R); return False
    run(f"docker rm -f {c['container']} 2>/dev/null")
    ex=" ".join([f"-e {k}={v}" for k,v in c.get("extra",{}).items()])
    ok,out=run(f"docker run -d --name {c['container']} --restart unless-stopped --network {c['net']} -p {c['port']} --env-file {c['env']} {ex} {c['image']}")
    if not ok: say(f"Failed: {out[:200]}",R); return False
    say(f"Started! {time.time()-t:.1f}s",G)
    return True

def status():
    say("PAPA Status",B)
    for n,c in SVC.items():
        ok,s=run(f"docker inspect {c['container']} --format {{{{.State.Status}}}}")
        say(f"  {n:20} {s.strip()}", G if s.strip()=="running" else R)

import argparse
p=argparse.ArgumentParser(prog="pl deploy")
s=p.add_subparsers(dest="cmd")
d=s.add_parser("deploy"); d.add_argument("service"); d.add_argument("--skip-build",action="store_true")
s.add_parser("status")
a=p.parse_args()
if a.cmd=="deploy": sys.exit(0 if deploy(a.service,a.skip_build) else 1)
elif a.cmd=="status": status()
else: p.print_help()
