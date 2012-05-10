import ConfigParser, json, memcache, urllib2, datetime, urlparse
import lxml.html
import jsonpickle
import re

class Job:
  def __init__(self, name, url):
    self.name = name
    self.url = url

  @classmethod
  def create_from_jenkins_json(cls, job_url, jobs_data):
    job = None
    
    if job_url in jobs_data["jobs"]:
      job_data = jobs_data["jobs"][job_url]
      name = job_data["name"]
      job = Job(name, job_url)
      job.color = job_data["color"]
      if "claim" in job_data:
        job.claim = job_data["claim"]
    else:
      job = Job(job_url.split("/")[-1], job_url)
      job.color = "transparent"
      Log.print_with_time("Job with url [" + job_url + "] was not found in the downloaded jobs.")     
    return job

class Stage:
  def __init__(self):
    self.name = ""
    self.jobs = []
    self.color = "blue"

  @classmethod
  def create_from_jenkins_json(cls, stage_json, jobs_data):
    stage = Stage()
    stage.name = stage_json['name']
    stage.init_stage(stage_json, jobs_data)
    return stage

  def init_stage(self, stage_json, jobs_data):
    self.blocks_commits = stage_json['blocks_commits']
    for job_json in stage_json['jobs']:
      job = Job.create_from_jenkins_json(job_json, jobs_data)
      if job.color.find("red") > -1:
        self.color = "red"
      elif self.color is not "red" and job.color.find("anime")  > -1:
        self.color = "blue_anime"
      self.jobs.append(job)


class Pipeline:
  def __init__(self):
    self.stages = []
    self.can_commit = True
    self.name = ''
  
  @classmethod
  def create_from_jenkins_json(cls, pipeline_json, jobs_data):
    pipeline = cls()
    pipeline.name = pipeline_json['name']
    pipeline.init_pipeline(pipeline_json, jobs_data)
    return pipeline

  def init_pipeline(self,pipeline_json,jobs_data):
    for stage_json in pipeline_json['stages']:
      stage = Stage.create_from_jenkins_json(stage_json, jobs_data)
      self.stages.append(stage)
      if stage.blocks_commits and stage.color is "red":
        self.can_commit = False
    self.refresh_time = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")

class HttpHelper:
  @classmethod
  def download_html_with_retry(cls, url, retry_count):
    retval = None
    for i  in range(0, retry_count):
      try:
        retval = urllib2.urlopen(url, timeout=3).read()
        if i != 0:
          Log.print_with_time("Warning: Retrieving url[" + url + "] succeeded after " + str((i+1)) + " times.")
        return retval
      except Exception, (error):
        Log.print_with_time("Error while downloading from url [" + url + "]. Error: " + str(error))
    return None

class Log:
  @classmethod
  def print_with_time(cls, error):
    print datetime.datetime.now().strftime("%Y/%m/%d - %H:%M:%S") + ": " + str(error)

