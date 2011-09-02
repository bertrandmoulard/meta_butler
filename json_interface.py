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
  try:
    return json.dumps(g.mc.get("meta_butler_data"))
  except Exception, (error):
    return json.dumps({"errors": ["error getting data from memcached"]})
  
if __name__ == "__main__":
  app.debug = True
  app.run(host='0.0.0.0', port=8080)