import ConfigParser, json, memcache, urllib2, datetime
import lxml.html
import jsonpickle
import re

class Job:
  def __init__(self, job_json, jobs_data, init_with_json=True):
    if init_with_json:
      self.init_job(job_json, jobs_data)
    else: 
      self.init_bamboo_job(job_json)

  def init_bamboo_job(self, job_json):
    self.url = job_json["link"]["href"]  
    self.color = "blue"
    self.name = job_json["name"]

  def init_job(self, job_json, jobs_data):    
    self.url = job_json
    try:
      job_data = jobs_data["jobs"][job_json]
      self.color = job_data["color"]
      self.name = job_data["name"]
      if "claim" in job_data:
        self.claim = job_data["claim"]
    except:
      self.color = "transparent"
      self.name = job_json.split("/")[-1]

class Stage:
  def __init__(self, stage_json, jobs_data, init_with_json=True):
    self.name = stage_json['name']
    self.jobs = []
    self.color = "blue"
    if init_with_json:
      self.init_stage(stage_json, jobs_data)
    else:
      self.init_bamboo_stage(stage_json)

  def init_bamboo_stage(self, stage_json):
    self.blocks_commits = True    
    for job_json in stage_json['plans']['plan']:
      job = Job(job_json, [], False)
      if job.color.find("red") > -1:
        self.color = "red"
      elif self.color is not "red" and job.color.find("anime")  > -1:
        self.color = "blue_anime"
      self.jobs.append(job)

  def init_stage(self, stage_json, jobs_data):
    self.blocks_commits = stage_json['blocks_commits']
    for job_json in stage_json['jobs']:
      job = Job(job_json, jobs_data)
      if job.color.find("red") > -1:
        self.color = "red"
      elif self.color is not "red" and job.color.find("anime")  > -1:
        self.color = "blue_anime"
      self.jobs.append(job)


class Pipeline:
  def __init__(self, pipeline_json, jobs_data, init_with_json=True):
    self.stages = []
    self.can_commit = True
    self.name = pipeline_json['name']
    if init_with_json:
      self.init_pipeline(pipeline_json, jobs_data)
    else: 
      self.init_bamboo_pipeline(pipeline_json)

  def init_bamboo_pipeline(self, pipeline_json):
    for stage_json in pipeline_json['stages']['stage']:
      stage = Stage(stage_json, [], False)
      self.stages.append(stage)
      if stage.blocks_commits and stage.color is "red":
        self.can_commit = False
    self.refresh_time = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")


  def init_pipeline(self,pipeline_json,jobs_data):
    for stage_json in pipeline_json['stages']:
      stage = Stage(stage_json, jobs_data)
      self.stages.append(stage)
      if stage.blocks_commits and stage.color is "red":
        self.can_commit = False
    self.refresh_time = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")


class Bamboo:
  ALL_PLANS_PATH = "/rest/api/latest/plan.json?expand=plans.plan.stages.stage.plans"

  def __init__(self, servers):
    self.servers = servers

  def process(self):
    print "process"
    for server in self.servers:
      jobs_content = self.download_server_info(server)
      if jobs_content is not None:
        try:
          self.parse_json(jobs_content)
        except Exception, (error):
          print error
          self.print_with_time("error collecting jobs from this content: ")
          print jobs_content

  def parse_json(self, json_string):
    o = json.loads(json_string)
    for plan in o['plans']['plan']:
      pipeline = Pipeline(plan,[],False)
      print pipeline
      # id = server + "job/" + job['name']
      # job_hash = {"name" : plan['name'], "server" : server, "color" : job['color']}
      # self.data["jobs"][id] = job_hash



  def download_server_info(self, server):
    try:
      return urllib2.urlopen(server + self.ALL_PLANS_PATH, timeout=2).read()
    except Exception, (error):
      error_message = "error downloading jobs info from: " + server
      #self.data['errors'].append(error)
      print(error)
      return None          


class MetaButler:
  def __init__(self, path_to_config = "config.js"):
    self.pipelines = []
    self.read_config(path_to_config)
    self.data = {"jobs": {}, "errors": []}

  def read_config(self, path_to_config):
    f = open(path_to_config)
    j = json.load(f)
    self.servers = j['meta_butler']['servers'] 
    connection_string = j["meta_butler"]["memcache_host"] + ":"
    connection_string += j["meta_butler"]["memcache_port"]
    self.mc = memcache.Client([connection_string], debug=0)
    self.pipeline_config = j['pipelines']
    
  def populate_pipelines(self, pipeline_configs, jobs_data):
    for pipeline_json in pipeline_configs:
      pipeline = Pipeline(pipeline_json, jobs_data)
      self.pipelines.append(pipeline)

  def collect_claims_from_html(self, server, html_string):
    html = lxml.html.fromstring(html_string)
    rows = html.cssselect("#projectStatus tr")
    for row in rows:
      claimer = self.get_claimer_from_row(row)
      job_name = self.get_job_name_from_row(row)
      
      if claimer is not None and job_name is not None:
        if self.data["jobs"][server + "job/" + job_name] is not None:
          self.data["jobs"][server + "job/" + job_name]['claim'] = claimer
        
  
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
        claimer_text = td.text_content().replace("claimed by", "").strip()
        return re.sub("\s*because:.*", "", claimer_text)
    return None
      
  def collect_jobs_from_json(self, server, json_string):
    o = json.loads(json_string)
    for job in o['jobs']:
      id = server + "job/" + job['name']
      job_hash = {"name" : job['name'], "server" : server, "color" : job['color']}
      self.data["jobs"][id] = job_hash
  
  def save_data(self):
    self.mc.set("all_jobs", self.data)
    self.mc.set("pipelines", json.loads(jsonpickle.encode(self.pipelines, unpicklable=False)))
    
  def add_refresh_time_to_data(self):
    self.data['refresh'] = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")
          
  def do_your_job(self):
    if self.servers is not None:
      process_jenkins_servers()
    if self.bamboo_servers is not None:
      Bamboo(self.bamboo_servers).process()

    self.add_refresh_time_to_data()
    self.populate_pipelines(self.pipeline_config, self.data)
    self.save_data()

  def process_jenkins_servers(self):
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

  def process_bamboo_servers(self):
    print "noop"

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
