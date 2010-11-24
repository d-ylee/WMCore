#!/usr/bin/env python
"""
_Report_t_

Unit tests for the Report class.
"""

import unittest
import os
import xml.dom.minidom
import time

import WMCore.WMInit

from WMCore.FwkJobReport.Report import Report
from WMCore.WMSpec.Steps.WMExecutionFailure import WMExecutionFailure

class ReportTest(unittest.TestCase):
    """
    _ReportTest_

    Unit tests for the Report class.
    """
    def setUp(self):
        """
        _setUp_

        Figure out the location of the XML report produced by CMSSW.
        """
        self.xmlPath = os.path.join(WMCore.WMInit.getWMBASE(),
                                    "test/python/WMCore_t/FwkJobReport_t/CMSSWProcessingReport.xml")
        self.badxmlPath = os.path.join(WMCore.WMInit.getWMBASE(),
                                    "test/python/WMCore_t/FwkJobReport_t/CMSSWFailReport2.xml")
        return

    # json/dejson
    # persist/unpersist load/save
    # add error

    # retrieveStep
    # getOutputModule
    # getOutputFile
    # getAllFilesFromStep
    # getAllFiles

    def verifyInputData(self, report):
        """
        _verifyInputData_

        Verify that the input file in the Report class matches the input file in
        the XML generated by CMSSW.
        """
        inputFiles = report.getInputFilesFromStep("cmsRun1")

        assert len(inputFiles) == 1, \
               "Error: Wrong number of input files."
        assert inputFiles[0]["lfn"] == "/store/data/BeamCommissioning09/MinimumBias/RAW/v1/000/122/023/142F3F42-C5D6-DE11-945D-000423D94494.root", \
               "Error: Wrong LFN on input file."
        assert inputFiles[0]["pfn"] == "dcap://cmsdca.fnal.gov:24137/pnfs/fnal.gov/usr/cms/WAX/11/store/data/BeamCommissioning09/MinimumBias/RAW/v1/000/122/023/142F3F42-C5D6-DE11-945D-000423D94494.root", \
               "Error: Wrong PFN on input file."

        inputRun = list(inputFiles[0]["runs"])
        assert len(inputRun) == 1, \
               "Error: Wrong number of runs in input."
        assert inputRun[0].run == 122023, \
               "Error: Wrong run number on input file."
        assert len(inputRun[0].lumis) == 1, \
               "Error: Wrong number of lumis in input file."
        assert 215 in inputRun[0].lumis, \
               "Error: Input file is missing lumis."

        assert inputFiles[0]["events"] == 2, \
               "Error: Wrong number of events in input file."
        assert inputFiles[0]["size"] == 0, \
               "Error: Wrong size in input file."

        assert inputFiles[0]["catalog"] == "trivialcatalog_file:/uscmst1/prod/sw/cms/SITECONF/T1_US_FNAL/PhEDEx/storage.xml?protocol=dcap", \
               "Error: Catalog on input file is wrong."
        assert inputFiles[0]["guid"] == "142F3F42-C5D6-DE11-945D-000423D94494", \
               "Error: GUID of input file is wrong."
        
        return

    def verifyRecoOutput(self, report):
        """
        _verifyRecoOutput_

        Verify that all the metadata in the RECO output module is correct.
        """
        outputFiles = report.getFilesFromOutputModule("cmsRun1", "outputRECORECO")

        assert len(outputFiles) == 1, \
               "Error: Wrong number of output files."
        assert outputFiles[0]["lfn"] == "/store/backfill/2/unmerged/WMAgentCommissioining10/MinimumBias/RECO/rereco_GR09_R_34X_V5_All_v1/0000/outputRECORECO.root", \
               "Error: Wrong LFN on output file: %s" % outputFiles[0]["lfn"]
        assert outputFiles[0]["pfn"] == "outputRECORECO.root", \
               "Error: Wrong PFN on output file."

        outputRun = list(outputFiles[0]["runs"])
        assert len(outputRun) == 1, \
               "Error: Wrong number of runs in output."
        assert outputRun[0].run == 122023, \
               "Error: Wrong run number on output file."
        assert len(outputRun[0].lumis) == 1, \
               "Error: Wrong number of lumis in output file."
        assert 215 in outputRun[0].lumis, \
               "Error: Output file is missing lumis."

        assert outputFiles[0]["events"] == 2, \
               "Error: Wrong number of events in output file."
        assert outputFiles[0]["size"] == 0, \
               "Error: Wrong size in output file."

        assert len(outputFiles[0]["input"]) == 1, \
               "Error: Wrong number of input files."
        assert outputFiles[0]["input"][0] == "/store/data/BeamCommissioning09/MinimumBias/RAW/v1/000/122/023/142F3F42-C5D6-DE11-945D-000423D94494.root", \
               "Error: LFN of input file is wrong."

        assert len(outputFiles[0]["checksums"]) == 0, \
               "Error: There should be no checksums in output file."
        assert outputFiles[0]["catalog"] == "", \
               "Error: Catalog on output file is wrong."
        assert outputFiles[0]["guid"] == "7E3359C8-222E-DF11-B2B0-001731230E47", \
               "Error: GUID of output file is wrong: %s" % outputFiles[0]["guid"]
        assert outputFiles[0]["module_label"] == "outputRECORECO", \
               "Error: Module label of output file is wrong."
        assert outputFiles[0]["branch_hash"] == "cf37adeb60b427f4ccd0e21b5771146b", \
               "Error: Branch has on output file is wrong."

        return

    def verifyAlcaOutput(self, report):
        """
        _verifyAlcaOutput_

        Verify that all of the meta data in the ALCARECO output module is
        correct.
        """
        outputFiles = report.getFilesFromOutputModule("cmsRun1", "outputALCARECORECO")
        assert len(outputFiles) == 1, \
               "Error: Wrong number of output files."
        assert outputFiles[0]["lfn"] == "/store/backfill/2/unmerged/WMAgentCommissioining10/MinimumBias/ALCARECO/rereco_GR09_R_34X_V5_All_v1/0000/B8F849C9-222E-DF11-B2B0-001731230E47.root", \
               "Error: Wrong LFN on output file: %s" % outputFiles[0]["lfn"]
        assert outputFiles[0]["pfn"] == "outputALCARECORECO.root", \
               "Error: Wrong PFN on output file."

        outputRun = list(outputFiles[0]["runs"])
        assert len(outputRun) == 1, \
               "Error: Wrong number of runs in output."
        assert outputRun[0].run == 122023, \
               "Error: Wrong run number on output file."
        assert len(outputRun[0].lumis) == 1, \
               "Error: Wrong number of lumis in output file."
        assert 215 in outputRun[0].lumis, \
               "Error: Output file is missing lumis."

        assert outputFiles[0]["events"] == 2, \
               "Error: Wrong number of events in output file."
        assert outputFiles[0]["size"] == 0, \
               "Error: Wrong size in output file."

        assert len(outputFiles[0]["input"]) == 1, \
               "Error: Wrong number of input files."
        assert outputFiles[0]["input"][0] == "/store/data/BeamCommissioning09/MinimumBias/RAW/v1/000/122/023/142F3F42-C5D6-DE11-945D-000423D94494.root", \
               "Error: LFN of input file is wrong."

        assert len(outputFiles[0]["checksums"]) == 0, \
               "Error: There should be no checksums in output file."
        assert outputFiles[0]["catalog"] == "", \
               "Error: Catalog on output file is wrong."
        assert outputFiles[0]["guid"] == "B8F849C9-222E-DF11-B2B0-001731230E47", \
               "Error: GUID of output file is wrong: %s" % outputFiles[0]["guid"]
        assert outputFiles[0]["module_label"] == "outputALCARECORECO", \
               "Error: Module label of output file is wrong."
        assert outputFiles[0]["branch_hash"] == "cf37adeb60b427f4ccd0e21b5771146b", \
               "Error: Branch has on output file is wrong."

        return    

    def testXMLParsing(self):
        """
        _testParsing_

        Verify that the parsing of a CMSSW XML report works correctly.
        """
        myReport = Report("cmsRun1")
        myReport.parse(self.xmlPath)

        self.verifyInputData(myReport)
        self.verifyRecoOutput(myReport)
        self.verifyAlcaOutput(myReport)

        return

    def testBadXMLParsing(self):
        """
        _testBadXMLParsing_

        Verify that the parsing of a CMSSW XML report works correctly even if
        the XML is malformed.
        """
        myReport = Report("cmsRun1")
        myReport.parse(self.badxmlPath)
        return    

    def testErrorReporting(self):
        """
        _testErrorReporting_

        Verify that errors are correctly transfered from the XML report to the
        python report.
        """
        cmsException = \
