import pandas as pd

#point at one raw excel file
file = "European/2014/E coli/number-e-coli-isolates-and-percentage-resistant-fluoroquinolones-2011-2014.xlsx"

# Read it with NO assumptions about headers, so we see the raw layout
df = pd.read_excel(file, header=None)

# Show the first 8 rows
print(df.head(8))