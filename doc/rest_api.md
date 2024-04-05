# Description of the ABD REST API

## Authentication
The API uses session based authentication.
### Login
Login is done by sending a POST request to the login url with the username and password as data.  
If the credentials are correct, a session is created and the user is logged in.
- **url**: /login/
- **method**: POST
- **data**:
    ```json
    {
      "username": "username",
      "password": "password"
    }
    ``` 
### Logout
Logout is done by sending a POST request to the logout url.
- **url**: /logout/
- **method**: POST

### Users Detail
Interface to the user table/object. Session authentication is required.
### GET overview of current user
- **url**: /user/
- **method**: GET

## Batteries 
Interface to the battery table/object.
###  GET list of all batteries
- **url**: database/api/batteries/

Returns a list of batteries, where each item in the list is represented with
key-value pairs. Following keys are returned for per battery:
- **url**: API url to detail view of that battery
- **id**: primary key
- **name**
- **battery_type**: API url to battery type
- **battery_type_id**: battery_type primary key
- **weight**
- **vnom**: Nominal voltage (V)
- **vmax**: Upper cut-off voltage (V)
- **vmin**: Lower cut-off voltage (V),
- **comments**
- **cell_test**: List of cell tests linked to that battery (primary keys)

### GET one battery
- **url**: database/api/batteries/<int:pk>/
  - <int:pk>: primary key as integer

### Create new battery
NOT FUNCTIONAL YET!!

POST request on:
- **url**: database/api/batteries/
- data
    ```json
    {
      "vmin": null,
      
    }
     ````
  
## Cell tests
A battery may have several tests assigned to it.

### GET list of cell tests
- **url**: database/api/cell_tests/

Returns list of all cell tests (for all batteries)

### GET one cell test
- **url**: database/api/cell_tests/<int:pk>/
  - <int:pk>: primary key as integer

## Aggregated cycling data (AggData)

### Get list of aggregate cycles
Aggregated cycle data for  one battery can be retrieved with:
- **url**: database/api/cycles?battery=<int:battery_pk>&cell_tests=<int:pk_1>, <int:pk_2>, ...
- **query_params**:
  - battery: Primary key of battery for which to retrieve data.
  - cell_tests (_optional_): Comma separated list of cell test primary keys. 
    If not specified all aggregated cycling data for the battery will be returned

Data is returned in the following format:
````json
{
  "fields": ["list of names"],
  "data": [["array of values"]]
}
````
Request without the "battery"-filter is not accepted and returns an exception. 
Following fields are returned:
- **id** (int): Primary key off agg_data row
- **cycling_test_id** (int): Primary key of related cell test
- **cycle_id** (int): Cycle number (normally monotonically increasing)
- **charge_capacity** (real): Charge capacity in Ah
- **discharge_capacity** (real): Discharge capacity in Ah
- **efficiency** (real): Ratio between charge and discharge capacity
- **charge_c_rate** (real): C-rate during charge step
- **discharge_c_rate** (real): C-rate during discharge step
- **ambient_temperature** (real): Average ambient temperature during cycle
- **error_codes**
### Get aggregated data of one cycle
- **url**: database/api/cycles/<int:cycle_pk>/
  - <int:cycle_pk>: Primary key of cycle to retrieve

Data is returned as key-value pairs in json format.

# Raw cycling data
As for aggregated data, retrieving all raw data at once is not supported. 
As well, editing and creating entries is not supported yet.
For GET requests following url serves as base:
- base-url = database/api/cycling_rawdata

Data is returned in the following format:
````json
{
  "fields": ["list of names"],
  "data": [["array of values"]]
}
````
## Filter options
- battery: primary key of battery, returns all raw data for one battery. 
  - Example: database/api/cycling_rawdata?battery=2
- cycles: list of primary cycle (agg_data) primary keys. Can not be combined with battery filter!
  - Example: database/api/cycling_rawdata?cycles=2,5,7,10
- fields: list of field names to retrieve. If not specified following fields are retrieved:
  ````python
  fields = ["id", "time", "voltage", "current", "capacity", "energy", "agg_data_id", "cycle_id", 
            "step_flag", "time_in_step", "cell_temperature", "ambient_temperature"]
  ````
  Can be combined with battery and cycles filter.
  - Example: database/api/cycling_rawdata?cycles=2,5,7,10&fields=voltage,current

CAUTION: Even for one battery the raw data can be easily >500k rows!! 
So, testing the API in the browser is not advisable, since rendering the output can be slow. 
(Request for approx. 500 rows x 12 fields takes roughly 10 seconds with python requests package)

## Fields
- **id**: Primary key of the raw data row
- **time**: Time zone localized timestamp
- **voltage**: Voltage (V)
- **current**: Current (A)
- **capacity**: Cumulative capacity for charge/discharge (Ah)
- **energy**: Cumulative energy for charge/discharge (Wh)
- **agg_data_id**: Primary key of related agg_data row
- **cycle_id**
- **step_flage**: Indicator of step in test profile: 0 = failure, 1 = OCV, 2 = cc_charge, 3 = cv_charge, 
4 = cc_discharge, 5 = cv_discharge
- **time_in_step**: Time passed (s) since current step was started
- **cell_temperature**: Temperature on cell surface (°C)
- **ambient_temperature**: Ambient temperature (°C)