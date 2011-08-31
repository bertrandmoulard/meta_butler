from flask import Flask, g, request
import ConfigParser
import memcache, json

app = Flask(__name__)

def get_memcache_client():
  return memcache.Client(['127.0.0.1:11211'], debug=0)
  
@app.before_request
def before_request():
  g.mc = get_memcache_client()
  
@app.teardown_request
def teardown_request(exception):
  g.mc.disconnect_all()

@app.route("/jobs")
def jobs():
  all_jobs, jobs_to_return = g.mc.get("meta_butler_jobs"), {}
  for key in [job.strip() for job in request.args.get('jobs').split(",")]:
    if all_jobs.has_key(key):
      jobs_to_return = all_jobs[key]
  return json.dumps(jobs_to_return)
  
if __name__ == "__main__":
  app.debug = True
  app.run(host='0.0.0.0', port=8080)
