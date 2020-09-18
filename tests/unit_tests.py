from unittest import TestCase, TestLoader, TextTestRunner
from pathlib import Path
import sys
from sndpgen import SndpGraph, Timer, parse_args_sndp_gen, generate_command

class TestSndpGraph(TestCase):

    @classmethod
    def setUpClass(cls):
        SndpGraph.DEBUG = True

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
        data = graph.data_as_dict
        self.assertEqual(data['NrOfLocations'], num_locations)
        self.assertEqual(data['NrOfProducts'], num_products)
        self.assertEqual(data['NrOfScen'], num_scen)
        # data below might change if we modify the class variables of SndpGraph
        self.assertListEqual(data['MaterialReq'], [{'material': 1, 'value': 2}, {'material': 2, 'value': 3}])
        self.assertListEqual(data['Prob'], [{'SCEN': 1, 'value': 0.5}, {'SCEN': 2, 'value': 0.5}])
        self.assertListEqual(data['Demand'], [{'SCEN': 1, 'value': 5673}, {'SCEN': 2, 'value': 7295}])

    def test_adjust_sales_price(self):
        num_locations = 10
        num_products = 5
        num_scen = 3
        graph = SndpGraph('instance_name', num_locations, num_products, num_scen, 2)
        init_sales_price = graph.sales_price
        graph.adjust_sales_price()
        self.assertLessEqual(graph.sales_price, init_sales_price)

    @classmethod
    def tearDownClass(cls):
        for file in Path().glob("instance_name*"):
            file.unlink()


class TestCommandLineSndpGen(TestCase):

    @classmethod
    def setUpClass(cls):
        SndpGraph.DEBUG = True

    def test_parse_args(self):
        filename = 'param.yaml'
        parsed = parse_args_sndp_gen(['--yaml', filename])
        self.assertEqual(parsed.yaml, filename)

    def test_parse_args_default_yaml(self):
        parsed = parse_args_sndp_gen([])
        self.assertEqual(parsed.yaml, 'param.yaml')

    def test_command_line(self):
        Timer('test_command_line').start()
        filename = 'param.yaml'
        sys.argv = sys.argv + ['--yaml', filename]
        self.assertTrue(generate_command())
        Timer('test_command_line').pause()
        Timer.report()

    def test_command_default_yaml(self):
        self.assertTrue(generate_command())

    def test_command_wrong_yaml(self):
        filename = 'param_wrong.yaml'
        sys.argv = sys.argv + ['--yaml', filename]
        self.assertFalse(generate_command())

    @classmethod
    def tearDownClass(cls):
        for file in Path().glob("SNDP_*"):
             file.unlink()


try:
    from sndpgen.sndp_model import SndpModel
except ImportError:
    pass
else:
    class TestSndpModel(TestCase):

        @classmethod
        def setUpClass(cls):
            cls.model_path = Path(f'10_5_0_1.mpl')

        def test_adjust_sales_price(self):
            original_sndp_model = SndpModel(self.model_path)
            sndp_model_path = Path(f'SNDP_10_5_0_1_temp.mpl')
            original_sndp_model.export(sndp_model_path) # we do not want to modify the original model
            sndp_model = SndpModel(sndp_model_path)
            init_sales_price = sndp_model.data_as_dict['SalesPrice']
            init_num_open_locations = len(sndp_model.solution_open_production)
            sndp_model.adjust_sales_price()
            adjusted_sales_price = sndp_model.data_as_dict['SalesPrice']
            adjusted_num_open_locations = len(sndp_model.solution_open_production)
            self.assertLessEqual(adjusted_sales_price, init_sales_price)
            self.assertLessEqual(init_num_open_locations, adjusted_num_open_locations)

        @classmethod
        def tearDownClass(cls):
            for file in Path().glob("SNDP_*"):
                file.unlink()

if __name__ == '__main__':
    loader = TestLoader()
    suite = loader.discover('')
    runner = TextTestRunner(verbosity=2)
    runner.run(suite)