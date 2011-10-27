{
	"meta_butler" : {
		"servers": [
			"http://ci.cp.vpc.realestate.com.au:8080/", 
      "http://ci.vpc.realestate.com.au:8080/", 
			"http://10.113.192.70:9080/"
  	],
  	"memcache_host": "127.0.0.1",
  	"memcache_port": "11211"
	}, 
	"pipelines": [
		{
			"name": "Customer Systems",
			"stages": [
				{
					"name": "Commit", 
					"blocks_commits": true,
					"jobs": [
						"http://ci.cp.vpc.realestate.com.au:8080/job/cp-01-quality/", 
						"http://ci.cp.vpc.realestate.com.au:8080/job/cp-09-performance/"
					]
				},
				{
					"name": "Package",
					"blocks_commits": false,
					"jobs": [
						"http://ci.cp.vpc.realestate.com.au:8080/job/cp-rpmify/"
				  ]
				}
			]
			
		}
	]
}
