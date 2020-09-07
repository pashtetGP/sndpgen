TITLE
	SNDP_10_5_0_1

STOCHASTIC

DATA
	NrOfScen := DATAFILE("10_5_0_1_ScalarData.dat");
	NrOfLocations := DATAFILE("10_5_0_1_ScalarData.dat"); !last location is a final location (market)
	Market := NrOfLocations; !last location is a final location (market)
	NrOfProducts := DATAFILE("10_5_0_1_ScalarData.dat");
	EndProduct := NrOfProducts;	!last product is the end product
	SalesPrice := DATAFILE("10_5_0_1_ScalarData.dat");
	PlantCost := DATAFILE("10_5_0_1_ScalarData.dat");
	PlantCapacity := DATAFILE("10_5_0_1_ScalarData.dat");

SCENARIO
	SCEN := 1..NrOfScen;

PROBABILITIES
	Prob[SCEN] := SPARSEFILE("10_5_0_1_Prob.dat");

RANDOM DATA
	Demand[SCEN] := SPARSEFILE("10_5_0_1_Demand.dat");

INDEX
	location := 1..NrOfLocations;
	start := location;
	finish := location;
	product := 1..NrOfProducts;
	material[product] WHERE (product <> EndProduct);
	arc[start, finish]:= INDEXFILE("10_5_0_1_arc.dat");
	
DATA
	ShipCost[start, finish]:= SPARSEFILE("10_5_0_1_ShipCost.dat");
	ArcProduct[product, start, finish] := SPARSEFILE("10_5_0_1_ArcProduct.dat");
	MaterialReq[material] := SPARSEFILE("10_5_0_1_MaterialReq.dat");

INDEX
	plantLocation[location] WHERE (ArcProduct[product:=EndProduct, start:=location, finish:=Market] = 1);

STAGE1 BINARY VARIABLES
	OpenProduction[plantLocation];

STAGE2 VARIABLES
	Ship[product, start, finish] WHERE (ArcProduct[product, start, finish] = 1);

MACROS
	TotalRevenue := SUM(start:  SalesPrice * Ship[product:=EndProduct, start, finish:=Market]);
	FixedCost := SUM(plantLocation: PlantCost * OpenProduction);
	TotalShipCost := SUM(product,start,finish: ShipCost * Ship);

MAX
	Profit = TotalRevenue - FixedCost - TotalShipCost;

SUBJECT TO
	BOMConstr[plantLocation, material]:
		MaterialReq[material] * Ship[product:=EndProduct, start:=plantLocation, finish:=Market] = SUM(start: Ship[product:=material, start, finish:=plantLocation]);
	
	DemandConstr -> DemConstr: SUM(start: Ship[product:=EndProduct,start,finish:=Market]) <= Demand;
	
	PlantConstr[plantLocation]:
		Ship[product:=EndProduct, start:=plantLocation, finish:=Market] <= PlantCapacity * OpenProduction[plantLocation];

	