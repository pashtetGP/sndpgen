import random
import time
from graphviz import Digraph
import multiprocessing as mp
import math
from warnings import warn
from pkg_resources import resource_filename
from pathlib import Path


class Timer:
    _timers = {}

    @classmethod
    def reset_all(cls):
        for timer in cls._timers.values():
            timer.reset()

    @classmethod
    def report(cls):
        print('Timer: total elapsed time, sec')
        for timer_label in sorted(cls._timers.keys()):
            print(cls._timers[timer_label])

    def __init__(self, label):
       if label in self._timers: # we already have such timer
            current_timer = self._timers[label]
            self._current_start = current_timer._current_start
            self._previous_elapsed = current_timer._previous_elapsed
            self._label = label
            self._timers[label] = self
       else:
            self._current_start = None
            self._previous_elapsed = 0
            self._label = label
            self._timers[label] = self


    @property
    def elapsed_time(self): # total elapsed time
        if self._current_start is None: # timer is not running
            return self._previous_elapsed
        else:
            return self._previous_elapsed + (time.perf_counter() - self._current_start)

    def start(self):
        if self._current_start is not None:
            raise RuntimeError(f"Timer is running. Use .pause() to stop it")

        self._current_start = time.perf_counter()

    def pause(self):
        if self._current_start is None:
            raise RuntimeError(f"Timer is not running. Use .unpause() to start it")

        self._previous_elapsed += time.perf_counter() - self._current_start
        self._current_start = None

    def reset(self):
        self._current_start = None
        self._previous_elapsed = 0

    def __repr__(self):
        return f'{self._label}: {self.elapsed_time:0.4f}'

    def __str__(self):
        return self.__repr__()

def progress_bar(task: str, current: int, total: int, barLength = 20):
    percent = float(current) * 100 / total
    arrow   = '-' * int(percent/100 * barLength - 1) + '>'
    spaces  = ' ' * (barLength - len(arrow))
    bar_str = f'{task}: [{arrow}{spaces}] {current}/{total}'
    if SndpGraph.DEBUG and (current / 1).is_integer(): # end='r' does not work in PyCharm
        print(bar_str, end='\n')
    else:
        print(bar_str, end='\r')


class _Product():
    def __init__(self, id, graph):
        self._graph = graph
        self.id = id
        self.type = SndpGraph.STR_PRODUCT_TYPE_MATERIAL
        self._plants = [] # plants where it is being manufactures

        #data cache
        self._graph._data['NrOfProducts'] += 1

    def add_plant(self, plant):
        if plant in self.get_plants():
            raise ('Plant {} is already in the list of plants of Product {}.'.format(plant.id, self.id))
        plant._graph = self._graph
        self._plants.append(plant)

    def get_plants(self):
        return self._plants[:]

    def __str__(self):
        if self.type == SndpGraph.STR_PRODUCT_TYPE_END_PRODUCT:
            return 'End Product: ' + str(self.id)
        else:
            return 'Product: ' + str(self.id)

    def __repr__(self):
        return self.__str__()


