# File upload
In this section is described how the HDF5-file (*.h5) is structured and how the specific fields are formatted to upload it on the ABD-Website.
## Basic structure
The HDF5-file should be hierarchically structured as following:
```
BatteryTable/
│   └─ data
└─── Dataset/
     │   └─ data
     ├─── CellTest0/
     │    │   └─ data
     │    ├─── CyclingRawData/
     │    │     └─ data
     │    └─── ErrorCodes
     │          └─ data
     ├─── CellTest1/
     │    │   └─ data
     │    ├─── CyclingRawData/
     │    │     └─ data
     │    └─── ErrorCodes/
     │          └─ data
     ├─── CellTest2/
     │    │   └─ data
     │    ├─── EISRawData/
     │    │     └─ data
     │    └─── ErrorCodes/
     │          └─ data
     ├───...
```
## Data structure
In this section is explained what the required and additional(_italic_) fields and it's datatypes are per data and for special fields(marked with *) the field format as subcategory in the document.
### BatteryTable-data
| chemical_type_cathode | _cathode_proportions_ | _chemical_type_anode_ | _anode_proportions_ | format  | format_type | specific_type | manufacturer | weight | _nominal_voltage_ | max_voltage | min_voltage | theoretical_capacity | _comments_ |
|-----------------------|-----------------------|-----------------------|---------------------|---------|-------------|---------------|--------------|--------|-------------------|-------------|-------------|----------------------|------------|
| string                | string*               | string                | string*             | string* | string*     | string        | string       | float  | float             | float       | float       | float                | string     |

#### Field formats
##### cathode/anode_proportions:
The proportions can only be set if the respective chemical-type is specified.  
The format for chemical-types that are not blends would be: **xx:yy:zz** where xx+yy+zz = 100% (+-1%). Preferable with double digit units and as much parts as diffrent chemicals are used.  
For blends the same rule as above counts but the proportions between the blends are deliminited by an underscore (_): **X**&#95;xx:yy:zz&#95;**Y**&#95;xx:yy:zz where X+Y = 100% (+-1%). For readability only one digit units are prefered but double digit units also work.
###### Example:
| simple   | blends                      |
|----------|-----------------------------|
| 5:5      | 5_3:3:3_5_4:4:2             |
| 33:33:33 | 75_5:5_25_33:33:33          |
| 3:3:3    | 33_4:2:4_33_20:35:45_33_8:2 |
| 25:50:25 | ...                         |
| 2:2:2:4  | ...                         |
##### format / format_type:
There are 4 diffrent format types to choose from:
- cylindrical
- pouch
- prismatic
- blade

It is necessary to identify the correct format.

For the format, if there is no clear name then the dimensions are used as the name.  
For the **cylindrical** are most of the time no clear name available so it is written in **diamter** x **height** without any delimiter.  
For the **pouch** and **blade** are also no clear name for the most of time so the dimensions are the name itself, written as **length** x **width** x **height** with the multiplication-star(&#42;)  
For the **prismatic** are often clear names available. The dimensions are only set in the database. If there is no clear name the same format as the pouch and blade are used: **length** x **width** x **height** with the multiplication-star(&#42;)
Examples are bellow.

| cylindrical | pouch                | prismatic | blade                |
|-------------|----------------------|-----------|----------------------|
| 18650       | 574&#42;118&#42;13.5 | BEV1      | 574&#42;118&#42;13.5 |
| 21700       |                      | PHEV1     | 905&#42;118&#42;13.5 |
| 46800       |                      | HEV       |                      |

### Dataset-data
| name   | organisation | doi     | license | url     | authors | _owner_ |
|--------|--------------|---------|--------|---------|---------|---------|
| string | string       | string* | string | string* | string  | string  |
#### Field formats
##### doi / url:
These fields are all links 

### CellTest-data
| date    | _equipment_ |
|---------|-------------|
| string* | string      |
#### Field formats
##### date:
The date is a string in the format **YYYY-MM-DD**

### CyclingRawData-data
| time_in_step | voltage | current | cycle_id | timestamp_utc | step_flag | capacity | energy | _cell_temperature_ | _ambient_temperature_ |
|--------------|---------|---------|----------|---------------|-----------|----------|--------|--------------------|-----------------------|
| float*       | float   | float   | int      | datetime*     | int*      | float    | float  | float              | float                 |
#### Field formats
##### time-in-step:
floating number representing seconds.
##### timestamp_utc:
datetime in UTC **YYYY-MM-DD hh:mm:ss.xxxxxx** where the miliseconds are only represented if given and more digits if value is given.
##### step_flag:
Integer according to enum:
```
failure = 0
OCV = 1
cc_charge = 2
cv_charge = 3
cc_discharge = 4
hppc_test = 5
hppc_discharge = 6
EIS = 7
cv_discharge = 8
rest = 9
```
### EISRawData-data
**TBD**
### ErrorCodes-data
| _cycle_id_ | _error_     |
|------------|-------------|
| int        | Array[int]* |

Data is always implemented even if empty. Entry is for cycle with error(s) that were detected during cleanup.
#### Field formats
##### error:
Errorcodes as an array of integers according to enum:
```
missing_cycle: int = 1  # missing cycle(s) in data
utc_gap: int = 2  # str = gap in utc bigger than threshold
no_real_cycle: int = 3  # a cycle with only one entry (no real cycle)
cycle_deleted: int = 4  # code written to next cycle
jump_in_time: int = 5  # deleted cycle

```
## Prequisites
In the current version some error handling is provided. That means there are some prequisites before uploading data.
- All the foreign keys have to be created first.
    - Battery Format


  
While for these models exist no matching entries for the uploaded Battery, there will nothing be saved and an error message will appear.  
As part of the prequisites some initial Data regarding the Chemical-Type and Battery-Format is provided to minimize errors and smoothen up the process.  
ChemicalType and Supplier will be automatically created if atleast a name is given.
## Debugging
If during the file-upload errors occur they will be logged. The server-admin can view the logfiles directly on the file-system.  
**TO BE DEVELOPED:** Logfiles are viewable online filtered by user and custom filters for log-level. 