"""cms::Exception caught in cmsRun
---- EventProcessorFailure BEGIN
EventProcessingStopped
---- ScheduleExecutionFailure BEGIN
ProcessingStopped
---- NoRecord BEGIN
No "CastorDbRecord" record found in the EventSetup.
 Please add an ESSource or ESProducer that delivers such a record.
cms::Exception going through module CastorRawToDigi/castorDigis run: 121849 lumi: 1 event: 23
---- NoRecord END
Exception going through path raw2digi_step
---- ScheduleExecutionFailure END
an exception occurred during current event processing
cms::Exception caught in EventProcessor and rethrown
---- EventProcessorFailure END"""

        xmlPath = os.path.join(WMCore.WMInit.getWMBASE(),
                               "test/python/WMCore_t/FwkJobReport_t/CMSSWFailReport.xml")

        myReport = Report("cmsRun1")
        myReport.parse(xmlPath)

        assert hasattr(myReport.data.cmsRun1, "errors"), \
               "Error: Error section missing."
        assert getattr(myReport.data.cmsRun1.errors, "errorCount") == 1, \
               "Error: Error count is wrong."
        assert hasattr(myReport.data.cmsRun1.errors, "error0"), \
               "Error: Error0 section is missing."
        assert myReport.data.cmsRun1.errors.error0.type == "CMSException", \
               "Error: Wrong error type."
        assert myReport.data.cmsRun1.errors.error0.exitCode == "8001", \
               "Error: Wrong exit code."
        assert myReport.data.cmsRun1.errors.error0.details == cmsException, \
               "Error: Error details are wrong:\n|%s|\n|%s|" % (myReport.data.cmsRun1.errors.error0.details,
                                                               cmsException)
        
        return

    def testMultipleInputs(self):
        """
        _testMultipleInputs_

        Verify that parsing XML reports with multiple inputs works correctly.
        """
        xmlPath = os.path.join(WMCore.WMInit.getWMBASE(),
                               "test/python/WMCore_t/FwkJobReport_t/CMSSWMultipleInput.xml")        
        myReport = Report("cmsRun1")
        myReport.parse(xmlPath)

        assert hasattr(myReport.data.cmsRun1.input, "source"), \
               "Error: Report missing input source."

        inputFiles = myReport.getInputFilesFromStep("cmsRun1")

        assert len(inputFiles) == 2, \
               "Error: Wrong number of input files."

        for inputFile in inputFiles:
            assert inputFile["input_type"] == "primaryFiles", \
                   "Error: Wrong input type."
            assert inputFile["module_label"] == "source", \
                   "Error: Module label is wrong"
            assert inputFile["catalog"] == "trivialcatalog_file:/uscmst1/prod/sw/cms/SITECONF/T1_US_FNAL/PhEDEx/storage.xml?protocol=dcap", \
                   "Error: Catalog is wrong."
            assert inputFile["events"] == 2, \
                   "Error: Wrong number of events."
            assert inputFile["input_source_class"] == "PoolSource", \
                   "Error: Wrong input source class."

            if inputFile["guid"] == "F0875ECD-3347-DF11-9FE0-003048678A80":
                assert inputFile["lfn"] == "/store/backfill/2/unmerged/WMAgentCommissioining10/MinimumBias/RECO/rereco_GR10_P_V4_All_v1/0000/F0875ECD-3347-DF11-9FE0-003048678A80.root", \
                       "Error: Input LFN is wrong."
                assert inputFile["pfn"] == "dcap://cmsdca3.fnal.gov:24142/pnfs/fnal.gov/usr/cms/WAX/11/store/backfill/2/unmerged/WMAgentCommissioining10/MinimumBias/RECO/rereco_GR10_P_V4_All_v1/0000/F0875ECD-3347-DF11-9FE0-003048678A80.root", \
                       "Error: Input PFN is wrong."
                assert len(inputFile["runs"]) == 1, \
                       "Error: Wrong number of runs."
                assert list(inputFile["runs"])[0].run == 124216, \
                       "Error: Wrong run number."
                assert 1 in list(inputFile["runs"])[0], \
                       "Error: Wrong lumi sections in input file."
            else:
                assert inputFile["guid"] == "626D74CE-3347-DF11-9363-0030486790C0", \
                       "Error: Wrong guid."
                assert inputFile["lfn"] == "/store/backfill/2/unmerged/WMAgentCommissioining10/MinimumBias/RECO/rereco_GR10_P_V4_All_v1/0000/626D74CE-3347-DF11-9363-0030486790C0.root", \
                       "Error: Input LFN is wrong."
                assert inputFile["pfn"] == "dcap://cmsdca3.fnal.gov:24142/pnfs/fnal.gov/usr/cms/WAX/11/store/backfill/2/unmerged/WMAgentCommissioining10/MinimumBias/RECO/rereco_GR10_P_V4_All_v1/0000/626D74CE-3347-DF11-9363-0030486790C0.root", \
                       "Error: Input PFN is wrong."
                assert len(inputFile["runs"]) == 1, \
                       "Error: Wrong number of runs."
                assert list(inputFile["runs"])[0].run == 124216, \
                       "Error: Wrong run number."
                assert 2 in list(inputFile["runs"])[0], \
                       "Error: Wrong lumi sections in input file."

        return

    def testJSONEncoding(self):
        """
        _testJSONEncoding_

        Verify that turning the FWJR into a JSON object works correctly.
        """
        xmlPath = os.path.join(WMCore.WMInit.getWMBASE(),
                               "test/python/WMCore_t/FwkJobReport_t/CMSSWProcessingReport.xml")
        myReport = Report("cmsRun1")
        myReport.parse(xmlPath)

        jsonReport = myReport.__to_json__(None)

        assert "task" in jsonReport.keys(), \
               "Error: Task name missing from report."

        assert len(jsonReport["steps"].keys()) == 1, \
               "Error: Wrong number of steps in report."
        assert "cmsRun1" in jsonReport["steps"].keys(), \
               "Error: Step missing from json report."
        
        cmsRunStep = jsonReport["steps"]["cmsRun1"]

        jsonReportSections = ["status", "errors", "logs", "parameters", "site",
                              "analysis", "cleanup", "input", "output", "start"]
        for jsonReportSection in jsonReportSections:
            assert jsonReportSection in cmsRunStep.keys(), \
                "Error: missing section: %s" % jsonReportSection
                
        return

    def testTimeSetting(self):
        """
        _testTimeSetting_

        Can we set the times correctly?
        """
        stepName = "cmsRun1"
        timeDiff = 0.01
        myReport = Report(stepName)
        localTime = time.time()
        myReport.setStepStartTime(stepName)
        myReport.setStepStopTime(stepName)
        repTime = myReport.getTimes(stepName)

        self.assertTrue(repTime["startTime"] - localTime < timeDiff)
        self.assertTrue(repTime["stopTime"] - localTime < timeDiff)

        return


    def testTaskJobID(self):
        """
        _testTaskJobID_

        Test the basic task and jobID functions
        """


        report = Report('fake')
        self.assertEqual(report.getTaskName(), None)
        self.assertEqual(report.getJobID(), None)
        report.setTaskName('silly')
        report.setJobID(100)
        self.assertEqual(report.getTaskName(), 'silly')
        self.assertEqual(report.getJobID(), 100)

        return
        
    
if __name__ == "__main__":
    unittest.main()
