"""Privacy-preserving local ledger and conflict-safe Obsidian Markdown output."""
import sqlite3,json,hashlib
from pathlib import Path
from datetime import date
class State:
    def __init__(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);self.db=sqlite3.connect(path)
        self.db.executescript('CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, proposed TEXT NOT NULL, body TEXT NOT NULL);CREATE TABLE IF NOT EXISTS measures(id TEXT PRIMARY KEY, applied TEXT NOT NULL, body TEXT NOT NULL);CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, body TEXT NOT NULL);')
    def propose(self,task,as_of):
        old=self.db.execute('SELECT proposed FROM tasks WHERE id=?',(task['id'],)).fetchone()
        if old and (as_of-date.fromisoformat(old[0])).days<28:return False
        # Tasks are page-oriented; never cache raw Search Console query strings.
        with self.db:self.db.execute('INSERT OR REPLACE INTO tasks VALUES(?,?,?)',(task['id'],as_of.isoformat(),json.dumps(task,ensure_ascii=False)))
        return True
    def observe(self,report):
        body={'id':report['id'],'period':report['period'],'current':report['current'],'previous':report['previous'],'gscStatus':report['gscStatus']}
        with self.db:self.db.execute('INSERT OR IGNORE INTO observations VALUES(?,?)',(report['id'],json.dumps(body)))
    def record_measure(self,measure_id,applied,body):
        with self.db:self.db.execute('INSERT OR IGNORE INTO measures VALUES(?,?,?)',(measure_id,applied,json.dumps(body)))
    def history(self):return [{'id':i,'applied':d,**json.loads(b)} for i,d,b in self.db.execute('SELECT id,applied,body FROM measures ORDER BY applied')]
    def export_ledger(self,path):
        data={table:[list(row) for row in self.db.execute('SELECT * FROM '+table+' ORDER BY id')] for table in ('tasks','measures','observations')}
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    def import_ledger(self,path):
        path=Path(path)
        if not path.exists():return
        if path.stat().st_size>5_000_000:raise ValueError('ledger_too_large')
        data=json.loads(path.read_text())
        with self.db:
            for table,count in (('tasks',3),('measures',3),('observations',2)):
                for row in data.get(table,[]):
                    if not isinstance(row,list) or len(row)!=count or any(not isinstance(v,str) for v in row):raise ValueError('invalid_ledger')
                    self.db.execute('INSERT OR IGNORE INTO '+table+' VALUES('+','.join('?' for _ in row)+')',row)
    def evaluate_measure(self,measure,period,current):
        if measure.get('stage','applied')!='applied':return {'status':'not_applied'}
        applied=date.fromisoformat(measure['applied'])
        if (date.fromisoformat(period['start'])-applied).days<28:return {'status':'observation_window'}
        rows=[json.loads(x[0]) for x in self.db.execute('SELECT body FROM observations')]
        before=[r for r in rows if r['period']['end']<measure['applied'] and r['gscStatus']=='available' and r['current'] is not None]
        if not before or current is None:return {'status':'baseline_missing'}
        from .analysis import compare_metrics
        baseline=max(before,key=lambda r:r['period']['end'])
        return {'status':'observed_not_causal','beforePeriod':baseline['period'],'afterPeriod':period,'comparison':compare_metrics(current,baseline['current'])}
    def close(self):self.db.close()

def write_managed(root,relative,body):
    root=Path(root).resolve();path=(root/relative).resolve()
    if root not in path.parents or path.suffix!='.md' or any(p.is_symlink() for p in (Path(root/relative),*Path(root/relative).parents) if p!=root):raise ValueError('unsafe_output_path')
    digest=hashlib.sha256(body.encode()).hexdigest();marker='<!-- unity-seo-managed sha256='+digest+' -->\n'
    if path.exists():
        previous=path.read_text();first,sep,rest=previous.partition('\n')
        if not first.startswith('<!-- unity-seo-managed sha256=') or first!='<!-- unity-seo-managed sha256='+hashlib.sha256(rest.encode()).hexdigest()+' -->':raise FileExistsError('managed_report_edited')
        if previous==marker+body:return path
        raise FileExistsError('immutable_report_conflict')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:f.write(marker+body)
    return path
