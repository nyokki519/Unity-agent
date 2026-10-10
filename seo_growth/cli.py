"""Run weekly, write managed reports, optionally ingest private Analytics payloads."""
import argparse,json,os,sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler
from .storage import State,write_managed
from .report import collect,markdown,redact

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def ingest(report):
    url=os.environ.get('SEO_ANALYTICS_URL');token=os.environ.get('SEO_INGEST_TOKEN')
    if not url or not token:return 'not_configured'
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname!='unity-analytics.vercel.app' or p.path!='/api/seo/reports' or p.username or p.password:return 'invalid_endpoint'
    raw=json.dumps(report,ensure_ascii=False).encode()
    if len(raw)>524288:return 'payload_too_large'
    try:
        with build_opener(NoRedirect()).open(Request(url,data=raw,method='POST',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}),timeout=30) as r:
            return 'saved' if r.status in (200,201) else 'unavailable'
    except Exception:return 'unavailable'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='config.json');parser.add_argument('--state',default='.state/seo.sqlite');parser.add_argument('--ledger');sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--as-of');run.add_argument('--output',default='out');run.add_argument('--vault');run.add_argument('--redact-queries',action='store_true');run.add_argument('--require-gsc',action='store_true')
    measure=sub.add_parser('record-measure');measure.add_argument('--id',required=True);measure.add_argument('--date',required=True);measure.add_argument('--summary',required=True);measure.add_argument('--commit',required=True);measure.add_argument('--page',required=True)
    args=parser.parse_args();state=State(Path(args.state))
    try:
        if args.ledger:state.import_ledger(Path(args.ledger))
        if args.command=='record-measure':
            from datetime import date
            date.fromisoformat(args.date);state.record_measure(args.id,args.date,{'summary':args.summary,'commit':args.commit,'page':args.page});print('measure_recorded');return 0
        config=json.loads(Path(args.config).read_text());report=collect(config,state,args.as_of)
        analytics=ingest(report);report['analyticsStatus']=analytics
        public=redact(report) if args.redact_queries else report
        out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
        name=report['id'];path=out/(name+'.json')
        raw=json.dumps(public,ensure_ascii=False,indent=2)+'\n'
        if path.exists() and path.read_text()!=raw:raise FileExistsError('immutable_report_conflict')
        path.write_text(raw)
        write_managed(out,name+'.md',markdown(public))
        if args.vault:write_managed(Path(args.vault),'Unity/SEO/Weekly/'+name+'.md',markdown(public))
        print(json.dumps({'id':name,'gscStatus':report['gscStatus'],'analyticsStatus':analytics,'output':str(out),'queriesRedacted':args.redact_queries}))
        return 2 if args.require_gsc and report['gscStatus']!='available' else 0
    except (ValueError,FileExistsError) as e:
        print('report_failed:'+str(e).split(':')[0],file=sys.stderr);return 1
    finally:
        if args.ledger:state.export_ledger(Path(args.ledger))
        state.close()
if __name__=='__main__':raise SystemExit(main())
