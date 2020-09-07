import argparse
import sys
from pathlib import Path
import yaml
from sndp_gen import SndpGraph

def parse_args_sndp_gen(args):

    parser = argparse.ArgumentParser(prog='sndp_gen',
                                     description='sndp_gen generates .cor, .tim, .cor files of Stochastic Network Design Problems for the specifc number of locations, products and scenarios.')

    parser.add_argument('--yaml', type=str, default='param.yaml', action='store',
                        help='''yaml file with the parameters of SNDP problems to generate: number of locations, products etc. Filename should include the extension. Default: param.yaml\n
#Example contents:\n
num_locations:\n
    - 10\n
    - 20\n
    - 40\n
num_products:\n
    - 5\n
    - 10\n
    - 20\n
num_scen:\n
    - 1\n
    - 25\n
    - 125\n
    - 500\n
    - 1000\n
    - 10000\n
num_variations: 3\n
''')

    return parser.parse_args(args)


def read_parameters(yaml_filename):
    yaml_file = Path(yaml_filename)
    if yaml_file.is_file():
        with open(yaml_file.resolve()) as file:
            try:
                return yaml.safe_load(file)
            except yaml.YAMLError as e:
                print(e)


def sndp_gen_command():

    '''

    :return: True - no errors happend during the conversion.
    '''

    result = False
    parsed = parse_args_sndp_gen(sys.argv[1:])
    yaml_filename = parsed.yaml

    parameters = read_parameters(yaml_filename)
    if parameters is None:
        print(f"Error: {yaml_filename} yaml file was not found")
        return result

    list_num_locations = parameters.get('num_locations')
    list_num_products = parameters.get('num_products')
    list_num_scen = parameters.get('num_scen')
    num_variations = parameters.get('num_variations')
    if list_num_locations is None:
        print(f"Error: num_locations is not specified in {yaml_filename}")
    elif list_num_products is None:
        print(f"Error: num_products is not specified in {yaml_filename}")
    elif list_num_scen is None:
        print(f"Error: num_scen is not specified in {yaml_filename}")
    elif num_variations is None:
        print(f"Error: num_variations is not specified in {yaml_filename}")
    else:
        # generate all combinations
        for num_locations in list_num_locations:
            for num_products in list_num_products:
                for variation in range(num_variations):
                    num_scen = list_num_scen[0]  # generate instance for the first num_scen in the list_num_scen
                    instance_name = 'SNDP_{}_{}_{}_'.format(num_locations, num_products, variation)
                    graph = SndpGraph(instance_name + str(num_scen), num_locations, num_products, num_scen, random_seed=variation)
                    graph.adjust_sales_price()
                    graph.export_mpl(graph.name)
                    if num_locations <= SndpGraph.INT_MAX_LOCATIONS_TO_VISUALIZE:
                        graph.visualize(to_file=instance_name)
                    # We change only stochastic data for this instances.
                    # We could initilize SNDP_Graph() for every num_scen but since random_seed
                    # stays the same, the core data will also be the same
                    for num_scen in list_num_scen[1:]:
                        graph.regenerate_stochastic_data(num_scen)
                        graph.export_mpl(instance_name + str(num_scen))

        result = True

    return result

def adjust_price_command():
    '''
    Adjust sales price for all SNDP .mpl problems
    '''

    try:
        from sndp_gen.sndp_model import SndpModel
    except ImportError:
        print('OptiMax Library is not installed. Cannot adjust prices of sndp models in .mpl')
        return
    for file in Path().glob("*.mpl"):
        sndp_model = SndpModel(file)
        sndp_model.adjust_sales_price()
