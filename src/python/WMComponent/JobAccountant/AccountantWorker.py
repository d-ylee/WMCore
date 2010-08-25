#!/usr/bin/env python
#pylint: disable-msg=E1103, W6501, E1101, C0301
#E1103: Use DB objects attached to thread
#W6501: Allow string formatting in error messages
#E1101: Create config sections
#C0301: The names for everything are so ridiculously long
# that I'm disabling this.  The rest of you will have to get
# bigger monitors.
"""
_AccountantWorker_

Used by the JobAccountant to do the actual processing of completed jobs.
"""

__revision__ = "$Id: AccountantWorker.py,v 1.31 2010/05/24 20:40:46 mnorman Exp $"
__version__ = "$Revision: 1.31 $"

import os
import threading
import logging
import gc

from WMCore.Agent.Configuration  import Configuration
from WMCore.FwkJobReport.Report  import Report
from WMCore.DAOFactory           import DAOFactory
from WMCore.Database.Transaction import Transaction

from WMCore.DataStructs.Run import Run
from WMCore.WMBS.File       import File
from WMCore.WMBS.Job        import Job
from WMCore.WMBS.JobGroup   import JobGroup

from WMCore.JobStateMachine.ChangeState import ChangeState
from WMComponent.DBSBuffer.Database.Interface.DBSBufferFile import DBSBufferFile

