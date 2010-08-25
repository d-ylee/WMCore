#!/usr/bin/env python


"""
Checks for finished subscriptions
Upon finding finished subscriptions, notifies WorkQueue and kills them
"""

__revision__ = "$Id: TaskArchiver.py,v 1.1 2009/10/30 13:43:05 mnorman Exp $"
__version__ = "$Revision: 1.1 $"

import logging
import threading

from WMCore.Agent.Harness import Harness
from WMCore.WMFactory import WMFactory

from WMComponent.TaskArchiver.TaskArchiverPoller import TaskArchiverPoller

#from WMCore.WorkQueue.WorkQueue import WorkQueue




class TaskArchiver(Harness):

    def __init__(self, config):
        # call the base class
        Harness.__init__(self, config)
        self.pollTime = 1

        self.config = config
        
	print "TaskArchiver.__init__"

    def preInitialization(self):
	print "TaskArchiver.preInitialization"

        # Add event loop to worker manager
        myThread = threading.currentThread()

        pollInterval = self.config.TaskArchiver.pollInterval
        logging.info("Setting poll interval to %s seconds" % pollInterval)
        myThread.workerThreadManager.addWorker(TaskArchiverPoller(self.config), pollInterval)

        return