class _Location():
    def __init__(self, id, graph):
        self._graph = graph
        self.id = id
        self._products = []
        self._inbounds = [] # inbound routes
        self._outbounds = []  # outbound routes

        # data cache
        self._graph._data['NrOfLocations'] += 1

    def add_product(self, product):
        if product in self.get_products():
            raise(f'Product {product} is already produced in location {self.id}')
        assert(product._graph == self._graph)
        self._products.append(product)
        product.add_plant(self)
        if product.type == SndpGraph.STR_PRODUCT_TYPE_END_PRODUCT:
            self._graph._end_product_plants.add(self)

        # data cache
        for name in ['ScalarData', 'ShipCost', 'ArcProduct', 'arc']: # 'MaterialReq' are excluded since they cannot be modified:
            self._graph._data_valid_export[name] = None
        self.update_graph_data_cache(product)

    def get_products(self):
        return self._products[:]

    def add_inbound(self, route):
        route._graph = self._graph
        self._inbounds.append(route)

    def get_inbounds(self):
        return self._inbounds[:]

    def add_outbound(self, route):
        route._graph = self._graph
        self._outbounds.append(route)

    def get_outbounds(self):
        return self._outbounds[:]

    def update_graph_data_cache(self, product = None, route = None):
        if product is None:
            products = self.get_products()
        else:
            products = [product]
        if route is None:
            routes = self.get_outbounds()
        else:
            routes = [route]
        for product in products:
            end_location = self._graph.get_end_location()
            for route in routes:
                if product.type == SndpGraph.STR_PRODUCT_TYPE_MATERIAL and route.end == end_location:
                    continue
                new_arc_prod_key = f'{product.id},{route.start.id},{route.end.id}'
                if new_arc_prod_key not in self._graph._data['ArcProduct']:
                    self._graph._data['ArcProduct'][new_arc_prod_key] = {'product': product.id, 'start': route.start.id, 'finish': route.end.id, 'value': 1}
                    self._graph._data_txt['ArcProduct'] += f'{new_arc_prod_key},1\n'
                    new_arc_key = f'{route.start.id},{route.end.id}'
                    if new_arc_key not in self._graph._data['arc']:
                        self._graph._data['arc'][new_arc_key] = {'start': route.start.id, 'finish': route.end.id}
                        self._graph._data_txt['arc'] += f'{new_arc_key}\n'
            if product.type == SndpGraph.STR_PRODUCT_TYPE_MATERIAL and self in self._graph.get_end_product_plants():
                new_arc_prod_key = f'{product.id},{self.id},{self.id}'
                if new_arc_prod_key not in self._graph._data['ArcProduct']:
                    self._graph._data['ArcProduct'][new_arc_prod_key] = {'product': product.id, 'start': self.id, 'finish': self.id, 'value': 1}
                    self._graph._data_txt['ArcProduct'] += f'{new_arc_prod_key},1\n'
                    new_arc_key = f'{self.id},{self.id}'
                    if new_arc_key not in self._graph._data['arc']:
                        self._graph._data['arc'][new_arc_key] = {'start': self.id, 'finish': self.id}
                        self._graph._data_txt['arc'] += f'{self.id},{self.id}\n'

    def __str__(self):
        if self.get_products():
            return str(self.id) + ' Products: ' + ','.join(str(product.id) for product in self.get_products())
        else:
            return str(self.id)

    def __repr__(self):
        return 'Location: ' + self.__str__()


class _Route():
    def __init__(self, start, end, distance):
        if not isinstance(start, _Location) or not isinstance(end, _Location):
            raise('Start and end should be Location objects.')
        if start.id == end.id:
            raise('Start and end are the same location for the route.')
        self._graph = None
        self.start = start
        start.add_outbound(self)
        self.end = end
        end.add_inbound(self)
        self.distance = distance

    def __str__(self):
        return 'Route: ' + str(self.start.id) + ',' + str(self.end.id)

    def __repr__(self):
        return self.__str__()


class _Scenario():
    def __init__(self, id, probability, demand):
        self._graph = None
        self.id = id
        self.probability = probability
        self.demand = demand

    def __str__(self):
        return f'Scen: {str(self.id)} Prob: {self.probability} Demand: {self.demand}'

    def __repr__(self):
        return self.__str__()


