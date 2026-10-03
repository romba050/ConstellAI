"""Fetch bibliography for the current PMID slice into a review file, never the graph."""
import argparse
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

EDITION = Path(__file__).resolve().parents[1]

def text(node, path):
    found = node.find(path)
    return ''.join(found.itertext()).strip() if found is not None else None

def refresh(output):
    output = Path(output)
    if output.exists():
        raise ValueError('Review output already exists; it will not be overwritten.')
    data = json.loads((EDITION / 'data/pilot_evidence.json').read_text(encoding='utf-8'))
    pmids = sorted({s['pmid'] for s in data['sources'] if s.get('pmid')})
    if not pmids or len(pmids) > 100 or not all(p.isdigit() for p in pmids):
        raise ValueError('Expected a focused slice of 1–100 valid PMIDs.')
    address = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?' + urllib.parse.urlencode(
        {'db': 'pubmed', 'id': ','.join(pmids), 'retmode': 'xml', 'tool': 'MEDR5Atlas'})
    request = urllib.request.Request(address, headers={'User-Agent': 'MEDR5Atlas-public-metadata/1.0'})
    with urllib.request.urlopen(request, timeout=40) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('Focused metadata response exceeded the size limit.')
    records = []
    for entry in ET.fromstring(raw).findall('PubmedArticle'):
        article = entry.find('MedlineCitation/Article')
        identifiers = {x.get('IdType'): x.text for x in entry.findall('PubmedData/ArticleIdList/ArticleId')}
        pmid = text(entry, 'MedlineCitation/PMID')
        if pmid not in pmids:
            raise ValueError('Unexpected PMID in public response.')
        authors = [text(a, 'CollectiveName') or ' '.join(filter(None,[text(a,'ForeName'),text(a,'LastName')]))
                   for a in article.findall('AuthorList/Author')]
        records.append(dict(pmid=pmid,title=text(article,'ArticleTitle'),doi=identifiers.get('doi'),pmcid=identifiers.get('pmc'),
            journal=text(article,'Journal/Title'),publication_year=text(article,'Journal/JournalIssue/PubDate/Year'),authors=authors,
            publication_types=[x.text for x in article.findall('PublicationTypeList/PublicationType')],
            source_url='https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/',
            corrections=[dict(type=c.get('RefType'),pmid=text(c,'PMID')) for c in entry.findall('MedlineCitation/CommentsCorrectionsList/CommentsCorrections')]))
    if {x['pmid'] for x in records} != set(pmids):
        raise ValueError('Public response did not contain the complete requested PMID slice.')
    result = dict(retrieved_at=datetime.now(timezone.utc).isoformat(),metadata_source_url=address,records=records,
        boundary='Bibliography-only review proposal. No abstract/full-text republication, journal filter, numerical score, automatic claim/graph update or Ovid access.')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return len(records)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    try:
        count = refresh(args.output)
    except (ValueError,OSError,ET.ParseError) as error:
        parser.error(str(error))
    print(f'{count} public bibliography records saved for review; graph and scores unchanged.')
