#!/usr/bin/env python
"""
The actual taskArchiver algorithm
"""
__all__ = []
__revision__ = "$Id: TaskArchiverPoller.py,v 1.1 2009/10/30 13:43:05 mnorman Exp $"
__version__ = "$Revision: 1.1 $"

import threading
import logging
import re
import os
import os.path
from sets import Set

from subprocess import Popen, PIPE

from WMCore.WorkerThreads.BaseWorkerThread import BaseWorkerThread

from WMCore.WMBS.Subscription import Subscription
from WMCore.WMBS.Fileset      import Fileset
from WMCore.WMBS.Workflow     import Workflow
from WMCore.WMBS.Job          import Job
from WMCore.WMFactory         import WMFactory
from WMCore.DAOFactory        import DAOFactory

class TaskArchiverPoller(BaseWorkerThread):
    """
    Polls for Error Conditions, handles them
    """
    def __init__(self, config):
        """
        Initialise class members
        """
        BaseWorkerThread.__init__(self)
        self.config = config
    
    def setup(self, parameters):
        """
        Load DB objects required for queries
        """

        myThread = threading.currentThread()

        self.daoFactory = DAOFactory(package = "WMCore.WMBS",
                                     logger = myThread.logger,
                                     dbinterface = myThread.dbi)


        return




    def terminate(self,params):
        logging.debug("terminating. doing one more pass before we die")
        self.algorithm(params)
        return


    

    def algorithm(self, parameters):
        """
	Performs the archiveJobs method, looking for each type of failure
	And deal with it as desired.
        """
        logging.debug("Running algorithm for finding finished subscriptions")
        myThread = threading.currentThread()
        try:
            self.archiveTasks()
        except:
            raise

        return


    def archiveTasks(self):
        """
        _archiveJobs_
        
        archiveJobs will handle the master task of looking for finished subscriptions,
        checking to see if they've finished, and then notifying the workQueue and
        finishing things up.
        """


        myThread = threading.currentThread()

        subList  = self.findFinishedSubscriptions()
        doneList = self.notifyWorkQueue(subList)
        self.killSubscriptions(doneList)
        #self.cleanWorkArea(doneList)


    def findFinishedSubscriptions(self):
        """
        _findFinishedSubscriptions_
        
        Figures out which one of the subscriptions is actually finished.
        """
        subList = []

        myThread = threading.currentThread()

        myThread.transaction.begin()

        jobListAction = self.daoFactory(classname = "Jobs.GetAllJobs")
        jobList  = jobListAction.execute(state = "cleanout")

        subscriptionList = self.daoFactory(classname = "Subscriptions.List")
        subscriptions    = subscriptionList.execute()

        for subscription in subscriptions:
            wmbsSubscription = Subscription(id = subscription)
            jobs             = wmbsSubscription.getJobs()
            finished = True
            if len(jobs) == 0:
                finished = False
            for job in jobs:
                if not job['id'] in jobList:
                    finished = False
                    break
            if finished:
                subList.append(wmbsSubscription)

        myThread.transaction.commit()
                
        return subList

    def notifyWorkQueue(self, subList):
        """
        _notifyWorkQueue_
        
        Tells the workQueue component that a particular subscription,
        or set of subscriptions, is done.  Receives confirmation
        """

        doneList = []

        #In the future, this will talk to the workQueue
        #Right now it doesn't because I'm not sure how to do it
        doneList = subList

        return doneList


    def killSubscriptions(self, doneList):
        """
        _killSubscriptions_
        
        Actually dump the subscriptions
        """

        for subscription in doneList:
            subscription.deleteEverything()

        return



        
    
