#!/usr/bin/env python
"""
    WorkQueue.Policy.Start.Dataset tests
"""

__revision__ = "$Id: Dataset_t.py,v 1.8 2010/07/14 14:46:38 swakef Exp $"
__version__ = "$Revision: 1.8 $"

import unittest
import shutil
from WMCore.WorkQueue.Policy.Start.Dataset import Dataset
#from WMCore.WMSpec.StdSpecs.ReReco import rerecoWorkload, getTestArguments
from WMCore_t.WorkQueue_t.WorkQueue_t import TestReRecoFactory, rerecoArgs
from WMCore_t.WMSpec_t.samples.MultiTaskProcessingWorkload import workload as MultiTaskProcessingWorkload
from WMCore_t.WorkQueue_t.MockDBSReader import MockDBSReader

class DatasetTestCase(unittest.TestCase):

    splitArgs = dict(SliceType = 'NumberOfFiles', SliceSize = 10)

    def testTier1ReRecoWorkload(self):
        """Tier1 Re-reco workflow"""
        Tier1ReRecoWorkload = TestReRecoFactory()('ReRecoWorkload', rerecoArgs)
        inputDataset = Tier1ReRecoWorkload.taskIterator().next().inputDataset()
        dataset = "/%s/%s/%s" % (inputDataset.primary,
                                     inputDataset.processed,
                                     inputDataset.tier)
        dbs = {inputDataset.dbsurl : MockDBSReader(inputDataset.dbsurl, dataset)}
        for task in Tier1ReRecoWorkload.taskIterator():
            units = Dataset(**self.splitArgs)(Tier1ReRecoWorkload, task, dbs)
            self.assertEqual(1, len(units))
            for unit in units:
                self.assertEqual(2, unit['Jobs'])
                self.assertEqual(Tier1ReRecoWorkload, unit['WMSpec'])
                self.assertEqual(task, unit['Task'])
                self.assertEqual(unit['Data'], dataset)


    def testMultiTaskProcessingWorkload(self):
        """Multi Task Processing Workflow"""
        datasets = []
        tasks, count = 0, 0
        for task in MultiTaskProcessingWorkload.taskIterator():
            tasks += 1
            inputDataset = task.inputDataset()
            datasets.append("/%s/%s/%s" % (inputDataset.primary,
                                           inputDataset.processed,
                                           inputDataset.tier))
        dbs = {inputDataset.dbsurl : MockDBSReader(inputDataset.dbsurl, *datasets)}
        for task in MultiTaskProcessingWorkload.taskIterator():
            units = Dataset(**self.splitArgs)(MultiTaskProcessingWorkload, task, dbs)
            self.assertEqual(1, len(units))
            for unit in units:
                self.assertEqual(2, unit['Jobs'])
                self.assertEqual(MultiTaskProcessingWorkload, unit['WMSpec'])
                self.assertEqual(task, unit['Task'])
                self.assertEqual(unit['Data'], datasets[count])
            count += 1
        self.assertEqual(tasks, count)


if __name__ == '__main__':
    unittest.main()