class Bamboo:
  ALL_PLANS_PATH = "/rest/api/latest/plan.json?expand=plans.plan.stages.stage.plans.plan"
  ALL_RESULTS_PATH = "/rest/api/latest/result.json?expand=results.result.stages.stage.results.result"

  def __init__(self, servers):
    self.servers = servers
    self.pipelines = []
    self.pipelines_result = []

  def process(self):
    for server in self.servers:
      try:
        plans_json = self.download_contents(server, self.ALL_PLANS_PATH)
        results_json = self.download_contents(server, self.ALL_RESULTS_PATH)
        pipelines = self.generate_pipelines_from_json(plans_json, results_json)
        self.pipelines = self.pipelines + pipelines
      except Exception, (error):
        Log.print_with_time("Bamboo build data could not be retrieved for server [" + server + "] because of error [" + str(error) + "]")
    return self.pipelines

  def download_contents(self, server, path):
    content = None
    try:
      content = self.download_server_info(server, path)
    except Exception, (error):
      Log.print_with_time("error while retrieving data from" + server + "/" + path + ":" + str(error))
      raise

    all_contents = None
    if content is not None:
      try:
        all_contents = json.loads(content)
      except Exception, (error):
        Log.print_with_time("error while processing the data from" + server + "/" + path + ":" + str(error) + ". Data:")
        Log.print_with_time(contents)
    return all_contents

  def dump_json(self, json_to_dump):
    print json.dumps(json_to_dump, indent=2)

  def find_plan_result_by_plan_key(self, plan_key, results_json):
    for result in results_json:
      if result["key"].startswith(plan_key):
        return result

  def find_stage_result_by_name(self, stage_name, results_json):
    for result in results_json:
      if result["name"] == stage_name:
        return result

  def find_job_result_by_key(self, job_key, results_json):
    for result in results_json:
      if result["key"].startswith(job_key):
        return result

  def generate_pipelines_from_json(self, pipelines_json, results_json):
    pipelines = []
    if pipelines_json is not None and pipelines_json.has_key('plans'):
      for plan_json in pipelines_json['plans']['plan']:
        plan_result_json = self.find_plan_result_by_plan_key(plan_json["key"], results_json['results']['result'])
        pipeline = self.generate_pipeline_from_json(plan_json, plan_result_json)
        pipelines.append(pipeline)
    return pipelines

  def generate_pipeline_from_json(self, plan_json, plan_result_json):
    pipeline = Pipeline()
    pipeline.name = plan_json['name'];
    pipeline.key = plan_json['key']
    for stage_json in plan_json['stages']['stage']:
      if plan_result_json is None or plan_result_json["state"] == "Successful":
        stage = self.generate_stage_from_json(stage_json, None)
      else:
        stage = self.generate_stage_from_json(stage_json, self.find_stage_result_by_name(stage_json["name"], plan_result_json["stages"]["stage"]))
      pipeline.stages.append(stage)
      if stage.blocks_commits and stage.color is "red":
        pipeline.can_commit = False
        pipeline.refresh_time = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")
    return pipeline

  def generate_stage_from_json(self, stage_json, stage_result_json):
    stage = Stage()
    stage.blocks_commits = True
    stage.name = stage_json['name']
    for job_json in stage_json['plans']['plan']:
      if stage_result_json is None:
        job_result_json = None
      else:
        job_result_json = self.find_job_result_by_key(job_json["key"],stage_result_json["results"]["result"])

      job = self.generate_job_from_json(job_json, job_result_json)

      if job.color.find("red") > -1:
        stage.color = "red"
      elif stage.color is not "red" and job.color.find("anime")  > -1:
        stage.color = "blue_anime"
      stage.jobs.append(job)
    return stage

  def generate_job_from_json(self, job_json, job_result_json):
    job = Job(job_json["shortName"], job_json["link"]["href"])
    if job_result_json is None:
      job_result = "Successful"
    else:
      job_result = job_result_json["state"]
    job.color = self.determine_color(job_json["isBuilding"], job_result)
    job.key = job_json["key"]
    return job

  def determine_color(self, is_building, result_string):
    if result_string == "Successful" or result_string == "Unknown":
      if is_building:
        return "blue_anime"
      else:
        return "blue"
    else:
      if is_building:
        return "red_anime"
      else:
        return "red"

  def download_server_info(self, server, path):
    url = urlparse.urljoin(server, path)
    content = HttpHelper.download_html_with_retry(url, 3)
    return content

