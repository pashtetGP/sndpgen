import random
import math
import time
from graphviz import Digraph
import multiprocessing as mp
import math


class _Product():
    def __init__(self, id, graph):
        self._graph = graph
        self.id = id
        self.type = SndpGraph.STR_PRODUCT_TYPE_MATERIAL
        self._plants = [] # plants where it is being manufactures

    def add_plant(self, plant):
        if plant in self.get_plants():
            raise ('Plant {} is already in the list of plants of Product {}.'.format(plant.id, self.id))
        plant._graph = self._graph
        self._graph._clear_nodes_data_cache()
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

    def add_product(self, product):
        if product in self.get_products():
            raise(f'Product {product} is already produced in location {self.id}')
        product._graph = self._graph
        self._graph._clear_nodes_data_cache()
        self._products.append(product)
        product.add_plant(self)

    def get_products(self):
        return self._products[:]

    def add_inbound(self, route):
        route._graph = self._graph
        self._graph._clear_nodes_data_cache()
        self._inbounds.append(route)

    def get_inbounds(self):
        return self._inbounds[:]

    def add_outbound(self, route):
        route._graph = self._graph
        self._graph._clear_nodes_data_cache()
        self._outbounds.append(route)

    def get_outbounds(self):
        return self._outbounds[:]

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
    FLOAT_MIN_SCENARIO_DEMAND = 1000
    FLOAT_MAX_SCENARIO_DEMAND = 20000

    FLOAT_SALES_PRICE = 120 # in the initial instance it was 13
    FLOAT_PLANT_COST = 2000
    FLOAT_PLANT_CAPACITY =  5000

    STR_PRODUCT_TYPE_MATERIAL = 'STR_PRODUCT_TYPE_MATERIAL'
    STR_PRODUCT_TYPE_END_PRODUCT = 'STR_PRODUCT_TYPE_END_PRODUCT'

    INT_MIN_MULTITHREAD_LOCATION_LIMIT = 2000 # we force num_cpu to be 1 if number_locations lower this value
    INT_MAX_LOCATIONS_TO_VISUALIZE = 40 # we will not run visualize() if the number of locations exceeds this value
    INT_MIN_ITEMS_LOGGING = 250 # we provide completion long for some loops iterator of which has at least these number of itmes


    def __init__(self, name, num_locations, num_products, num_scen, random_seed = None):

        start = time.time()

        self.name = name
        self.random_seed = random_seed
        random.seed(random_seed)

        # Initialize data cache
        scalar_data_names = ['NrOfLocations','NrOfProducts','NrOfScen']
        list_data_names = ['MaterialReq','Prob','Demand','ShipCost','ArcProduct','arc']
        self._data = {name:None for name in scalar_data_names}
        for name in list_data_names:
            self._data[name] = []
        self._nodes_cache_cleared_ = True
        self._stochastic_data_cache_cleared_ = True

        # Initialize products
        if num_products < 2:
            raise('There should be at least two products in the SNDP problem: material and end product.')
        if num_products > 40:
            print(f'If num products > 40, the instance might be disbalanced: production too expensive and solution value 0')
        self._products_ = {product_id:_Product(product_id, self) for product_id in range(1, num_products + 1)}  # +1 since in MPL indexing starts from 1
        self.get_products()[-1].type = SndpGraph.STR_PRODUCT_TYPE_END_PRODUCT # last product is end product
        max_material_req = math.floor(40/(num_products)*2) # in order to have moderate production costs
        self.material_requirements = [random.randint(1, max_material_req) for material in self.get_materials()] # in the end product
        self.dot_graph = None

        # Initialize all locations
        if num_locations < 2:
            raise('There should be at least two locations in the SNDP problem: market and another location.')
        self._locations_ = {location_id:_Location(location_id, self) for location_id in range(1, num_locations + 1)}

        # Nodes with end product
        self._routes_ = {}
        plants_with_end_prod = random_subset(self.get_plants(), math.floor(num_locations * SndpGraph.FLOAT_PERCENT_OF_LOC_WITH_END_PROD))
        for plant in plants_with_end_prod:
            # end product (at least) should be produced there
            plant.add_product(self.get_end_product())
            route_object = _Route(plant, self.get_end_location(), random.randint(1, SndpGraph.INT_MAX_DISTANCE))
            self.add_route(route_object)

        # Assign materials to plants and create routes
        #num_cpu = mp.cpu_count()
        num_cpu = 1 # multiprocessing does not provide any efficiency improvements
        if num_locations < SndpGraph.INT_MIN_MULTITHREAD_LOCATION_LIMIT:
            num_cpu = 1

        end_product_plants = self.get_end_product_plants()
        if num_cpu > 1: # multiprocessing
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
                if random_num_materials == 0:
                    continue
                random_materials = random_subset(self.get_materials(), random_num_materials)  # except the last one
                for material in random_materials:
                    plant.add_product(material)

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

                if num_plants > SndpGraph.INT_MIN_ITEMS_LOGGING:
                    print(f'Data generated for plant {plant.id}/{num_plants}')

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

            if len(end_product_plants) > SndpGraph.INT_MIN_ITEMS_LOGGING:
                print(f'Data validated for plant {counter}/{len(end_product_plants)}')

        end = time.time()
        print('{0} SNDP graph info generated for {1:0.3f} sec.'.format(self.name, end - start))

        # Stochastic data
        self._scenarios_ = []
        self.regenerate_stochastic_data(num_scen)

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
                if self._routes_.get(key_opposite):
                    continue
                key = '{}-{}'.format(plant.id, end_product_plant.id)
                if not self._routes_.get(key):  # if the route does not already exist
                    #self.add_route(Route(plant, end_product_plant, random.randint(1, SNDP_Graph.MAX_DISTANCE)))
                    shared_add_routes[key] = random.randint(1, SndpGraph.INT_MAX_DISTANCE)

            print(f'Data generated for plant {plant.id}')

        return add_products

    def regenerate_stochastic_data(self, num_scen):
        start = time.time()
        if num_scen > (SndpGraph.FLOAT_MAX_SCENARIO_DEMAND - SndpGraph.FLOAT_MIN_SCENARIO_DEMAND):
            raise ValueError("SNDP_Graph.FLOAT_MAX_SCENARIO_DEMAND is too small for the num_scen.")

        self._scenarios_ = []
        probability_per_scenario = 1 / num_scen  # we assume uniformal distribution
        demands = random.sample(range(SndpGraph.FLOAT_MIN_SCENARIO_DEMAND, SndpGraph.FLOAT_MAX_SCENARIO_DEMAND), num_scen)
        for scenario_id in range(1, num_scen):  # indexing starts from 1, all scenarios except the last one
            self.add_scenario(_Scenario(scenario_id, probability_per_scenario, demands[scenario_id - 1]))

        left_probability = 1.0 - sum(scen.probability for scen in self.get_scenarios())
        assert (left_probability > 0)
        self.add_scenario(_Scenario(num_scen, left_probability, demands[num_scen - 1]))  # last scenario
        end = time.time()

        print('{0} SNDP stochastic data generated for {1:0.3f} sec.'.format(self.name, end - start))

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
        self.dot_graph.render(to_file, view=view)

    def data_as_dict(self):
        data = self._data

        # Consts from class variables
        data['SalesPrice'] = SndpGraph.FLOAT_SALES_PRICE
        data['PlantCost'] = SndpGraph.FLOAT_PLANT_COST
        data['PlantCapacity'] = SndpGraph.FLOAT_PLANT_CAPACITY

        if data['NrOfLocations'] is None: # never filled or was cleared
            data['NrOfLocations'] = len(self.get_locations())
        if data['NrOfProducts'] is None:
            data['NrOfProducts'] = len(self.get_products())
        if data['MaterialReq'] == []:
            data['MaterialReq'] = [{'material': i + 1, 'value': k} for (i, k) in enumerate(self.material_requirements)]

        if data['ShipCost'] == []:
            assert(data['ArcProduct'] == [] and data['arc'] == [] and "ShipCost, ArcProduct and arc should be cleared together")
            ShipCost_value = []
            ArcProduct_value = [] # product, start, finish, 1
            arc_value_set = set() # values should be distinct
            end_product = self.get_end_product()
            routes = self.get_routes()
            for counter, route in enumerate(routes, 1):
                ShipCost_value.append({'start': route.start.id, 'finish': route.end.id, 'value': route.distance})
                # let us look at the routes and products delivered on them
                for product in route.start.get_products():
                    if product != end_product and route.end == self.get_end_location():
                        continue
                    ArcProduct_value.append({'product': product.id, 'start': route.start.id, 'finish': route.end.id, 'value': 1})
                    arc_value_set.add(f'{route.start.id},{route.end.id}')

                if len(routes) > SndpGraph.INT_MIN_ITEMS_LOGGING:
                    print(f'Data transformed to dict for route {counter}/{len(routes)}')

            data['ShipCost'] = ShipCost_value

            # arcs for production
            end_product_plants = self.get_end_product_plants()
            for counter, location in enumerate(end_product_plants, 1):
                for product in location.get_products():
                    # ship 344 should be only if 4 is the end product plant
                    if product == end_product:
                        continue
                    ArcProduct_value.append({'product': product.id, 'start': location.id, 'finish': location.id, 'value': 1})
                    arc_value_set.add(f'{location.id},{location.id}')

                if len(end_product_plants) > SndpGraph.INT_MIN_ITEMS_LOGGING:
                    print(f'Data transformed to dict for prouction arc {counter}/{len(end_product_plants)}')

            data['ArcProduct'] = ArcProduct_value

            # decode arc value
            arc_value = []
            for element in arc_value_set:
                arc_value.append({'start': element.split(',')[0], 'finish': element.split(',')[1]})
            data['arc'] = arc_value

        # stochastic data
        if data['NrOfScen'] is None:
            assert(data['Prob'] == [] and data['Demand'] == [] and "NrOfScen, Prob and Demand should be cleared together")
            scenarios = self.get_scenarios()
            data['NrOfScen'] = len(scenarios)
            data['Prob'] = [{'SCEN': scen.id, 'value': scen.probability} for scen in scenarios]
            data['Demand'] = [{'SCEN': scen.id, 'value': scen.demand} for scen in scenarios]

        self._nodes_cache_cleared_ = False
        self._stochastic_data_cache_cleared_ = False

        return data

    def _clear_nodes_data_cache(self):
        if not self._nodes_cache_cleared_:
            for name in ['NrOfLocations', 'NrOfProducts']: # basically we do not need to clear it because it cannot be modified:
                self._data[name] = None
            for name in ['ShipCost', 'ArcProduct', 'arc']: # 'MaterialReq' are excluded since they cannot be modified:
                self._data[name] = []
            self._nodes_cache_cleared_ = True

    def _clear_stochastic_data_cache(self):
        if not self._stochastic_data_cache_cleared_:
            for name in ['NrOfScen']:
                self._data[name] = None
            for name in ['Prob', 'Demand']:
                self._data[name] = []
            self._stochastic_data_cache_cleared_ = True

    def add_route(self, route):
        if self.get_route(route.start, route.end):
            raise ('Route already exists in the graph.')
        self._clear_nodes_data_cache()
        route._graph = self
        self._routes_['{}-{}'.format(route.start.id, route.end.id)] = route

    def add_scenario(self, scenario):
        self._clear_stochastic_data_cache()
        scenario._graph = self
        self._scenarios_.append(scenario)

    def get_products(self):
        return list(self._products_.values())

    def get_materials(self):
        return self.get_products()[:-1]  # all except the last products which are the end product

    def get_product(self, id):
        product = self._products_.get(id)
        if product is None:
            raise (f'Product with {id} was not found.')
        return product

    def get_end_product(self):
        return self.get_products()[-1]

    def get_locations(self):
        return list(self._locations_.values())

    def get_plants(self):
        return self.get_locations()[:-1] # last location is end location

    def get_end_product_plants(self):
        return [plant for plant in self.get_end_product().get_plants()]

    def get_location(self, id):
        location = self._locations_.get(id)
        if location is None:
            raise (f'Location with {id} was not found.')
        return location

    def get_end_location(self):
        return self.get_locations()[-1]

    def get_routes(self):
        return list(self._routes_.values())

    def get_route(self, start, end):
        if not isinstance(start, _Location) or not isinstance(end, _Location):
            raise('Start and end arguments should be Location objects')
        key = '{}-{}'.format(start.id, end.id)
        return self._routes_.get(key)

    def get_scenarios(self):
        return self._scenarios_[:]

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