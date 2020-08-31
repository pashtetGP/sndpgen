import argparse
import sys
from pathlib import Path
import yaml
from pkg_resources import resource_filename
from sndp_gen import SndpGraph
from opt_convert import MplWithExtData

def parse_args(args):

    parser = argparse.ArgumentParser(prog='sndp_gen',
                                     description='sndp_gen generates .cor, .tim, .cor files of Stochastic Network Design Problems for the specifc number of locations, products and scenarios.')

    parser.add_argument('--yaml', type=str, default='param.yaml', action='store',
                        help='''yaml filename with the parameters of SNDP problems: number of locations, products etc. Filename should include the extension. Default: param.yaml
#Example:
num_locations:
    - 10
    - 20
    - 40
num_products:
    - 5
    - 10
    - 20
num_scen:
    - 1
    - 25
    - 125
    - 500
    - 1000
    - 10000
num_variations: 3
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


def command_line():

    '''

    :return: True - no errors happend during the conversion.
    '''

    result = False
    parsed = parse_args(sys.argv[1:])
    yaml_filename = parsed.yaml

    parameters = read_parameters(yaml_filename)

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
        sndp_path = resource_filename(__name__, 'SNDP_default.mpl')
        initial_model = MplWithExtData(Path(sndp_path))
        # copy model so that we do not modify the initial files
        initial_model.export(Path('SNDP_default.mpl'))
        stochastic_model = MplWithExtData(Path('SNDP_default.mpl'))
        # generate all combinations
        for num_locations in list_num_locations:
            for num_products in list_num_products:
                for variation in range(num_variations):
                    num_scen = list_num_scen[0]  # generate instance for the first num_scen in the list_num_scen
                    instance_name = 'SNDP_{}_{}_{}_{}'.format(num_locations, num_products, variation, num_scen)
                    graph = SndpGraph(instance_name, num_locations, num_products, num_scen, random_seed=variation)
                    stochastic_model.set_ext_data(graph.data_as_dict())
                    stochastic_model.export(Path(instance_name).with_suffix('.mpl'))
                    stochastic_model.export(Path(instance_name).with_suffix('.mps'))
                    graph.visualize(to_file=instance_name)
                    # We change only stochastic data for this instances.
                    # We could initilize SNDP_Graph() for every num_scen but since random_seed
                    # stays the same, the core data will also be the same
                    for num_scen in list_num_scen[1:]:
                        instance_name = 'SNDP_{}_{}_{}_{}'.format(num_locations, num_products, variation, num_scen)
                        graph.regenerate_stochastic_data(num_scen)
                        stochastic_model.set_ext_data(graph.data_as_dict())
                        stochastic_model.export(Path(instance_name).with_suffix('.mpl'))
                        stochastic_model.export(Path(instance_name).with_suffix('.mps'))
                        graph.visualize(to_file=instance_name)

        result = True

    return result