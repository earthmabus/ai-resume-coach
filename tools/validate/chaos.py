#!/usr/bin/env python3
"""MR-014 end-to-end chaos certification catalog and evidence evaluator."""
from __future__ import annotations
import argparse, json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

@dataclass(frozen=True)
class Scenario:
    id: str; title: str; mutating: bool; proves: tuple[str, ...]; restoration: str | None

SCENARIOS=(
 Scenario('guard-both-sites','Reject disabling both sites',False,('routing invariant',),None),
 Scenario('bidirectional-routing','Bidirectional regional isolation and survivor workflow',True,('DNS convergence','authenticated survivor writes','owner-region correctness','cross-region reads','routing restoration'),'both routing records restored'),
 Scenario('worker-backlog','Regional worker interruption, backlog retention, replay, and drain',True,('event-source interruption','durable backlog','idempotent duplicate submission','worker restoration','terminal completion','queue drain'),'event source mapping enabled'),
 Scenario('post-recovery','Post-recovery platform reconciliation',False,('both regions ready','MRSC healthy','authenticated global read','no unresolved restoration'),None),
)

def catalog():
 return {'schemaVersion':2,'generatedAt':datetime.now(timezone.utc).isoformat(),'milestone':'MR-014','certification':'END_TO_END_CHAOS_AND_FAILURE','scenarios':[asdict(x) for x in SCENARIOS],'safety':{'mutationsRequire':['CONFIRM_MUTATION=YES','EXECUTE_CHAOS=YES'],'automaticRestorationRequired':True,'bothSitesDisabledForbidden':True,'routingPlanMustBeRoutingOnly':True}}

def evaluate(payload):
 supplied=payload.get('scenarios',{}) if isinstance(payload,dict) else {}; rows=[]; errors=[]
 for s in SCENARIOS:
  obs=supplied.get(s.id,{}) or {}; status=obs.get('status','NOT_RUN'); restored=obs.get('restored')
  if status not in {'PASS','NOT_RUN'}: errors.append(f'{s.id}: status={status}')
  if s.restoration and status=='PASS' and restored is not True: errors.append(f'{s.id}: restoration was not proven')
  checks=obs.get('checks',{}) or {}
  failed=[k for k,v in checks.items() if v is not True]
  if status=='PASS' and failed: errors.append(f"{s.id}: failed checks={','.join(failed)}")
  rows.append({'id':s.id,'status':status,'restored':restored,'checks':checks,'evidence':obs.get('evidence')})
 executed=[x for x in rows if x['status']!='NOT_RUN']
 required={s.id for s in SCENARIOS}; passed={x['id'] for x in rows if x['status']=='PASS'}
 complete=required <= passed
 if executed and not complete: errors.append('certification incomplete: every MR-014 scenario must pass')
 result='NOT_RUN' if not executed else ('PASS' if complete and not errors else 'FAIL')
 return {'schemaVersion':2,'generatedAt':datetime.now(timezone.utc).isoformat(),'result':result,'errors':errors,'summary':{'total':len(rows),'executed':len(executed),'passed':len(passed),'complete':complete},'scenarios':rows}

def main():
 p=argparse.ArgumentParser(); p.add_argument('command',choices=('catalog','evaluate')); p.add_argument('--results',type=Path); p.add_argument('--output',type=Path); a=p.parse_args()
 out=catalog() if a.command=='catalog' else evaluate(json.loads(a.results.read_text()) if a.results else {})
 text=json.dumps(out,indent=2,sort_keys=True)
 if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(text+'\n')
 print(text); return 1 if out.get('result')=='FAIL' else 0
if __name__=='__main__': raise SystemExit(main())
