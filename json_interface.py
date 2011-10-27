from flask import Flask, g, request
import ConfigParser
import memcache, json
from flask import make_response

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

@app.route("/pipelines")
def pipelines():
  return get_data("pipelines")

if __name__ == "__main__":
  app.debug = True
  app.run(host='0.0.0.0', port=8080)
