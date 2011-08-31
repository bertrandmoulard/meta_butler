# What it does

- Gathering the jobs from the jenkins servers around
It reads a list of your jenkins servers in config.txt. It creates a hashmap including all jobs from all servers (job url, name, color). It downloads the claim info from the jenkins claim page (it you have installed the claim plugin). It saves the hashmap to memcached server under they key "meta_butler_jobs". The memcached server is specified in the config as well.

To run it once

```
python meta_butler.py
```

to run it continually

```
nohup ./refresh.sh &
```

- Accessing the jobs information
There is a little flask app to access the info in json format.
to start the server in dev mode

```
python json_interface.py
```

for a proper install, see how to run a flask app with wsgi: http://flask.pocoo.org/docs/deploying/mod_wsgi/

http://hostname/jobs will get you the json with all the jobs
http://hostname/jobs?jobs=http://my.ci.server/jobs/unittests,http://my.ci.server/jobs/acceptancetests will get you the json for two jobs only (so provide a csv list of job urls to filter to response)