class AccountantWorker:
    """
    Class that actually does the work of parsing FWJRs for the Accountant
    Run through ProcessPool
    """
    
    def __init__(self, **kwargs):
        """
        __init__

        Create all DAO objects that are used by this class.
        """
        myThread = threading.currentThread()
        self.transaction = myThread.transaction
        self.daoFactory = DAOFactory(package = "WMCore.WMBS",
                                     logger = myThread.logger,
                                     dbinterface = myThread.dbi)
        self.dbsDaoFactory = DAOFactory(package = "WMComponent.DBSBuffer.Database",
                                        logger = myThread.logger,
                                        dbinterface = myThread.dbi)
        self.uploadFactory = DAOFactory(package = "WMComponent.DBSUpload.Database",
                                        logger = myThread.logger,
                                        dbinterface = myThread.dbi)
        

        self.getOutputMapAction      = self.daoFactory(classname = "Jobs.GetOutputMap")
        self.bulkAddToFilesetAction  = self.daoFactory(classname = "Fileset.BulkAddByLFN")
        self.bulkParentageAction     = self.daoFactory(classname = "Files.AddBulkParentage")
        self.getJobTypeAction        = self.daoFactory(classname = "Jobs.GetType")
        self.getParentInfoAction     = self.daoFactory(classname = "Files.GetParentInfo")
        self.getMergedChildrenAction = self.daoFactory(classname = "Files.GetMergedChildren")
        self.setParentageByJob       = self.daoFactory(classname = "Files.SetParentageByJob")
        self.setFileRunLumi          = self.daoFactory(classname = "Files.AddRunLumi")
        self.setFileLocation         = self.daoFactory(classname = "Files.SetLocationByLFN")
        self.setFileAddChecksum      = self.daoFactory(classname = "Files.AddChecksumByLFN")
        self.addFileAction           = self.daoFactory(classname = "Files.Add")
        self.jobCompleteInput        = self.daoFactory(classname = "Jobs.CompleteInput")

        self.dbsStatusAction = self.dbsDaoFactory(classname = "DBSBufferFiles.SetStatus")
        self.dbsParentStatusAction = self.dbsDaoFactory(classname = "DBSBufferFiles.GetParentStatus")
        self.dbsChildrenAction = self.dbsDaoFactory(classname = "DBSBufferFiles.GetChildren")
        self.dbsCreateFiles    = self.dbsDaoFactory(classname = "DBSBufferFiles.Add")
        self.dbsSetLocation    = self.dbsDaoFactory(classname = "DBSBufferFiles.SetLocationByLFN")
        self.dbsInsertLocation = self.dbsDaoFactory(classname = "DBSBufferFiles.AddLocation")
        self.dbsSetChecksum    = self.dbsDaoFactory(classname = "DBSBufferFiles.AddChecksumByLFN")
        self.dbsSetRunLumi     = self.dbsDaoFactory(classname = "DBSBufferFiles.AddRunLumi")


        self.dbsNewAlgoAction    = self.dbsDaoFactory(classname = "NewAlgo")
        self.dbsNewDatasetAction = self.dbsDaoFactory(classname = "NewDataset")
        self.dbsAssocAction      = self.dbsDaoFactory(classname = "AlgoDatasetAssoc")      
        self.dbsExistsAction     = self.dbsDaoFactory(classname = "DBSBufferFiles.ExistsForAccountant")
        self.dbsLFNHeritage      = self.dbsDaoFactory(classname = "DBSBufferFiles.BulkHeritageParent")

        self.dbsSetDatasetAlgoAction = self.uploadFactory(classname = "SetDatasetAlgo")

        config = Configuration()
        config.section_("JobStateMachine")
        config.JobStateMachine.couchurl = kwargs["couchURL"]
        config.JobStateMachine.couchDBName = kwargs["couchDBName"]

        self.stateChanger = ChangeState(config)

        # Hold data for later commital
        self.dbsFilesToCreate  = []
        self.wmbsFilesToBuild  = []
        self.fileLocation      = None
        self.mergedOutputFiles = []
        self.listOfJobsToSave  = []
        self.filesetAssoc      = []
        self.count = 0
        self.assocID           = None

        
        return

    def reset(self):
        """
        _reset_

        Reset all global vars between runs

        """

        self.dbsFilesToCreate  = []
        self.wmbsFilesToBuild  = []
        self.fileLocation      = None
        self.mergedOutputFiles = []
        self.listOfJobsToSave  = []
        self.filesetAssoc      = []
        gc.collect()

        return

    def loadJobReport(self, parameters):
        """
        _loadJobReport_

        Given a framework job report on disk, load it and return a
        FwkJobReport instance.  If there is any problem loading or parsing the
        framework job report return None.
        """
        # The jobReportPath may be prefixed with "file://" which needs to be
        # removed so it doesn't confuse the FwkJobReport() parser.
        jobReportPath = parameters['fwjr_path']
        jobReportPath = jobReportPath.replace("file://","")

        if not os.path.exists(jobReportPath):
            logging.error("Bad FwkJobReport Path: %s" % jobReportPath)
            return self.createMissingFWKJR(parameters, 99999, 'Cannot find file in jobReport path')

        if os.path.getsize(jobReportPath) == 0:
            logging.error("Empty FwkJobReport: %s" % jobReportPath)
            return self.createMissingFWKJR(parameters, 99998, 'jobReport of size 0')

        jobReport = Report()

        try:
            jobReport.load(jobReportPath)
        except Exception, msg:
            logging.error("Cannot load %s: %s" % (jobReportPath, msg))
            return self.createMissingFWKJR(parameters, 99997, 'Cannot load jobReport')

        return jobReport

    def didJobSucceed(self, jobReport):
        """
        _didJobSucceed_
        
        Get the status of the jobReport.  This will loop through all the steps
        and make sure the status is 'Success'.  If a step does not return
        'Success', the job will fail.
        """

        if not hasattr(jobReport, 'data'):
            return False

        if not hasattr(jobReport.data, 'steps'):
            return False


        for step in jobReport.data.steps:
            report = getattr(jobReport.data, step)
            if report.status != 'Success' and report.status != 0:
                return False

        return True
   
    def __call__(self, parameters):
        """
        __call__

        Handle a completed job.  The parameters dictionary will contain the job
        ID and the path to the framework job report.
        """
        returnList = []
        self.transaction.begin()

        for job in parameters:
            logging.info("Handling %s" % job["fwjr_path"])
            
            fwkJobReport = self.loadJobReport(job)
            jobSuccess = None
            
            if not self.didJobSucceed(fwkJobReport):
                logging.error("I have a bad jobReport for %i" %(job['id']))
                self.handleFailed(jobID = job["id"],
                                  fwkJobReport = fwkJobReport)
                jobSuccess = False
            else:
                self.handleSuccessful(jobID = job["id"],
                                      fwkJobReport = fwkJobReport,
                                      fwkJobReportPath = job['fwjr_path'])
                jobSuccess = True
                

            returnList.append({'id': job["id"], 'jobSuccess': jobSuccess})
            self.count += 1
            #if self.count%1000 == 0:
            #    pdb.set_trace()
            #break

        # Now things done at the end of the job

        # Do what we can with WMBS files
        self.handleWMBSFiles()

        # Create DBSBufferFiles
        self.createFilesInDBSBuffer()

        # Handle filesetAssoc
        if len(self.filesetAssoc) > 0:
            self.bulkAddToFilesetAction.execute(binds = self.filesetAssoc,
                                                conn = self.transaction.conn,
                                                transaction = True)
        # Now do WMBSJobs
        idList = []
        for wmbsJob in self.listOfJobsToSave:
            idList.append(wmbsJob['id'])
        if len(idList) > 0:
            self.jobCompleteInput.execute(id = idList,
                                          conn = self.transaction.conn,
                                          transaction = True)

        # Straighten out DBS Parentage
        if len(self.mergedOutputFiles) > 0:
            self.handleDBSBufferParentage()

        self.stateChanger.propagate(self.listOfJobsToSave, "success", "complete")

        self.transaction.commit()
        self.reset()
        return returnList

    def outputFilesetsForJob(self, outputMap, merged, moduleLabel):
        """
        _outputFilesetsForJob_

        Determine if the file should be placed in any other fileset.  Note that
        this will not return the JobGroup output fileset as all jobs will have
        their output placed there.

        If a file is merged and the output map has it going to a merge
        subscription the file will be placed in the output fileset of the merge
        subscription.
        """
        if not outputMap.has_key(moduleLabel):
            logging.info("Output module label missing from output map.")
            return None

        if merged == False:
            return outputMap[moduleLabel]["fileset"]

        if len(outputMap[moduleLabel]["children"]) == 1:
            outputChild = outputMap[moduleLabel]["children"][0]
            if outputChild["child_sub_type"] == "Merge":
                return outputChild["child_sub_output_fset"]

        return outputMap[moduleLabel]["fileset"]        

    def addFileToDBS(self, jobReportFile):
        """
        _addFileToDBS_

        Add a file that was output from a job to the DBS buffer.
        """
        datasetInfo = jobReportFile["dataset"]

        dbsFile = DBSBufferFile(lfn = jobReportFile["lfn"],
                                size = jobReportFile["size"],
                                events = jobReportFile["events"],
                                checksums = jobReportFile["checksums"],
                                status = "NOTUPLOADED")
        dbsFile.setAlgorithm(appName = datasetInfo["applicationName"],
                             appVer = datasetInfo["applicationVersion"],
                             appFam = jobReportFile["module_label"],
                             psetHash = "GIBBERISH", configContent = "MOREGIBBERISH")
        
        dbsFile.setDatasetPath("/%s/%s/%s" % (datasetInfo["primaryDataset"],
                                              datasetInfo["processedDataset"],
                                              datasetInfo["dataTier"]))
        for run in jobReportFile["runs"]:
            newRun = Run(runNumber = run.run)
            newRun.extend(run.lumis)
            dbsFile.addRun(newRun)

        dbsFile.setLocation(se = list(jobReportFile["locations"])[0], immediateSave = False)

        self.dbsFilesToCreate.append(dbsFile)

        return



    def findDBSParents(self, lfn):
        """
        _findDBSParents_
        
        Find the parent of the file in DBS
        This is meant to be called recursively
        """
        parentsInfo = self.getParentInfoAction.execute([lfn],
                                                       conn = self.transaction.conn,
                                                       transaction = True)
        newParents = set()
        for parentInfo in parentsInfo:

            # This will catch straight to merge files that do not have redneck
            # parents.  We will mark the straight to merge file from the job
            # as a child of the merged parent.
            if int(parentInfo["merged"]) == 1:
                newParents.add(parentInfo["lfn"])

            elif parentInfo['gpmerged'] == None:
                continue

            # Handle the files that result from merge jobs that aren't redneck
            # children.  We have to setup parentage and then check on whether or
            # not this file has any redneck children and update their parentage
            # information.
            elif int(parentInfo["gpmerged"]) == 1:
                newParents.add(parentInfo["gplfn"])

            # If that didn't work, we've reached the great-grandparents
            # And we have to work via recursion
            else:
                parentSet = self.findDBSParents(lfn = parentInfo['gplfn'])
                for parent in parentSet:
                    newParents.add(parent)

        return newParents
        

    def addFileToWMBS(self, jobType, fwjrFile, jobMask, jobID = None):
        """
        _addFileToWMBS_

        Add a file that was produced in a job to WMBS.  
        """
        fwjrFile["first_event"] = jobMask["FirstEvent"]
        fwjrFile["last_event"]  = jobMask["LastEvent"]

        if fwjrFile["first_event"] == None:
            fwjrFile["first_event"] = 0
        if fwjrFile["last_event"] == None:
            fwjrFile["last_event"] = fwjrFile["events"]

        if jobType == "Merge" and fwjrFile["module_label"] != "logArchive":
            fwjrFile["merged"] = True

        wmbsFile = self.createFileFromDataStructsFile(file = fwjrFile, jobID = jobID)
        
        if fwjrFile["merged"]:
            self.addFileToDBS(fwjrFile)

        return wmbsFile

    def handleSuccessful(self, jobID, fwkJobReport, fwkJobReportPath = None):
        """
        _handleSuccessful_

        Handle a successful job, parsing the job report and updating the job in
        WMBS.
        """
        wmbsJob = Job(id = jobID)
        wmbsJob.load()
        wmbsJob["outcome"] = "success"
        wmbsJob.getMask()
        outputID = wmbsJob.loadOutputID()

        wmbsJob["fwjr"]    = fwkJobReport

        outputMap = self.getOutputMapAction.execute(jobID = jobID,
                                                    conn = self.transaction.conn,
                                                    transaction = True)

        jobType = self.getJobTypeAction.execute(jobID = jobID,
                                                conn = self.transaction.conn,
                                                transaction = True)

        fileList = fwkJobReport.getAllFiles()

        for fwjrFile in fileList:
            wmbsFile = self.addFileToWMBS(jobType, fwjrFile, wmbsJob["mask"],
                                          jobID = jobID)
            merged = fwjrFile['merged']
            moduleLabel = fwjrFile["module_label"]
            if not wmbsFile and not moduleLabel:
                # Something got screwed up in addFileToWMBS.  Send job to FAIL
                self.transaction.rollback()
                self.transaction.begin()
                self.handleFailed(jobID = jobID, fwkJobReport = fwkJobReport)
                return

            if merged:
                self.mergedOutputFiles.append(wmbsFile)

            self.filesetAssoc.append({"lfn": wmbsFile["lfn"], "fileset": outputID})
            outputFileset = self.outputFilesetsForJob(outputMap, merged, moduleLabel)
            if outputFileset != None:
                self.filesetAssoc.append({"lfn": wmbsFile["lfn"], "fileset": outputFileset})

        # Only save once job is done, and we're sure we made it through okay
        self.listOfJobsToSave.append(wmbsJob)
        wmbsJob.save()

        return
        
    def handleFailed(self, jobID, fwkJobReport):
        """
        _handleFailed_

        Handle a failed job.  Update the job's metadata marking the outcome as
        'failure' and incrementing the retry count.  Mark all the files used as
        input for the job as failed.  Finally, update the job's state.
        """
        wmbsJob = Job(id = jobID)
        wmbsJob.load()

        wmbsJob["outcome"] = "failure"
        wmbsJob["retry_count"] += 1
        wmbsJob.save()
        
        # We'll fake the rest of the state transitions here as the rest of the
        # WMAgent job submission framework is not yet complete.
        wmbsJob["fwjr"] = fwkJobReport
        self.stateChanger.propagate([wmbsJob], "jobfailed", "complete")
        return


    def createMissingFWKJR(self, parameters, errorCode = 999,
                           errorDescription = 'Failure of unknown type'):
        """
        _createMissingFWJR_
        
        Create a missing FWJR if the report can't be found by the code in the
        path location.
        """
        report = Report()
        report.addError("cmsRun1", 84, errorCode, errorDescription)
        report.data.cmsRun1.status = "Failed"
        return report



    def createFilesInDBSBuffer(self):
        """
        _createFilesInDBSBuffer_
        It does the actual job of creating things in DBSBuffer
        WARNING: This assumes all files in a job have the same final location
        """

        if len(self.dbsFilesToCreate) == 0:
            # Whoops, nothing to do!
            return


        dbsFileTuples = []
        dbsLocations  = []
        dbsFileLoc    = []
        dbsCksumBinds = []
        runLumiBinds  = []
        selfChecksums = None
        for dbsFile in self.dbsFilesToCreate:
            # Append a tuple in the format specified by DBSBufferFiles.Add
            # Also run insertDatasetAlgo

            lfn           = dbsFile['lfn']
            selfChecksums = dbsFile['checksums']
            jobLocation   = dbsFile.getLocations()[0]
            
            dbsFileTuples.append((lfn, dbsFile['size'],
                                  dbsFile['events'], dbsFile.insertDatasetAlgo(),
                                  dbsFile['status']))
            
            dbsFileLoc.append({'lfn': lfn, 'sename' : jobLocation})
            runLumiBinds.append({'lfn': lfn, 'runs': dbsFile['runs']})

            if selfChecksums:
                # If we have checksums we have to create a bind
                # For each different checksum
                for entry in selfChecksums.keys():
                    dbsCksumBinds.append({'lfn': lfn, 'cksum' : selfChecksums[entry],
                                          'cktype' : entry})


        self.dbsInsertLocation.execute(siteName = jobLocation,
                                       conn = self.transaction.conn,
                                       transaction = True)

        self.dbsCreateFiles.execute(files = dbsFileTuples,
                                    conn = self.transaction.conn,
                                    transaction = True)

        self.dbsSetLocation.execute(binds = dbsFileLoc,
                                    conn = self.transaction.conn,
                                    transaction = True)

        self.dbsSetChecksum.execute(bulkList = dbsCksumBinds,
                                    conn = self.transaction.conn,
                                    transaction = True)

        self.dbsSetRunLumi.execute(file = runLumiBinds,
                                   conn = self.transaction.conn,
                                   transaction = True)

        # Now that we've created those files, clear the list
        self.dbsFilesToCreate = []

        return


    def handleWMBSFiles(self):
        """
        _handleWMBSFiles_

        Do what can be done in bulk in bulk
        """

        if len(self.wmbsFilesToBuild) == 0:
            # Nothing to do
            return
        
        parentageBinds = []
        runLumiBinds   = []
        fileCksumBinds = []
        fileLocations  = []
        fileCreate     = []

        
        for wmbsFile in self.wmbsFilesToBuild:
            lfn           = wmbsFile['lfn']
            selfChecksums = wmbsFile['checksums']
            parentageBinds.append({'child': lfn, 'jobid': wmbsFile['jid']})
            runLumiBinds.append({'lfn': lfn, 'runs': wmbsFile['runs']})
            fileLocations.append({'lfn': lfn, 'location': wmbsFile.getLocations()[0]})

            if selfChecksums:
                # If we have checksums we have to create a bind
                # For each different checksum
                for entry in selfChecksums.keys():
                    fileCksumBinds.append({'lfn': lfn, 'cksum' : selfChecksums[entry],
                                           'cktype' : entry})

            fileCreate.append([lfn,
                               wmbsFile['size'],
                               wmbsFile['events'],
                               None,
                               wmbsFile["first_event"],
                               wmbsFile["last_event"],
                               wmbsFile['merged']])


        
        self.addFileAction.execute(files = fileCreate,
                                   conn = self.transaction.conn,
                                   transaction = True)

        
        self.setParentageByJob.execute(binds = parentageBinds,
                                       conn = self.transaction.conn,
                                       transaction = True)

        self.setFileRunLumi.execute(file = runLumiBinds,
                                    conn = self.transaction.conn,
                                    transaction = True)

        self.setFileAddChecksum.execute(bulkList = fileCksumBinds,
                                        conn = self.transaction.conn,
                                        transaction = True)

        self.setFileLocation.execute(lfn = fileLocations,
                                     location = self.fileLocation,
                                     conn = self.transaction.conn,
                                     transaction = True)


        # Clear out finished files
        self.wmbsFilesToBuild = []

        return

    def createFileFromDataStructsFile(self, file, jobID):
        """
        _createFileFromDataStructsFile_

        This function will create a WMBS File given a DataStructs file
        """
        wmbsFile = File()
        wmbsFile.update(file)

        if type(file["locations"]) == set:
            seName = list(file["locations"])[0]
        elif type(file["locations"]) == list:
            seName = file["locations"][0]
        else:
            seName = file["locations"]

        wmbsFile["locations"] = set()
        wmbsFile.setLocation(se = seName, immediateSave = False)
        wmbsFile['jid'] = jobID
        self.wmbsFilesToBuild.append(wmbsFile)

        return wmbsFile


    def handleDBSBufferParentage(self):
        """
        _handleDBSBufferParentage_

        Handle all the DBSBuffer Parentage in bulk if you can
        """

        outputLFNs = [f['lfn'] for f in self.mergedOutputFiles]
        bindList         = []
        parentLFNs       = []
        parentMissing    = set()
        for lfn in outputLFNs:
            newParents = self.findDBSParents(lfn = lfn)
            for parentLFN in newParents:
                bindList.append({'child': lfn, 'parent': parentLFN})
            parentLFNs.extend(list(newParents))

        # Now we get whether or not the parents exist
        exists = self.dbsExistsAction.execute(lfn = parentLFNs)
        for parent in parentLFNs:
            if not parent in exists:
                parentMissing.add(parent)


        if len(parentMissing) > 0:
            # Then we have to create parents
            # First, do we need to create a dummy dataset?
            if self.assocID == None:
                # Then we do
                self.createDummyAlgoDataset()


            # Now we just need to add the files
            myThread = threading.currentThread()
            localTransaction = Transaction(myThread.dbi)
            localTransaction.begin()

            # Execute missing parent addition
            action = self.dbsDaoFactory(classname = "DBSBufferFiles.AddIgnore")
            action.execute(lfns = list(parentMissing), datasetAlgo = self.assocID,
                           status = "AlreadyInDBS",
                           conn = localTransaction.conn,
                           transaction = True)

            localTransaction.commit()


        # Now all the parents should exist
        # Commit them to DBSBuffer
        logging.info("About to commit all DBSBuffer Heritage information")

        self.dbsLFNHeritage.execute(binds = bindList,
                                    conn = self.transaction.conn,
                                    transaction = True)

        return




    def createDummyAlgoDataset(self):
        """
        _createDummyAlgoDataset_
        
        Create a dummy algo and dataset for parents
        That have not yet made it into DBS
        """

        logging.info("Creating a bogus dataset and algo")

        myThread = threading.currentThread()
        localTransaction = Transaction(myThread.dbi)
        localTransaction.begin()
        self.dbsNewAlgoAction.execute(appName = "cmsRun", appVer = "UNKNOWN",
                                      appFam = "UNKNOWN", psetHash = "GIBBERISH",
                                      configContent = "MOREBIGGERISH",
                                      conn = localTransaction.conn,
                                      transaction = True)
        
        self.dbsNewDatasetAction.execute(datasetPath = "/bogus/dataset/path",
                                         conn = localTransaction.conn,
                                         transaction = True)
        
        assocID = self.dbsAssocAction.execute(appName = "cmsRun", appVer = "UNKNOWN",
                                              appFam = "UNKNOWN", psetHash = "GIBBERISH",
                                              datasetPath = "/bogus/dataset/path",
                                              conn = localTransaction.conn,
                                              transaction = True)
        
        self.dbsSetDatasetAlgoAction.execute(datasetAlgo = assocID, inDBS = 1,
                                             conn = localTransaction.conn,
                                             transaction = True)

        self.assocID = assocID

        localTransaction.commit()


        return
    