class MetaButler:
  RETRY_COUNT = 3

  def __init__(self, path_to_config = "config.js"):
    self.pipelines = []
    self.bamboo_servers = []
    self.read_config(path_to_config)
    self.data = {"jobs": {}, "errors": []}

  def read_config(self, path_to_config):
    f = open(path_to_config)
    j = json.load(f)
    self.servers = j['meta_butler']['servers']

    if j['meta_butler'].has_key('bamboo'): 
      self.bamboo_servers = j['meta_butler']['bamboo']['servers']
    connection_string = j["meta_butler"]["memcache_host"] + ":"
    connection_string += j["meta_butler"]["memcache_port"]
    self.mc = memcache.Client([connection_string], debug=0)
    self.pipeline_config = j['pipelines']
    
  def populate_pipelines(self, pipeline_configs, jobs_data):
    for pipeline_json in pipeline_configs:
      pipeline = Pipeline.create_from_jenkins_json(pipeline_json, jobs_data)
      self.pipelines.append(pipeline)

  def collect_claims_from_html(self, server, html_string):
    try:
      html = lxml.html.fromstring(html_string)
      rows = html.cssselect("#projectStatus tr")
      for row in rows:
        claimer = self.get_claimer_from_row(row)
        job_name = self.get_job_name_from_row(row)
        
        if claimer is not None and job_name is not None:
          if self.data["jobs"][server + "job/" + job_name] is not None:
            self.data["jobs"][server + "job/" + job_name]['claim'] = claimer

    except Exception, (error):
      Log.print_with_time("Error occurred in collect_claims_from_html. Error:")
      Log.print_with_time(error)
      raise        
  
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

  def save_bamboo_pipelines(self, bamboo_pipelines):
    for pipeline in bamboo_pipelines:
      self.pipelines.append(pipeline)
    self.mc.set("bamboo_pipelines", json.loads(jsonpickle.encode(bamboo_pipelines, unpicklable=False)))

    
  def add_refresh_time_to_data(self):
    self.data['refresh'] = datetime.datetime.now().strftime("%A %d/%m/%Y - %H:%M:%S")
    
  def do_your_job(self):
    if self.servers is not None:
      self.process_jenkins_servers()
      self.add_refresh_time_to_data()
      self.populate_pipelines(self.pipeline_config, self.data)

    if self.bamboo_servers is not None:
      bamboo_pipelines = Bamboo(self.bamboo_servers).process()

    self.save_bamboo_pipelines(bamboo_pipelines)
    self.save_data()

  def process_jenkins_servers(self):
    for server in self.servers:
      url = server['url']

      jobs_content = self.download_server_info(url)
      if jobs_content is not None:
        try:
          self.collect_jobs_from_json(url, jobs_content)
        except Exception, (error):
          Log.print_with_time("error collecting jobs from this content: ")
          print jobs_content
      
        if server['download_claims']:
          claims_content = self.download_claim_info(url)
          if claims_content is not None:
            try:
              self.collect_claims_from_html(url, claims_content)
            except Exception, (error):
              Log.print_with_time(error)
              Log.print_with_time("error collecting claims from this content: ")
              print claims_content

  def download_server_info(self, server):
    url = urlparse.urljoin(server, "api/json")
    retval = HttpHelper.download_html_with_retry(url, self.RETRY_COUNT)
    if retval is None:
      Log.print_with_time("Warning: no jobs downloaded for server[" + url + "]")
    return retval
  
  def download_claim_info(self, server):
    url = urlparse.urljoin(server,"claims/?")
    retval = self.download_html_with_retry(url, self.RETRY_COUNT)
    if retval is None:
      Log.print_with_time("Warning: no claims downloaded for server[" + url + "]")
    return retval
  
  def download_html_with_retry(self, url, retry_count):
    retval = None
    for i  in range(0, retry_count):
      try:
        retval = urllib2.urlopen(url, timeout=3).read()
        if i != 0:
          Log.print_with_time("Warning: Retrieving url[" + url + "] succeeded after " + str((i+1)) + " times.")
        return retval
      except Exception, (error):
        Log.print_with_time("Error while downloading from url [" + url + "]. Error: " + str(error))
    return None
    
if __name__ == '__main__':
  butler = MetaButler()
  butler.do_your_job()
