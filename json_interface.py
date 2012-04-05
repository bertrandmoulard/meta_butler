from flask import Flask, g, request
import ConfigParser
import memcache, json
from flask import make_response
import os

app = Flask(__name__)

def get_data(key):
  data = ''
  try:
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    data = mc.get(key)
    mc.disconnect_all()
    data = json.dumps(data)
  except Exception, (error):
    data = json.dumps({"errors": ["error getting data from memcached"]})
  resp = make_response(data, 200)
  resp.headers["Access-Control-Allow-Origin"] = "*";
  return resp

@app.route("/jobs")
def jobs():
  return get_data("all_jobs")

@app.route("/pipelines.json")
@app.route("/pipelines")
def pipelines():
  return get_data("pipelines")

@app.route("/bamboo_pipelines")
def bamboo_pipelines():
  return get_data("bamboo_pipelines")

@app.route("/config.json")
def config():
  f = open(os.path.join("/", "home", "ci", "meta_butler", "config.js"))
  content = f.read()
  f.close()
  return content

if __name__ == "__main__":
  app.debug = True
  app.run(host='0.0.0.0', port=8080)
