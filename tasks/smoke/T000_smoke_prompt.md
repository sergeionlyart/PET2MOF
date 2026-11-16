# Task T000-smoke (model availability + typical-task check)
Work only inside the current directory. Do not read files outside it. Do not use the network.
Write a Python script `humid.py` that computes, for a gas that is 5 mol% CO2 / 95 mol% N2 on a DRY basis,
at absolute pressure 1.000 bar (100.000 kPa) and 35.00 °C, for RH = 0, 40, 70 %:
water saturation pressure (state the correlation you use and cite it), p_H2O, y_H2O, wet y_CO2, wet y_N2, p_CO2 (kPa).
Run it, and write the results to `result.json` with keys "psat_kPa","correlation", and "rows" (list of dicts with
keys RH, p_H2O_kPa, y_H2O, y_CO2, y_N2, p_CO2_kPa). Also add a test `test_humid.py` (plain asserts, runnable with
`python3 test_humid.py`) checking that wet mole fractions sum to 1 and that the dry-basis CO2:N2 ratio is preserved.
In your final message, report: the model name and reasoning effort you believe you are running with, and the numbers.
