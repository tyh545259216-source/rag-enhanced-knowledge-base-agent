import unittest
from evaluate import routing_metrics,distribution
class MetricsTests(unittest.TestCase):
    def test_confusion(self):
        cases=[{'expected_tool':'search_knowledge_base','actual_tools':['search_knowledge_base']},
               {'expected_tool':'search_knowledge_base','actual_tools':[]},
               {'expected_tool':None,'actual_tools':['search_knowledge_base']},
               {'expected_tool':None,'actual_tools':[]}]
        m=routing_metrics(cases)
        self.assertEqual([m[k] for k in ['TP','FP','FN','TN']],[1,1,1,1])
        self.assertEqual(m['accuracy'],.5);self.assertEqual(m['precision'],.5);self.assertEqual(m['recall'],.5);self.assertEqual(m['f1'],.5)
    def test_empty(self):self.assertIsNone(routing_metrics([])['accuracy'])
    def test_distribution(self):self.assertEqual(distribution([1,2,3])['median'],2)
if __name__=='__main__':unittest.main()
