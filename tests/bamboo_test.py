from nose.tools import *
from mock import patch, Mock, call
from meta_butler import Bamboo
from unittest import TestCase
import os.path, time

class TestBamboo:

  #@patch('urllib2.urlopen')
  def test_download_server_info(self):
    print "hello"
    Bamboo(["http://master.cd.vpc.realestate.com.au:8085"]).process()
    assert True == False
  