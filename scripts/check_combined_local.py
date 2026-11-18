"""Real loopback C HTTP + real tax engine + temporary case SQLite; no model substitute claims."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def checks_pass(checks):
    """A report with unresolved domain citations cannot satisfy integration acceptance."""
    return (checks.get('report_frozen') is True
            and checks.get('fsie_locators') == 21
            and checks.get('missing_domain_citations') == 0
            and checks.get('reload') is True)


def main():
    from scripts.combined_runtime import knowledge_server
    from packages.chat.service import ChatService
    from packages.chat.store import ChatStore
    from packages.agent.providers import CKnowledgeProvider, RoutedKnowledgeProvider, LegacyKnowledgeProvider
    from packages.agent.review import report_hash
    results = {'database': 'isolated_sqlite', 'model': 'not_called', 'knowledge_transport': 'real_loopback_http', 'checks': {}}
    with knowledge_server() as (url, token):
        with TemporaryDirectory(prefix='combined-http-') as directory:
            store = ChatStore('sqlite:///' + str(Path(directory) / 'case.sqlite'))
            try:
                # Synthetic ruling reader validates explicit source routing only;
                # it does not establish availability of the cloud ruling corpus.
                provider = RoutedKnowledgeProvider(CKnowledgeProvider(url, token),
                                                    LegacyKnowledgeProvider(lambda _: {'status': 'no_matching_units', 'passages': []}))
                service = ChatService(store, provider=provider); owner = 'user:http-smoke'
                doc = store.create(owner)
                doc = service.edit(owner, doc['id'], 0, str(uuid4()), {'dividend_amount': 1000000,
                    'dividend_currency': 'CNY', 'payer_jurisdiction': 'CN', 'income_type': 'dividend',
                    'receipt_date': '2026-10-11'})
                case = json.loads((ROOT / 'tests/integration/fixtures/holding.synthetic.json').read_text())
                bindings = {'dividend_amount': 'event.dividend', 'dividend_currency': 'case.currency',
                            'payer_jurisdiction': 'OP.loc', 'receipt_date': 'event.on'}
                doc = service.domain_setup(owner, doc['id'], doc['revision'], str(uuid4()), case, True, 'assess_current', bindings)
                doc = service.domain_plan(owner, doc['id'], doc['revision'], str(uuid4()))
                doc = service.domain_confirm(owner, doc['id'], doc['revision'], str(uuid4()))
                doc = service.domain_report(owner, doc['id'], doc['revision'], str(uuid4()), True)
                report = doc['analyses'][-1]
                results['checks']['report_frozen'] = report_hash(report) == report['report_hash']
                results['checks']['fsie_locators'] = len({p['locator'] for p in report['fsie_assessment']['passages']})
                results['checks']['evidence_reads'] = report['budget'].get('evidence', 0)
                results['checks']['current_entities'] = [e[0] for e in report['outcome']['structure']['entities']]
                results['checks']['missing_domain_citations'] = len(report['missing_locators'])
                results['checks']['missing_domain_locators'] = report['missing_locators']
                results['checks']['reload'] = store.get(owner, doc['id'])['revision'] == doc['revision']
                results['status'] = 'passed' if checks_pass(results['checks']) else 'failed'
            finally: store.engine.dispose()
    print(json.dumps(results, ensure_ascii=False))
    return 0 if results['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
