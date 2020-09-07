import math
optconvert_installed = True
try:
    from optconvert import MplWithExtData
except ModuleNotFoundError:
    optconvert_installed = False

if optconvert_installed:
    class SndpModel(MplWithExtData):
        """
        Extends the MplWithExtData class.
        Design specifically to represent the Stochastic Network Design Problem instances.

        Attributes
        ----------
        data_as_dict : dict
            returns model data in dict format. Implemented only for 'SalesPrice'. See MplWithExtData set_ext_data() for format and SndpGraph()
        solution_open_production : list
            list of OpenProduction variables names that have value 1.0 in the optimal solution, i.e., will be opened

        Methods
        -------
        adjust_sales_price
            find the smallest value of SalesPrice that does not decrease the number of open plants.
        """

        def adjust_sales_price(self):

            '''Find the smallest value of FLOAT_SALES_PRICE
            that does not change the set of open plants.
            Motivation: has as small obj value as possible to avoid numerical issues.'''

            sales_price = self.data_as_dict['SalesPrice']
            ub = sales_price
            lb = 0
            target_open_plants  = len(self.solution_open_production) # not smaller than with init. price
            step = sales_price/2
            direction = 'down'
            iter_counter = 0
            while True:
                if direction == 'up':
                    sales_price += step
                else:
                    sales_price -= step
                self.set_ext_data({'SalesPrice': sales_price})
                self.solve()
                obj_value = self.obj_value
                num_open_plants = len(self.solution_open_production)  # not smaller than with init. price
                if obj_value > 0 and num_open_plants >= target_open_plants:
                    if direction == 'up':
                        step /= 2
                        ub = sales_price
                    direction = 'down'
                else:
                    if direction == 'down':
                        step /= 2
                        lb = sales_price
                    direction = 'up'
                # check the gap
                assert(ub - lb > 0)
                iter_counter += 1
                if ub - lb <= 5:
                    self.set_ext_data({'SalesPrice': math.ceil(ub)})
                    break

        @property
        def data_as_dict(self) -> dict:
            """Overrides the method of the model class
            This method is not implemented for base class
            Implemented only for 'SalesPrice' data item

            Parameters
            ----------
            None

            Returns
            -------
            dict
                keys are the data items, values are the data values
            """
            return {'SalesPrice': self._mpl_model.DataConstants['SalesPrice'].Value}

        @property
        def solution_open_production(self):
            open_production = []
            for variable, value in self.solution.items():
                if 'OpenProd' in variable and value == 1.0:
                    open_production.append(variable)
            return open_production