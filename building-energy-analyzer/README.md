# Building Energy Analyzer

**Student:** Omar Ahmed Mohamed Suleiman

## Project description

A Python application that calculates and analyzes the energy consumption of rooms in buildings.
It has two connected modules, joined by a text menu in `main.py`:

- **Module 1 - Energy Consumption Calculator** (`energy_calculator.py`)
  A `Room` class (name, building, area, lighting / air-conditioning / equipment power in kW,
  daily operating hours) with input validation. Rooms can be added, listed, searched and updated.
  It calculates the estimated daily energy per room, the total, and the consumption per square metre,
  and saves the rooms to a CSV file.
  - Daily energy (kWh) = total power (kW) x operating hours
  - Consumption per m2 = daily energy / room area

- **Module 2 - Consumption and Cost Analysis** (`analysis.py`)
  Reads the actual daily readings (room ID, date, kWh), cleans them with pandas (duplicates, missing
  values), merges them with the room data, and calculates consumption and cost per room, building and
  month for a price per kWh entered by the user. NumPy compares the estimated consumption before and
  after reducing the air-conditioning power by a chosen percentage. Matplotlib creates four charts
  (line, bar, scatter, histogram). Reports are exported as CSV and charts as PNG.

**Input validation:** area must be greater than 0, power values must be 0 or more, and operating hours
must be between 0 and 24.

## Required libraries

- Python 3.9 or newer
- pandas
- numpy
- matplotlib

Install them with:

```
pip install -r requirements.txt
```

The notebook additionally needs Jupyter (or Google Colab) to open and run it.

## How to run

1. Download or clone the repository and open a terminal in the project folder (the one containing `main.py`).
2. Install the libraries (see above).
3. Start the program:

   ```
   python main.py
   ```

4. Use the menu. A typical order is: `5` (energy report) -> `7` (run analysis, enter a price per kWh,
   for example `2.0`) -> `8` (AC reduction, e.g. `20`) -> `9` (charts) -> `10` (export reports).
   Option `11` shows one room's estimated vs actual consumption.

To run the 6 test cases (3 valid, 3 invalid):

```
python tests/test_cases.py
```

To open the analysis notebook: open `Building_Energy_Analysis.ipynb` in Jupyter or Google Colab and
run all cells. When using Colab, upload the `data`, `tests`, `energy_calculator.py` and `analysis.py` files first.

## Project structure

```
main.py                         menu that connects both modules
energy_calculator.py            Module 1 - Room class, room manager, formulas, CSV storage
analysis.py                     Module 2 - cleaning, merging, cost, NumPy scenario, charts, exports
Building_Energy_Analysis.ipynb  short analysis notebook with the test results
tests/test_cases.py             3 valid and 3 invalid test cases (expected vs actual)
data/rooms.csv                  8 rooms in 2 buildings (Admin Block, Academic Block)
data/readings.csv               daily readings for 61 days (Aug-Sep 2026)
reports/                        exported CSV reports
charts/                         exported PNG charts
requirements.txt                required libraries
```

## Data

- `data/rooms.csv`: 8 rooms in 2 buildings.
- `data/readings.csv`: 490 readings (8 rooms x 61 days, Aug 1 - Sep 30, 2026). It contains 2 duplicate
  rows and 3 missing values, which are handled during cleaning.
