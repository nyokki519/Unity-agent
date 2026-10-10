"""Measured weekly reports; failed API calls remain explicit missing observations."""
from datetime import date,datetime,timezone
from zoneinfo import ZoneInfo
import hashlib,json,copy
from .analysis import periods,compare_metrics,opportunities,growing_queries
from .gsc import SearchConsole,ApiError,authenticated_transport
from .audit import audit_site
LIMITATIONS=[
 'Search Analytics returns top rows and omits anonymized query text; query/page sums are not property totals.',
 'Dates use America/Los_Angeles and a three-day final-data lag. All periods are seven complete inclusive days.',
 'URL Inspection is Google’s last indexed snapshot; not a live fetch or request to index.',
 'Search Console API does not provide Google-wide rank tracking, manual-actions/security reports, Instagram Insights or field Core Web Vitals.',
 'Short-term ranking fluctuations do not trigger website copy changes. Task cooldown is 28 days; observations do not establish causality.',
 'Public HTTP checks cannot establish Google indexing. 404 origin-root robots on GitHub Project Pages means no blocking robots, not project-path enforcement.'
]

def collect(config,state,as_of=None,api_factory=None,auditor=audit_site):
    today=date.fromisoformat(as_of) if as_of else datetime.now(ZoneInfo('America/Los_Angeles')).date()
    period,previous_period=periods(today)
    report={'schemaVersion':1,'siteUrl':config['siteUrl'],'period':period,'previousPeriod':previous_period,'current':None,'previous':None,'comparison':None,'gscStatus':'unavailable','queryRows':[],'previousQueryRows':[],'pageRows':[],'growingQueries':[],'tasks':[],'indexChecks':[],'publicChecks':auditor(config['siteUrl']),'coverage':{},'errors':[],'limitations':LIMITATIONS,'measures':state.history()}
    try:
        api=api_factory() if api_factory else SearchConsole(config['siteUrl'],authenticated_transport())
        if api is None:raise ApiError('authentication_required')
        selected=next((s for s in api.sites().get('siteEntry',[]) if s.get('siteUrl')==config['siteUrl']),None)
        report['propertyAccess']=selected is not None
        try:report['sitemaps']=api.sitemaps()
        except ApiError as e:
            report['coverage']['sitemaps']={'status':'unavailable'};report['errors'].append(str(e))
        current=api.totals(period);previous=api.totals(previous_period)
        # Commit the pair together; partial weeks never look like zero or a full comparison.
        report.update(current=current,previous=previous,comparison=compare_metrics(current,previous),gscStatus='available')
        for field,p,dims in [('queryRows',period,['query']),('previousQueryRows',previous_period,['query']),('pageRows',period,['page'])]:
            try:
                data=api.performance(p,dims);report[field]=data['rows'];report['coverage'][field]={'truncated':data['truncated'],'note':data['coverage']}
            except ApiError as e:
                report['coverage'][field]={'status':'unavailable'};report['errors'].append(str(e))
        if report['coverage'].get('queryRows',{}).get('status')!='unavailable' and report['coverage'].get('previousQueryRows',{}).get('status')!='unavailable':report['growingQueries']=growing_queries(report['queryRows'],report['previousQueryRows'])
        for task in opportunities([p for p in report['pageRows'] if p.get('keys',[None])[0] in config.get('inspectionUrls',[])],report['queryRows']):
            task['newProposal']=state.propose(task,today);report['tasks'].append(task)
        for url in config.get('inspectionUrls',[])[:10]:
            try:report['indexChecks'].append(api.inspect(url))
            except (ApiError,ValueError) as e:report['indexChecks'].append({'url':url,'status':'unavailable','verdict':'unknown','error':str(e) if isinstance(e,ApiError) else 'invalid_inspection_url'})
    except ApiError as e:report['gscStatus']=str(e);report['errors'].append(str(e))
    for m in report['measures']:m['evaluation']=state.evaluate_measure(m,period,report['current'])
    for field in ('queryRows','previousQueryRows','pageRows'):
        if len(report[field])>100:
            report['coverage'].setdefault(field,{})['reportRowsLimited']=100
            report[field]=report[field][:100]
    signature=hashlib.sha256(json.dumps(report,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    report['id']=period['end']+'-'+signature[:12]
    state.observe(report)
    return report

def redact(report):
    r=copy.deepcopy(report)
    for field in ('queryRows','previousQueryRows','growingQueries'):r.pop(field,None)
    r['queriesRedacted']=True
    return r

def text(value):
    # Queries and remote titles are data, never Markdown links or instructions.
    return str(value).replace('\\','\\\\').replace('|','\\|').replace('[','\\[').replace(']','\\]').replace('<','&lt;').replace('>','&gt;').replace('\n',' ').replace('\r',' ')

def markdown(r):
    lines=['# Unity SEO 週次レポート',f"\n対象: {r['siteUrl']}",f"\n期間（Pacific、最終データ）: {r['period']['start']}〜{r['period']['end']}",f"前期間: {r['previousPeriod']['start']}〜{r['previousPeriod']['end']}",f"\nGSC接続: `{r['gscStatus']}`",'\n## 検索パフォーマンス']
    if r['current'] is None:lines.append('未取得。認証・API権限・接続を確認してください。未取得を0件とは扱いません。')
    else:
        lines.extend(['| 指標 | 今期 | 前期 |','|---|---:|---:|'])
        for key,label in [('clicks','クリック'),('impressions','表示回数'),('ctr','CTR'),('position','平均掲載順位')]:
            a,b=r['current'][key],r['previous'][key]
            lines.append(f"| {label} | {a:.3f} | {b:.3f} |")
        lines.append('CTRは0〜1の比率。順位は低い数値ほど上位です。集計値はクエリ一覧の合算ではありません。')
        lines.append('\n比較: '+text(json.dumps(r['comparison'],ensure_ascii=False)))
    lines.append('\n## 伸びた検索キーワード')
    if r.get('queriesRedacted'):lines.append('公開用成果物では検索語を伏せています。詳細は認証付きAnalyticsまたはローカル出力をご確認ください。')
    for x in r.get('growingQueries',[]):lines.append(f"- {text(x['query'])}: クリック差 {x['clicksDelta']}、平均順位改善 {x['positionImprovement']:.2f}")
    if not r.get('growingQueries') and not r.get('queriesRedacted'):lines.append('比較可能な十分な表示回数のデータなし。伸びていないとは断定しません。')
    lines.append('\n## 改善候補（自動公開しない）')
    for t in r['tasks']:lines.append(f"- {text(t['title'])}: {text(t['target'])}（{'新規' if t['newProposal'] else '28日以内の継続観察'}）")
    if not r['tasks']:lines.append('数値に基づく新規候補なし。認証待ちや少ない母数では施策を捏造しません。')
    lines.append('\n## インデックス監視')
    for c in r['indexChecks']:lines.append(f"- {text(c['url'])}: {text(c.get('verdict','unknown'))} / {text(c.get('coverageState') or c['status'])}")
    if not r['indexChecks']:lines.append('未取得。HTTP 200だけでインデックス済みとは判定しません。')
    lines.append('\n## 公開サイトの技術チェック')
    for c in r['publicChecks']:lines.append(f"- {text(c['url'])}: {c['status']} / HTTP {c.get('httpStatus')} / {text(', '.join(c['issues']) or '指摘なし')}")
    lines.append('\n## 施策履歴と効果観察')
    for m in r.get('measures',[]):
        evaluation=m.get('evaluation',{})
        lines.append(f"- {text(m['applied'])}: {text(m.get('summary',m['id']))}。観察状況: {text(evaluation.get('status','unknown'))}。期間比較は因果効果の証明ではありません。")
        if evaluation.get('comparison'):lines.append('  比較: '+text(json.dumps(evaluation,ensure_ascii=False)))
    if not r.get('measures'):lines.append('記録された施策なし。`record-measure`で適用日・commit・変更内容・対象ページを保存できます。')
    lines.append('\n## データの制約')
    lines.extend('- '+text(x) for x in r['limitations'])
    return '\n'.join(lines)+'\n'
