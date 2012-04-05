from nose.tools import *
from mock import patch, Mock, call
from meta_butler import Bamboo
from unittest import TestCase
import os.path, time

class TestBamboo:
  config = "tests/fixture_config.js"

  @patch('urllib2.urlopen')
  def test_download_server_info(self, fake_uopen):
    fake_uopen.return_value.read.return_value = '{"plans": { "plan": [] } }'
    Bamboo(["http://someserver/"]).process()
    fake_uopen.assert_called_once_with0("/rest/api/latest/plan.json?expand=plans.plan.stages.stage.plans", timeout=2)

  