class SndpGraph():
    # Be careful with these parameters
    FLOAT_PERCENT_OF_LOC_WITH_END_PROD = 0.5 # this amount*num locations will be number bins in the problem
    INT_MAX_PRODUCTS_IN_ONE_LOCATION = 3  # might be higher under some conditions
    INT_MAX_DISTANCE = 5 # average is 3, too high value might lead to solution value = 0 (cost > sales)

    FLOAT_INIT_SALES_PRICE = 120 # in the initial instance it was 13. Might be adjusted with adjust_sales_price
    FLOAT_PLANT_COST = 2000
    FLOAT_PLANT_CAPACITY =  5000
    # min possible scenario demand = (1-FLOAT_MAX_PERCENT_DEMAND_DEFICIT) * FLOAT_PLANT_CAPACITY * number end product plants
    # max possible scenario demand = 0.9 * FLOAT_PLANT_CAPACITY * number end product plants
    FLOAT_MAX_PERCENT_DEMAND_DEFICIT = 0.5

    STR_PRODUCT_TYPE_MATERIAL = 'STR_PRODUCT_TYPE_MATERIAL'
    STR_PRODUCT_TYPE_END_PRODUCT = 'STR_PRODUCT_TYPE_END_PRODUCT'

    INT_MIN_MULTITHREAD_LOCATION_LIMIT = 2000 # we force num_cpu to be 1 if number_locations lower this value
    INT_MAX_LOCATIONS_TO_VISUALIZE = 40 # we will not run visualize() if the number of locations exceeds this value
    DEBUG = False


    def __init__(self, name, num_locations, num_products, num_scen, random_seed = None):

        Timer('Core data generated').start()

        self.name = name
        self.dot_graph = None
        self.random_seed = random_seed
        random.seed(random_seed)

        # Initialize data cache
        self._data = {}
        self.sales_price = SndpGraph.FLOAT_INIT_SALES_PRICE
        self._data['PlantCost'] = SndpGraph.FLOAT_PLANT_COST
        self._data['PlantCapacity'] = SndpGraph.FLOAT_PLANT_CAPACITY
        self._data['NrOfLocations'] = 0
        self._data['NrOfProducts'] = 0
        self._data_valid_export = {'ScalarData': None}  # path to the .dat file that is actual for current data

        list_data_names = ['MaterialReq','Prob','Demand','ShipCost','ArcProduct','arc']
        self._data_txt = {} # textual representation for .dat files
        for name in list_data_names:
            self._data[name] = {}
            self._data_txt[name] = ''
            self._data_valid_export[name] = None

        # Initialize products
        if num_products < 2:
            raise('There should be at least two products in the SNDP problem: material and end product.')
        if num_products > 40:
            print(f'If num products > 40, the instance might be disbalanced: production too expensive and solution value 0')
        self._products = {product_id:_Product(product_id, self) for product_id in range(1, num_products + 1)}  # +1 since in MPL indexing starts from 1
        self.get_products()[-1].type = SndpGraph.STR_PRODUCT_TYPE_END_PRODUCT # last product is end product
        max_material_req = math.floor(40/(num_products)*2) # in order to have moderate production costs
        self.material_requirements = [random.randint(1, max_material_req) for material in self.get_materials()] # in the end product
        self._data['MaterialReq'] = {i: {'material': i + 1, 'value': k} for (i, k) in enumerate(self.material_requirements)}
        self._data_txt['MaterialReq'] += '\n'.join([f'{i + 1},{k}' for (i, k) in enumerate(self.material_requirements)])

        # Initialize all locations
        if num_locations < 2:
            raise('There should be at least two locations in the SNDP problem: market and another location.')
        self._locations = {location_id:_Location(location_id, self) for location_id in range(1, num_locations + 1)}

        # Nodes with end product
        self._routes = {}
        plants_for_end_products = random_subset(self.get_plants(), math.floor(num_locations * SndpGraph.FLOAT_PERCENT_OF_LOC_WITH_END_PROD)) # set it right away for efficiency
        self._end_product_plants = set()
        for plant in plants_for_end_products:
            # end product (at least) should be produced there
            route_object = _Route(plant, self.get_end_location(), random.randint(1, SndpGraph.INT_MAX_DISTANCE))
            self.add_route(route_object)
            plant.add_product(self.get_end_product())
        end_product_plants = self.get_end_product_plants()

        # Assign materials to plants and create routes
        #num_cpu = mp.cpu_count()
        num_cpu = 1 # multiprocessing does not provide any efficiency improvements
        if num_locations < SndpGraph.INT_MIN_MULTITHREAD_LOCATION_LIMIT:
            num_cpu = 1

        if num_cpu > 1: # multiprocessing
            raise NotImplementedError('We need to fill in data cache here in the same manner as for single thread case.')
            add_products = [] # will store the changes to be applied
            manager = mp.Manager()
            # normal dict will not be shared among processes but we need it to be shared
            # manager.dict() makes things much slower - maybe use Array.
            add_routes = manager.dict()
            # add_routes = {} # even if we use normal dict (makes no sense) there is no benefit in speed
            pool = mp.Pool(num_cpu)
            results = [pool.apply_async(self.generate_plant_data, args=(worker_id, add_routes, num_cpu)) for worker_id in range(num_cpu)]
            pool.close()
            pool.join()
            for result in [res.get() for res in results]:
                add_products += result

            # apply changes
            # since data is not shared among processes, .add_product() and .add_route() should not be called from generate_plant_data()
            for record in add_products:
                plant = self.get_location(record['plant'])
                material = self.get_product(record['material'])
                plant.add_product(material)
            for key, distance in add_routes.items():
                star_id = int(key.split('-')[0])
                start_location = self.get_location(star_id)
                end_id = int(key.split('-')[1])
                end_location = self.get_location(end_id)
                self.add_route(_Route(start_location, end_location, distance))
        else:
            # we do not use here generate_plant_data() because making .add_route() and .add_product() right away is much faster
            num_plants = len(self.get_plants())
            for plant in self.get_plants():
                if plant in end_product_plants:
                    min_materials = 0  # in potential plants none of the materials might be manufactured
                    max_materials = math.ceil(len(self.get_materials())/4) # to avoid that all materials are manufactured on the plant site and should not be delivered
                else:
                    min_materials = 1
                    max_materials = len(self.get_materials())
                random_num_materials = min(random.randint(min_materials, max_materials),
                                           SndpGraph.INT_MAX_PRODUCTS_IN_ONE_LOCATION)
                if random_num_materials == 0: # no materials produced, lets go to the next plant
                    continue

                # Define the route to (several or all) potential end product plants for every plant
                random_num_end_product_plants = random.randint(1, len(end_product_plants))
                random_end_product_plants = random_subset(end_product_plants, random_num_end_product_plants)
                # connect the location with the end product plants
                for end_product_plant in random_end_product_plants:
                    # we need route only if product is produced not in the potential plant locations
                    if plant.id == end_product_plant.id:
                        continue
                    # routes can be one directional, omit the route if it already exists in another direction
                    if self.get_route(end_product_plant, plant):
                        continue
                    if not self.get_route(plant, end_product_plant):  # if the route does not already exist
                        self.add_route(_Route(plant, end_product_plant, random.randint(1, SndpGraph.INT_MAX_DISTANCE)))

                # Define materials to produce
                random_materials = random_subset(self.get_materials(), random_num_materials)  # except the last one
                for material in random_materials:
                    plant.add_product(material)

                progress_bar('Generate data for plants', plant.id, num_plants)

        # Test if graph is valid and solve the issues
        # - check if plant with material has at least one route to potential plant: this is guaranteed during assignment of materials to plants
        # - check if every potential plant has all the materials delivered
        # it will also automatically solve the issue if a material has no plant, since such material will not be delivered to all plants
        for counter, end_product_plant in enumerate(end_product_plants, 1):
            # materials produced in the plant itself
            available_materials = [product for product in end_product_plant.get_products() if
                                   product.type == SndpGraph.STR_PRODUCT_TYPE_MATERIAL]
            # and materials delivered
            connected_plants = [route.start for route in end_product_plant.get_inbounds()]
            for connected_plant in connected_plants:
                available_materials += [product for product in connected_plant.get_products() if product.type == SndpGraph.STR_PRODUCT_TYPE_MATERIAL]
            materials_not_delivered_to_plant = [material for material in self.get_materials() if
                                                material not in available_materials]
            for material in materials_not_delivered_to_plant:
                # add material to the potential plant itself or connected plants
                if len(connected_plants) > 0:
                    random_plant = random_subset(connected_plants, 1)[0]
                else: # produce in plant itself if no plants are connected
                    random_plant = end_product_plant
                random_plant.add_product(material)

            progress_bar('Validate data for plants', counter, len(end_product_plants))

        str(Timer('Core data generated'))
        Timer('Core data generated').reset()

        assert (self._data['NrOfLocations'] == num_locations)
        assert (self._data['NrOfLocations'] == len(self.get_locations()))
        assert (self._data['NrOfProducts'] == num_products)
        assert (self._data['NrOfProducts'] == len(self.get_products()))

        # Stochastic data
        self._scenarios = []
        self.regenerate_stochastic_data(num_scen)

    @property
    def sales_price(self):
        return self._data['SalesPrice']

    @sales_price.setter
    def sales_price(self, value):
        self._data['SalesPrice'] = value

    @property
    def data_as_dict(self):
        result = {}
        # scalar data
        for name in ['NrOfLocations', 'NrOfProducts', 'NrOfScen', 'SalesPrice', 'PlantCost', 'PlantCapacity']:  # basically we do not need to clear it because it cannot be modified:
            result[name] = self._data[name]
        # array data
        for name in ['MaterialReq', 'Prob', 'Demand', 'ShipCost', 'ArcProduct', 'arc']:  # 'MaterialReq' are excluded since they cannot be modified:
            result[name] = list(self._data[name].values())

        return result

    def generate_plant_data(self, worker_id, shared_add_routes, num_cpu = 0):
        '''Used in multiprocessing. Generates most of the data except the stochastic data'''
        random.seed(self.random_seed * worker_id+1) # +1 to avoid 0
        if num_cpu == 0:
            num_cpu = mp.cpu_count()

        add_products = [] # result that we will return
        all_plants = self.get_plants()
        end_product_plants = self.get_end_product_plants()

        plants_per_worker = max(math.floor(len(all_plants)/num_cpu),1)
        if (worker_id*plants_per_worker) >= len(all_plants): # we have no plants for this worker
            return []
        plants_start = plants_per_worker*(worker_id-1)
        if worker_id == 0: # no previous worker
            plants_start = 0
        plants_end = plants_start + plants_per_worker
        if worker_id == num_cpu-1: # last worker might be an exception
            plants_end = len(all_plants)
        plants = all_plants[plants_start:plants_end]

        for plant in plants:
            if plant in end_product_plants:
                min_materials = 0  # in potential plants none of the materials might be manufactured
                max_materials = 1  # to avoid that all materials are manufactured on the plant site and should not be delivered
            else:
                min_materials = 1
                max_materials = len(self.get_materials())
            random_num_materials = min(random.randint(min_materials, max_materials),
                                       SndpGraph.INT_MAX_PRODUCTS_IN_ONE_LOCATION)
            if random_num_materials == 0:
                continue
            random_materials = random_subset(self.get_materials(), random_num_materials)  # except the last one
            for material in random_materials:
                #plant.add_product(material)
                add_products.append({'plant': plant.id, 'material': material.id})

            # Define the route to (several or all) potential end product plants for every plant
            random_num_end_product_plants = random.randint(1, len(end_product_plants))
            random_end_product_plants = random_subset(end_product_plants, random_num_end_product_plants)
            # connect the location with the end product plants
            for end_product_plant in random_end_product_plants:
                # we need route only if product is produced not in the potential plant locations
                if plant.id == end_product_plant.id:
                    continue
                # routes can be one directional, omit the route if it already exists in another direction
                key_opposite = '{}-{}'.format(end_product_plant.id, plant.id)
                if self._routes.get(key_opposite):
                    continue
                key = '{}-{}'.format(plant.id, end_product_plant.id)
                if not self._routes.get(key):  # if the route does not already exist
                    #self.add_route(Route(plant, end_product_plant, random.randint(1, SNDP_Graph.MAX_DISTANCE)))
                    shared_add_routes[key] = random.randint(1, SndpGraph.INT_MAX_DISTANCE)

            print(f'Data generated for plant {plant.id}')

        return add_products

    def regenerate_stochastic_data(self, num_scen):
        Timer('Stochastic data generated').start()

        self._clear_stochastic_data_cache()
        min_scenario_demand = (1-SndpGraph.FLOAT_MAX_PERCENT_DEMAND_DEFICIT) * SndpGraph.FLOAT_PLANT_CAPACITY * len(self.get_end_product_plants())
        max_scenario_demand = 0.9 * SndpGraph.FLOAT_PLANT_CAPACITY * len(self.get_end_product_plants())
        if num_scen > (max_scenario_demand - min_scenario_demand):
            raise ValueError("SndpGraph.FLOAT_MAX_PERCENT_DEMAND_DEFICIT is too small for the num_scen.")

        self._scenarios = []
        probability_per_scenario = 1 / num_scen  # we assume uniformal distribution
        demands = random.sample(range(int(min_scenario_demand), int(max_scenario_demand)), num_scen)
        for scenario_id in range(1, num_scen):  # indexing starts from 1, all scenarios except the last one
            self.add_scenario(_Scenario(scenario_id, probability_per_scenario, demands[scenario_id - 1]))

        left_probability = 1.0 - sum(scen.probability for scen in self.get_scenarios())
        assert (left_probability > 0)
        self.add_scenario(_Scenario(num_scen, left_probability, demands[num_scen - 1]))  # last scenario

        print(Timer('Stochastic data generated'))
        Timer('Stochastic data generated').reset()

        assert(self._data['NrOfScen'] == num_scen)
        assert (self._data['NrOfScen'] == len(self.get_scenarios()))

    def visualize(self, format='jpg', view=False, to_file=None):
        if len(self.get_locations()) > SndpGraph.INT_MAX_LOCATIONS_TO_VISUALIZE:
            print(f'Visualization of graph {self.name} with {len(self.get_locations())} locations will take to much time and will not be done.')
            return
        if self.dot_graph is None:
            self.dot_graph = Digraph(comment=self.name)
        # Reload all the data
        self.dot_graph.clear()
        self.dot_graph.format = format

        end_product_plants = self.get_end_product_plants()
        for location in self.get_locations():
            if location == self.get_end_location():
                color = 'red'
                style = 'filled'
            elif location in end_product_plants:
                color = 'grey'
                style = 'filled'
            else:
                color = None
                style = 'solid'
            self.dot_graph.node(name=str(location.id), label=str(location), style=style, color=color)

        for route in self.get_routes():
            self.dot_graph.edge(str(route.start.id), str(route.end.id), label = str(route.distance), len = str(route.distance))

        # print(self.dot_graph.source)
        if to_file is None:
            to_file = self.name
        try:
            self.dot_graph.render(to_file, view=view)
        except Exception as e:
            print(f"WARNING: Visulalization of {self.name} failed. Due to this error: {e}")


    def export_mpl(self, filename : str):

        # export .mpl file
        model_formulation = Path(resource_filename(__name__, 'SNDP_default.mpl')).read_text()

        # export .dat files
        # scalar
        valid_export = self._data_valid_export['ScalarData']
        if valid_export is not None:
            out_filename = str(valid_export)
        else:
            out_filename = f'{filename}_ScalarData.dat'
            dat_file = Path(resource_filename(__name__, 'SNDP_default_ScalarData.dat')).read_text()
            dat_file_lines = dat_file.split('\n')
            for data_item_name in ['NrOfLocations', 'NrOfProducts', 'NrOfScen', 'SalesPrice', 'PlantCost', 'PlantCapacity']:
                # load and modify the data from the current data file
                data_row = dat_file_lines.index('!' + data_item_name) + 1
                dat_file_lines[data_row] = str(self._data[data_item_name])
            # and write to the new file
            out_file = Path(out_filename)
            out_file.write_text('\n'.join(dat_file_lines))
            self._data_valid_export['ScalarData'] = out_file
        # update links in the model formulation
        model_formulation = model_formulation.replace(f'SNDP_default_ScalarData.dat', str(out_filename))

        # arrays
        for data_item_name in ['ShipCost', 'ArcProduct', 'arc', 'Prob', 'Demand', 'MaterialReq']:
            valid_export = self._data_valid_export[data_item_name]
            if valid_export is not None:
                out_filename = str(valid_export)
            else:
                out_filename = f'{filename}_{data_item_name}.dat'
                some_value = next(iter(self._data[data_item_name].values())) # we get dict
                keys = some_value.keys()
                first_two_lines = '!{}\n!{}\n'.format(data_item_name, ','.join(keys))
                dat_contents = first_two_lines + self._data_txt[data_item_name]
                # and write to the new file
                out_file = Path(out_filename)
                out_file.write_text(dat_contents)
                self._data_valid_export[data_item_name] = out_file
            # update links in the model formulation
            model_formulation = model_formulation.replace(f'SNDP_default_{data_item_name}.dat', str(out_filename))

        Path(filename + '.mpl').write_text(model_formulation)

    def adjust_sales_price(self):

        '''Find the smallest value of SalesPrice
        that does not decrease the number of open plants.
        Motivation: has as small obj value as possible to avoid numerical issues.'''

        try:
            from sndpgen.sndp_model import SndpModel
        except ImportError:
            warn('optconvert is not installed, adjust_sales_price() will not be executed', ImportWarning)
            return
        self.export_mpl(f'{self.name}')
        sndp_model = SndpModel(Path(f'{self.name}.mpl'))
        sndp_model.adjust_sales_price()
        self.sales_price = sndp_model.data_as_dict['SalesPrice']
        self._data_valid_export['ScalarData'] = None

    def _clear_nodes_data_cache(self):
        self._data_valid_export['ScalarData'] = None
        for name in ['NrOfLocations', 'NrOfProducts']: # basically we do not need to clear it because it cannot be modified:
            self._data[name] = 0
        for name in ['ShipCost', 'ArcProduct', 'arc']: # 'MaterialReq' are excluded since they cannot be modified:
            self._data[name] = {}
            self._data_txt[name] = ''
            self._data_valid_export[name] = None

    def _clear_stochastic_data_cache(self):
        self._data_valid_export['ScalarData'] = None
        for name in ['NrOfScen']:
            self._data[name] = 0
        for name in ['Prob', 'Demand']:
            self._data[name] = {}
            self._data_txt[name] = ''
            self._data_valid_export[name] = None

    def add_route(self, route):
        if self.get_route(route.start, route.end):
            raise KeyError('Route already exists in the graph.')
        route._graph = self
        self._routes['{}-{}'.format(route.start.id, route.end.id)] = route

        # data cache
        for name in ['ScalarData', 'ShipCost', 'ArcProduct', 'arc']: # 'MaterialReq' are excluded since they cannot be modified:
            self._data_valid_export[name] = None
        route.start.update_graph_data_cache(product = None, route = route)
        # we check for duplicates above
        new_key = f'{route.start.id},{route.end.id}'
        self._data['ShipCost'][new_key] = {'start': route.start.id, 'finish': route.end.id, 'value': route.distance}
        self._data_txt['ShipCost'] += f'{new_key},{route.distance}\n'

    def add_scenario(self, scenario):
        scenario._graph = self
        self._scenarios.append(scenario)

        # data cache
        self._data['NrOfScen'] += 1
        if scenario.id in self._data['Prob']:
            raise KeyError('Scenario already exists in the graph.')
        assert(scenario.id not in self._data['Demand'] and 'How would this happen if error obove does not raise?')
        self._data['Prob'][scenario.id] = {'SCEN': scenario.id, 'value': scenario.probability}
        self._data_txt['Prob'] += f'{scenario.id},{scenario.probability}\n'
        self._data['Demand'][scenario.id] = {'SCEN': scenario.id, 'value': scenario.demand}
        self._data_txt['Demand'] += f'{scenario.id},{scenario.demand}\n'

    def get_products(self):
        return list(self._products.values())

    def get_materials(self):
        return self.get_products()[:-1]  # all except the last products which are the end product

    def get_product(self, id):
        product = self._products.get(id)
        return product

    def get_end_product(self):
        return self.get_products()[-1]

    def get_locations(self):
        return list(self._locations.values())

    def get_plants(self):
        return self.get_locations()[:-1] # last location is end location

    def get_end_product_plants(self):
        return self._end_product_plants

    def get_location(self, id):
        location = self._locations.get(id)
        if location is None:
            raise (f'Location with {id} was not found.')
        return location

    def get_end_location(self):
        return self.get_locations()[-1]

    def get_routes(self):
        return list(self._routes.values())

    def get_route(self, start, end):
        if not isinstance(start, _Location) or not isinstance(end, _Location):
            raise('Start and end arguments should be Location objects')
        key = '{}-{}'.format(start.id, end.id)
        return self._routes.get(key)

    def get_scenarios(self):
        return self._scenarios[:]

def random_subset( iterator, K ):
    result = []
    N = 0

    for item in iterator:
        N += 1
        if len( result ) < K:
            result.append( item )
        else:
            s = int(random.random() * N)
            if s < K:
                result[ s ] = item

    return result