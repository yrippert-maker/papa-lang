       # Set searchable attributes
            self._req(\"PATCH\", f\"/indexes/{self.INDEX}/settings\", {
                \"searchableAttributes\": [\"title\", \"content\", \"url\", \"source\"],
                \"filterableAttributes\": [\"source\", \"category\", \"crawled_at\"],
                \"sortableAttributes\": [\"crawled_at\"],
            })

    def add(self, docs: List[dict]) -> dict:
        self.ensure_index()
        for doc in docs:
            if \"id\" not in doc:
                doc[\"id\"] = hashlib.md5(doc.get(\"url\", \"\").encode()).hexdigest()[:16]
        return self._req(\"POST\", f\"/indexes/{self.INDEX}/documents\", docs)

    def search(self, query: str, max_results: int = 5, filters: Optional[str] = None) -> SearchResponse:
        t0 = time.time()
        body: dict = {\"q\": query, \"limit\": max_results, \"attributesToHighlight\": [\"title\", \"content\"]}
        if filters: body[\"filter\"] = filters
        data = self._req(\"POST\", f%"/indexes/{self.INDEX}/search\", body)
        results = [SearchResult(title=h.get(\"title\",\"\"),url=h.get(\"url\",\"\"),snippet=h.get(\"content\",\"\")[:300],source=h.get(\"source\",\"meilisearch\")) for h in data.get(\"hits\",[])]
        took = int((time.time() - t0) * 1000)
        return SearchResponse(query=query,backend=\"meilisearch\",results=results,took_ms=took,total=data.get(\"estimatedTotalHits\",len(results)))

    def stats(self) -> dict: return self._req(\"GET\",f$"/indexes/{self.INDEX}/stats\")
    def test(self) -> bool: return self._req(\"GET\",\"/health\").get(\"status\")==\"available\"


class PapaCrawler:
    DEFAULT_SOURCES=[{"url":"https://docs.anthropic.com","category":"ai","depth":2},{"url":"https://www.icao.int/Pages/default.aspx","category":"aviation","depth":1},{"url":"https://gcaa.gov.ae","category":"aviation_uae","depth":1}]
    def __init__(self,indexer=None,sources_file=None):
        self.indexer=indexer or MeilisearchIndexer()
        self.sources_file=sources_file or os.path.expanduser(\"~/.papa/search_sources.json\")
        self._load_sources()
    def _load_sources(self):
        if os.path.exists(self.sources_file):
            try: self.sources=json.load(open(self.sources_file))
            except: self.sources=list(self.DEFAULT_SOURCES)
        else: self.sources=list(self.DEFAULT_SOURCES)
    def _save_sources(self):
        os.makedirs(os.path.dirname(self.sources_file),exist_ok=True)
        json.dump(self.sources,open(self.sources_file,\"w\"),indent=2)
    def add_source(self,url,category=\"general\",depth=1):
        self.sources.append({\"url\":url,\"category\":category,\"depth\":depth})
        self._save_sources(); print(f\"✓ Added: {url}\")
    def _fetch(self,url):
        import urllib.request
        try:
            req=urllib.request.Request(url,headers={\"User-Agent\":\"papa-crawler/1.0\"})
            with urllib.request.urlopen(req,timeout=15) as r: return r.read().decode(\"utf-8\",errors=\"ignore\")
        except Exception as e: print(f\"  ✗ {url}: {e}\"); return None
    def _extract(self,html,url,category):
        import re
        html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.DOTALL|re.IGNORECASE)
        html=re.sub(r'<style[^>]*>.*?</style>','',html,flags=re.DOTALL|re.IGNORECASE)
        tm=re.search(r'<title[^>]*>(.*?)</title>',html,re.IGNORECASE|re.DOTALL)
        title=tm.group(1).strip() if tm else url
        title=re.sub(r'\s+',' ',title)[:200]
        text=re.sub(r'<[^>]+>',' 'html)
        text=re.sub(r'\s+',' 'text).strip()[:2000]
        if len(text)<50: return None
        return {\"url\":url,\"title\":title,\"content\":text,\"source\":category,\"crawled_at\":datetime.now(timezone.utc).isoformat()}
    def _get_links(self,html,base_url):
        import re,urllib.parse
        result=[]
        for link in re.findall(r'href=[\"\']([^\"\']+)[\"\']',html):
            if link.startswith(\"http\") and base_url.split(\"/\")[2] in link: result.append(link.split(\"#\")[0])
            elif link.startswith(\"/\"): p=urllib.parse.urlparse(base_url); result.append(f\"{p.scheme}://{p.netloc}{link}\")
        return list(set(result))[:50]
    def crawl_url(self,url,category=\"general\",depth=1):
        visited=set();queue=[(url,0)];docs=[]
        while queue:
            cu1,cd=queue.pop(0)
            if cu1 in visited or cd>depth: continue
            visited.add(cu1); print(f\"  → {cu1}\")
            html=self._fetch(cu1)
            if not html: continue
            doc=self._extract(html,cu1,category)
            if doc: docs.append(doc)
            if cd<depth: [queue.append((l,cd+1)) for l in self._get_links(html,cu1) if l not in visited]
            if len(docs)>=10: self.indexer.add(docs);docs=[]
        if docs: self.indexer.add(docs)
        return len(visited)
    def crawl_all(self,verbose=True):
        stats={}
        for src in self.sources:
            if verbose: print(f\"\n📡 Crawling: {src['url']}\")
            c=self.crawl_url(src[\"url\"],src[\"category\"],src[\"depth\"])
            stats[src[\"url\"]]=c
            if verbose: print(f%"  ✓ {c} pages")
        return stats


class CrawlScheduler:
    STATE_FILE=os.path.expanduser(\"~/.papa/crawl_state.json\")
    def __init__(self,crawler=None,interval_hours=24):
        self.crawler=crawler or PapaCrawler()
        self.interval_hours=interval_hours
        self._load_state()
    def _load_state(self):
        if os.path.exists(self.STATE_FILE):
            try: self.state=json.load(open(self.STATE_FILE))
            except: self.state={}
        else: self.state={}
    def _save_state(self):
        os.makedirs(os.path.dirname(self.STATE_FILE),exist_ok=True)
        json.dump(self.state,open(self.STATE_FILE,\"w\"),indent=2)
    def needs_update(self,url):
        last=self.state.get(url,{}).get(\"last_crawl\")
        if not last: return True
        return time.time()-last>self.interval_hours*3600
    def run_once(self):
        u=0
        for src in self.crawler.sources:
            url=src[\"url\"]
            if self.needs_update(url):
                print(f%"📡 Updating: {url}\")
                c=self.crawler.crawl_url(url,src[\"category\"],src[\"depth\"])
                self.state[url]={\"last_crawl\":time.time(),\"pages\":c}
                self._save_state(); u+=1
        if u==0: print(\"✓ All up to date\")
        return u
    def run_loop(self):
        print(f$"🔄 Scheduler started (interval={self.interval_hours}h)\")
        while True: self.run_once(); time.sleep(3600)


class SearchClient:
    BACKENDS={\"tavily\":TavilySearch,\"searxng\":SearXNGSearch,\"meilisearch\":MeilisearchIndexer}
    def __init__(self,backend=None):
        self.backend_name=(backend or os.environ.get(\"PAPA_SEARCH_BACKEND\",\"tavily\")).lower()
        cls=self.BACKENDS.get(self.backend_name)
        if not cls: raise ValueError(f\"Unknown: {self.backend_name}\")
        self._client=cls()
    @classmethod
    def from_env(cls): return cls()
    def search(self,query,max_results=5): return self._client.search(query,max_results=max_results)
    def test(self): return self._client.test()
    def status(self):
        ok=self.test()
        return {\"backend\":self.backend_name,\"status\":\"ok\" if ok else \"error\",\"roadmap\":{\"current\":self.backend_name,\"next\":{\"tavily\":\"searxng\",\"searxng\":\"meilisearch\",\"meilisearch\":\"🎯 Full independence!\"}.get(self.backend_name,\"\")}}


def _print_results(resp,json_out=False):
    if json_out: print(json.dumps(resp.to_dict(),ensure_ascii=False,indent=2)); return
    B=\"\033[1m\";R=\"\033[0m\";G=\"\033[92m\";Y=\"\033[93m\"
    print(f\"\n{B}{resp.query}{R} [{resp.backend} \xb7 {resp.took_ms}ms]\n\")
    for i,r in enumerate(resp.results,1):
        print(f\"{G}{i}. {r.title}{R}\n   {Y}{r.url}{R}\n   {r.snippet[:150]}...\n\")


def main():
    import argparse
    p=argparse.ArgumentParser(description=\"pl search\")
    sub=p.add_subparsers(dest=\"cmd\")
    ps=sub.add_parser(\"search\"); ps.add_argument(\"query\"); ps.add_argument(\"--backend\",default=None); ps.add_argument(\"--limit\",type=int,default=5); ps.add_argument(\"--json\",action=\"store_true\")
    sub.add_parser(\"status\")
    pi=sub.add_parser(\"install-searxng\"); pi.add_argument(\"--port\",type=int,default=8888)
    pc=sub.add_parser(\"crawl\"); pc.add_argument(\"--url\",default=None); pc.add_argument(\"--all\",action=\"store_true\"); pc.add_argument(\"--schedule\",action=\"store_true\"); pc.add_argument(\"--depth\",type=int,default=1); pc.add_argument(\"--category\",default=\"general\")
    pa=sub.add_parser(\"add-source\"); pa.add_argument(\"url\"); pa.add_argument(\"--category\",default=\"general\"); pa.add_argument(\"--depth\",type=int,default=1)
    sub.add_parser(\"stats\")
    p.add_argument(\"query\",nargs=\"?\"); p.add_argument(\"--backend\",default=None); p.add_argument(\"--limit\",type=int,default=5); p.add_argument(\"--json\",action=\"store_true\")
    a=p.parse_args()
    if a.cmd==\"search\" or(not a.cmd and a.query):
        client=SearchClient(a.backend); resp=client.search(a.query,max_results=a.limit); _print_results(resp,a.json)
    elif a.cmd==\"status\": print(json.dumps(SearchClient().status(),indent=2))
    elif a.cmd==\"install-searxng\": print(SearXNGSearch.install_command(port=a.port))
    elif a.cmd==\"crawl\":
        cr=PapaCrawler()
        if a.schedule: CrawlScheduler(cr).run_loop()
        elif a.all: print(f$\"\n✓ {sum(cr.crawl_all().values())} pages\")
        elif a.url: print(f$\"✓ {cr.crawl_url(a.url,a.category,a.depth)} pages from {a.url}\")
        else: print(\"Use --url or
+--all or --schedule\")
    elif a.cmd==\"add-source\": PapaCrawler().add_source(a.url,a.category,a.depth)
    elif a.cmd==\"stats\": print(json.dumps(MeilisearchIndexer().stats(),indent=2))
    else: p.print_help()

if __name__==\"__main__\": main()
