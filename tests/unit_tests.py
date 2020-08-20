from unittest import TestCase, TestLoader, TextTestRunner
from pathlib import Path
import sys
from sndp_gen import SndpGraph, parse_args, command_line

class TestSndpGraph(TestCase):

    def test_init(self):
        num_locations = 5
        num_products = 5
        num_scen = 10
        graph = SndpGraph('instance_name', 5, 5, 10, 1)
        self.assertEqual(len(graph.get_scenarios()),num_scen)
        self.assertEqual(len(graph.get_materials()), num_products-1) # last product in end product
        self.assertEqual(len(graph.get_products()), num_products)
        self.assertEqual(len(graph.get_locations()), num_locations)

    def test_regenerate_stochastic_data(self):
        graph = SndpGraph('instance_name', 5, 5, 10, 1)
        new_num_scen = 5
        graph.regenerate_stochastic_data(new_num_scen)
        self.assertEqual(len(graph.get_scenarios()), new_num_scen)

    def test_visualize(self):
        graph = SndpGraph('instance_name', 20, 5, 20, 1)
        graph.visualize()

    def test_data_as_dict(self):
        num_locations = 5
        num_products = 3
        num_scen = 2
        graph = SndpGraph('instance_name', num_locations, num_products, num_scen, 2)
        data = graph.data_as_dict()
        self.assertEqual(data['NrOfLocations'], num_locations)
        self.assertEqual(data['NrOfProducts'], num_products)
        self.assertEqual(data['NrOfScen'], num_scen)
        # data below might change if we modify the class variables of SndpGraph
        self.assertListEqual(data['MaterialReq'], [{'material': 1, 'value': 2}, {'material': 2, 'value': 3}])
        self.assertListEqual(data['Prob'], [{'SCEN': 1, 'value': 0.5}, {'SCEN': 2, 'value': 0.5}])
        self.assertListEqual(data['Demand'], [{'SCEN': 1, 'value': 6389}, {'SCEN': 2, 'value': 19366}])

    @classmethod
    def tearDownClass(cls):
        files_to_delete = ['instance_name.jpg', 'instance_name']
        for filename in files_to_delete:
            f = Path(filename)
            if f.is_file():
                f.unlink()


class TestCommandLine(TestCase):

    def test_parse_args(self):
        filename = 'param.yaml'
        parsed = parse_args(['--yaml', filename])
        self.assertEqual(parsed.yaml, filename)

    def test_parse_args_default_yaml(self):
        parsed = parse_args([])
        self.assertEqual(parsed.yaml, 'param.yaml')

    def test_command_line(self):
        filename = 'param.yaml'
        sys.argv = sys.argv + ['--yaml', filename]
        self.assertTrue(command_line())

    def test_command_default_yaml(self):
        self.assertTrue(command_line())

    def test_command_wrong_yaml(self):
        filename = 'param_wrong.yaml'
        sys.argv = sys.argv + ['--yaml', filename]
        self.assertFalse(command_line())

if __name__ == '__main__':
    loader = TestLoader()
    suite = loader.discover('')
    runner = TextTestRunner(verbosity=2)
    runner.run(suite)