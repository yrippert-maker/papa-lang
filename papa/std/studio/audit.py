import os,re,sys,json
from dataclasses import dataclass,field
from typing import List,Optional
from datetime import datetime

@dataclass
class Finding:
    severity:str; category:str; file:str; message:str
    fix_command:Optional[str]=None; line:Optional[int]=None
    def to_dict(self): return {"severity":self.severity,"category":self.category,"file":self.file,"line":self.line,"message":self.message,"fix_command":self.fix_command}

@dataclass
class AuditReport:
    project_dir:str
    scanned_at:str=field(default_factory=lambda:datetime.utcnow().isoformat())
    findings:List[Finding]=field(default_factory=list)
    stats:dict=field(default_factory=dict)
    def add(self,f): self.findings.append(f)
    def by_severity(self,s): return [f for f in self.findings if f.severity==s]
    def summary(self):
        c,h,m,l=len(self.by_severity("CRITICAL")),len(self.by_severity("HIGH")),len(self.by_severity("MEDIUM")),len(self.by_severity("LOW"))
        return f"CRITICAL:{c} HIGH:{h} MEDIUM:{m} LOW:{l} TOTAL:{len(self.findings)}"

class DuplicateChecker:
    def run(self,d,r):
        for root,dirs,files in os.walk(d):
            dirs[:]=[x for x in dirs if x not in("node_modules",".git",".next","__pycache__")]
            for x in dirs:
            for f in files:

class SyntaxChecker:
    PAT=re.compile(r""[^"\]*
")
    def run(self,d,r):
        for root,dirs,files in os.walk(d):
            dirs[:]=[x for x in dirs if x not in("node_modules",".git",".next","__pycache__")]
            for f in files:
                if not f.endswith((".ts",".tsx")): continue
                full=os.path.join(root,f)
                try:
                    for no,ln in enumerate(open(full,encoding="utf-8",errors="ignore"),1):
                        if self.PAT.search(ln): r.add(Finding("CRITICAL","syntax",os.path.relpath(full,d),"Unterminated string",line=no))
                except: pass

class OrphanRouteChecker:
    PATS=[(r"debug","HIGH"),(r"v\d+-test","HIGH"),(r"test-\w+","MEDIUM")]
    def run(self,d,r):
        api=os.path.join(d,"app","api")
        if not os.path.exists(api): return
        for root,dirs,files in os.walk(api):
            seg=os.path.basename(root)
            for pat,sev in self.PATS:

class LargeFileChecker:
    def run(self,d,r):
        for root,dirs,files in os.walk(d):
            dirs[:]=[x for x in dirs if x not in("node_modules",".git",".next","__pycache__")]
            for f in files:
                if not f.endswith((".ts",".tsx",".py")): continue
                full=os.path.join(root,f)
                try:
                    n=len(open(full,encoding="utf-8",errors="ignore").readlines())
                    if n>500: r.add(Finding("MEDIUM","large_file",os.path.relpath(full,d),f"{n} lines (>500)"))
                except: pass

class SecurityChecker:
    PATS=[(r"ghp_[a-zA-Z0-9]{30,}","GitHub token"),(r"sk-[a-zA-Z0-9]{20,}","OpenAI key"),(r"(?i)password\s*=\s*["'][^"']{6,}","Hardcoded password")]
    def run(self,d,r):
        for root,dirs,files in os.walk(d):
            dirs[:]=[x for x in dirs if x not in("node_modules",".git",".next","__pycache__")]
            for f in files:
                if not f.endswith((".ts",".tsx",".py",".js")) or ".env" in f: continue
                full=os.path.join(root,f)
                try:
                    for no,ln in enumerate(open(full,encoding="utf-8",errors="ignore"),1):
                        for pat,msg in self.PATS:
                            if re.search(pat,ln): r.add(Finding("CRITICAL","security",os.path.relpath(full,d),f"{msg} - move to .env",line=no))
                except: pass

def run_audit(project_dir,db_path=None,fix_suggest=False,as_json=False):
    rpt=AuditReport(project_dir=project_dir)
    for ch in [DuplicateChecker(),SyntaxChecker(),OrphanRouteChecker(),LargeFileChecker(),SecurityChecker()]: ch.run(project_dir,rpt)
    if as_json: print(json.dumps({"summary":rpt.summary(),"stats":rpt.stats,"findings":[f.to_dict() for f in rpt.findings]},ensure_ascii=False,indent=2))
    else:
        C={"CRITICAL":"[91m","HIGH":"[93m","MEDIUM":"[94m","LOW":"[37m"};R="[0m";B="[1m"
        print(f"
{B}PAPA-LANG pl audit{R}
  Project: {rpt.project_dir}
  Summary: {rpt.summary()}
  Stats: {rpt.stats}
")
        for sev in ["CRITICAL","HIGH","MEDIUM","LOW"]:
            fs=rpt.by_severity(sev)
            if not fs: continue
            print(f"{C[sev]}{B}-- {sev} ({len(fs)}){R}")
            for f in fs:
                loc=f":{f.line}" if f.line else ""
                print(f"  {C[sev]}[{f.category}]{R} {f.file}{loc}
    -> {f.message}")
                if fix_suggest and f.fix_command: print(f"    {B}FIX:{R} {f.fix_command}")
            print()
    return rpt

def main():
    import argparse
    p=argparse.ArgumentParser(description="pl audit")
    p.add_argument("--project",default="."); p.add_argument("--db",default=None)
    p.add_argument("--fix-suggest",action="store_true"); p.add_argument("--json",action="store_true")
    a=p.parse_args()
    d=os.path.abspath(a.project)
    if not os.path.exists(d): print(f"ERROR: {d} not found",file=sys.stderr); sys.exit(1)
    run_audit(d,db_path=a.db,fix_suggest=a.fix_suggest,as_json=a.json)

if __name__=="__main__": main()
