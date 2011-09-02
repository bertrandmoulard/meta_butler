import ConfigParser, json, memcache, urllib2, datetime
import lxml.html

class MetaButler:
  def __init__(self):
    self.config = ConfigParser.ConfigParser()
    self.config.readfp(open("config.txt"))
    self.servers = self.parse_servers_config(self.config.get("meta_butler", "servers"))
    connection_string = self.config.get("meta_butler", "memcache_host") + ":"
    connection_string += self.config.get("meta_butler", "memcache_port")
    self.mc = memcache.Client([connection_string], debug=0)
    self.data = {"jobs": {}, "errors": []}
    

  def parse_servers_config(self, servers_csv):
    return [server.strip() for server in servers_csv.split(',')]
    
  def collect_claims_from_html(self, server, html_string):
    html = lxml.html.fromstring(html_string)
    rows = html.cssselect("#projectStatus tr")
    for row in rows:
      claimer = self.get_claimer_from_row(row)
      job_name = self.get_job_name_from_row(row)
      
      if claimer is not None and job_name is not None:
        if self.data["jobs"][server + "jobs/" + job_name] is not None:
          self.data["jobs"][server + "jobs/" + job_name]['claim'] = claimer
        
  
  def get_job_name_from_row(self, row):
    links = row.cssselect("td a")  
    for link in links:
      if not link.text_content().startswith("#") and link.text_content().strip() != "":
        return link.text_content().strip()
    return None
  
  def get_claimer_from_row(self, row):
    tds = row.cssselect("td")
    for td in tds:
      if td.text_content().startswith("claimed by"):
        return td.text_content().replace("claimed by", "").strip()
    return None
      
  def collect_jobs_from_json(self, server, json_string):
    o = json.loads(json_string)
    for job in o['jobs']:
      id = server + "jobs/" + job['name']
      job_hash = {"name" : job['name'], "server" : server, "color" : job['color']}
      self.data["jobs"][id] = job_hash
  
  def save_data(self):
    self.mc.set("meta_butler_data", self.data)
    
  def add_refresh_time_to_data(self):
    self.data['refresh'] = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")
          
  def do_your_job(self):
    for server in self.servers:
      jobs_content = self.download_server_info(server)
      if jobs_content is not None:
        try:
          self.collect_jobs_from_json(server, jobs_content)
        except Exception, (error):
          self.print_with_time("error collecting jobs from this content: ")
          print jobs_content
      
      claims_content = self.download_claim_info(server)
      if claims_content is not None:
        try:
          self.collect_claims_from_html(server, claims_content)
        except Exception, (error):
          self.print_with_time("error collecting claims from this content: ")
          print claims_content
      
    self.add_refresh_time_to_data()
    self.save_data()
    
  def download_server_info(self, server):
    try:
      return urllib2.urlopen(server + "api/json", timeout=2).read()
    except Exception, (error):
      error = "error downloading jobs info from: " + server
      self.data['errors'].append(error)
      self.print_with_time(error)
      return None
  
  def download_claim_info(self, server):
    try:
      return urllib2.urlopen(server + "claims/?", timeout=2).read()
    except Exception, (error):
      error = "error downloading claims info from: " + server
      self.data['errors'].append(error)
      self.print_with_time(error)
      return None
  
  def print_with_time(self, error):
    print datetime.datetime.now().strftime("%Y/%m/%d - %H:%M:%S") + ": " + str(error)
    
if __name__ == '__main__':
  butler = MetaButler()
  butler.do_your_job()