"""Only deterministic generated-homepage maintenance, through a tested PR."""
import argparse,json,subprocess,os
from pathlib import Path
from datetime import date,datetime
from zoneinfo import ZoneInfo
from .storage import State

def allowed_changes(paths):return bool(paths) and set(paths)<= {'index.html'}
def can_propose(as_of,measures,open_prs):
    if any(p.get('headRefName','').startswith('automation/seo-maintenance-') for p in open_prs):return False
    return not any((as_of-date.fromisoformat(m['applied'])).days<28 for m in measures)

def command(repo,args):
    r=subprocess.run(args,cwd=repo,text=True,capture_output=True)
    if r.returncode:raise RuntimeError('maintenance_command_failed:'+args[0])
    return r.stdout.strip()

def maintain(repo,state,as_of,publish=False):
    repo=Path(repo).resolve()
    remote=command(repo,['git','remote','get-url','origin'])
    if remote not in ('https://github.com/nyokki519/unityHP','https://github.com/nyokki519/unityHP.git'):raise ValueError('untrusted_repository')
    if command(repo,['git','status','--porcelain']):raise ValueError('working_tree_not_clean')
    if not can_propose(as_of,state.history(),[]):return {'status':'cooldown'}
    command(repo,['node','tools/build-static.mjs']);command(repo,['python3','tools/sync-opening.py'])
    paths=command(repo,['git','diff','--name-only']).splitlines()
    if not paths:return {'status':'no_changes'}
    if not allowed_changes(paths):raise ValueError('change_outside_allowlist')
    command(repo,['git','diff','--check']);command(repo,['python3','-m','unittest','discover','-s','tests','-v'])
    diff=command(repo,['git','diff','--stat'])
    if not publish:return {'status':'dry_run','diff':diff,'changedFiles':paths}
    if not os.environ.get('GH_TOKEN'):return {'status':'github_authentication_required','diff':diff}
    prs=json.loads(command(repo,['gh','pr','list','--repo','nyokki519/unityHP','--state','open','--json','headRefName,number']))
    if not can_propose(as_of,state.history(),prs):return {'status':'open_pr_exists'}
    branch='automation/seo-maintenance-'+as_of.isoformat()
    command(repo,['git','switch','-c',branch]);command(repo,['git','add','index.html']);command(repo,['git','commit','-m','chore(seo): refresh tested static metadata and content'])
    command(repo,['git','push','origin','HEAD:refs/heads/'+branch])
    body='Refresh only generated initial HTML from approved content.js and opening sources. No new keyword copy, event dates, photo changes or rank-triggered edits. Verified static SEO tests and git diff --check. Merge remains a reviewable, reversible decision.'
    url=command(repo,['gh','pr','create','--repo','nyokki519/unityHP','--base','main','--head',branch,'--title','Refresh generated SEO content','--body',body])
    state.record_measure('maintenance:'+as_of.isoformat(),as_of.isoformat(),{'stage':'proposed','summary':'Tested static homepage maintenance PR','url':url})
    return {'status':'pr_created','url':url}

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--state',default='.state/seo.sqlite');p.add_argument('--ledger',default='state/ledger.json');p.add_argument('--publish',action='store_true');args=p.parse_args();s=State(Path(args.state))
    try:
        s.import_ledger(Path(args.ledger));result=maintain(args.repo,s,datetime.now(ZoneInfo('Asia/Tokyo')).date(),args.publish);print(json.dumps(result));return 0
    except (ValueError,RuntimeError):print('maintenance_failed');return 1
    finally:s.export_ledger(Path(args.ledger));s.close()
if __name__=='__main__':raise SystemExit(main())
