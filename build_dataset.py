import pandas as pd
import warnings
warnings.filterwarnings("ignore")
import glob   # finds files matching a pattern
import os     # handles file paths

# ---------- LOOKUP TABLES (bacterium & antibiotic name normalization) ----------
BACTERIA = {
    "e-coli": "Escherichia coli", "e coli": "Escherichia coli", "3gcrec": "Escherichia coli",
    "k-pneumoniae": "Klebsiella pneumoniae", "k pneumoniae": "Klebsiella pneumoniae",
    "klebsiella": "Klebsiella pneumoniae", "3gcrkp": "Klebsiella pneumoniae",
    "p-aeruginosa": "Pseudomonas aeruginosa", "p aeruginosa": "Pseudomonas aeruginosa",
    "pseudomonas": "Pseudomonas aeruginosa",
    "s-aureus": "Staphylococcus aureus", "s aureus": "Staphylococcus aureus",
    "staphylococcus": "Staphylococcus aureus",
    "s-pneumoniae": "Streptococcus pneumoniae", "s pneumoniae": "Streptococcus pneumoniae",
    "streptococcus": "Streptococcus pneumoniae",
    "acinetobacter": "Acinetobacter spp.",
    "e-faecalis": "Enterococcus faecalis", "e faecalis": "Enterococcus faecalis",
    "e-faecium": "Enterococcus faecium", "e faecium": "Enterococcus faecium",
    "enterococc": "Enterococcus spp.",
}

ANTIBIOTICS = {
    "combined-resistance": "Combined resistance", "combined resistance": "Combined resistance",
    "3-gen-cephalosporins": "3rd-gen cephalosporins", "cephalosporins": "3rd-gen cephalosporins",
    "esbl": "3rd-gen cephalosporins",
    "fluoroquinolones": "Fluoroquinolones", "carbapenems": "Carbapenems",
    "high-level-resistance-aminoglycosides": "Aminoglycosides (HLR)",
    "aminoglycosides": "Aminoglycosides",
    "aminopenicilins": "Aminopenicillins", "aminopenicillins": "Aminopenicillins",
    "piperacillin-tazobactam": "Piperacillin-tazobactam", "piperacillin": "Piperacillin",
    "ceftazidime": "Ceftazidime", "vancomycin": "Vancomycin",
    "meticilin": "Methicillin (MRSA)", "meticillin": "Methicillin (MRSA)",
    "methicillin": "Methicillin (MRSA)",
    "macrolides": "Macrolides", "penicillin": "Penicillin",
}

# The official EU/EEA countries that report to EARS-Net.
# Any row whose 'country' is not in this set is a footnote/aggregate and is dropped.
VALID_COUNTRIES = {
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Iceland", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta",
    "Netherlands", "Norway", "Poland", "Portugal", "Romania", "Slovakia",
    "Slovenia", "Spain", "Sweden", "United Kingdom",
}

def find_in_path(path, mapping):
    text = path.lower()
    for keyword, clean_name in mapping.items():
        if keyword in text:
            return clean_name
    return None

# ---------- RESHAPE ONE FILE (wide -> long) ----------
def process_file(file):
    """Read one multi-year N/%R file and return a list of tidy records."""
    raw = pd.read_excel(file, header=None)
    bacterium  = find_in_path(file, BACTERIA)
    antibiotic = find_in_path(file, ANTIBIOTICS)

    # If we can't identify the bug or drug, skip this file
    if bacterium is None or antibiotic is None:
        return []

    # Find the year-header row: scan the first 8 rows for one with 2+ years
    year_row_index = None
    for i in range(min(8, len(raw))):
        years_found = [v for v in raw.iloc[i]
                       if pd.notna(v) and isinstance(v, (int, float)) and 2009 <= v <= 2016]
        if len(years_found) >= 2:
            year_row_index = i
            break
    if year_row_index is None:
        return []   # no year row -> not a multi-year table, skip

    # Map column position -> year
    year_columns = {}
    for col_position, value in enumerate(raw.iloc[year_row_index]):
        if pd.notna(value) and isinstance(value, (int, float)) and 2009 <= value <= 2016:
            year_columns[col_position] = int(value)

    # Data rows start 2 rows below the year row (year row, then header row, then data)
    data_start = year_row_index + 2

    records = []
    for row_index in range(data_start, len(raw)):
        country = raw.iat[row_index, 0]
        if not isinstance(country, str) or len(country.strip()) < 3:
            continue
        for col_position, year in year_columns.items():
            if col_position - 1 < 1:
                continue
            n_isolates    = raw.iat[row_index, col_position - 1]
            pct_resistant = raw.iat[row_index, col_position]
            records.append({
                "country": country.strip(),
                "year": year,
                "bacterium": bacterium,
                "antibiotic": antibiotic,
                "n_isolates": pd.to_numeric(n_isolates, errors="coerce"),
                "pct_resistant": pd.to_numeric(pct_resistant, errors="coerce"),
            })
    return records

# ---------- MAIN: walk all 2013 & 2014 files ----------
all_records = []

files_2013 = glob.glob("European/2013/**/*.xlsx", recursive=True)
files_2014 = glob.glob("European/2014/**/*.xlsx", recursive=True)
all_files = files_2013 + files_2014

print(f"Found {len(all_files)} Excel files to process.")

for file in all_files:
    fname = os.path.basename(file).lower()
    # Only the "number-..." files carry BOTH N and %R across years; skip the rest
    if not fname.startswith("number"):
        continue
    records = process_file(file)
    all_records += records

tidy = pd.DataFrame(all_records)

# Clean the country field, then keep ONLY real reporting countries
tidy["country"] = tidy["country"].str.strip()          # remove stray spaces
before = len(tidy)
tidy = tidy[tidy["country"].isin(VALID_COUNTRIES)]      # drop footnotes & EU/EEA aggregates
after = len(tidy)
print(f"Dropped {before - after} junk/footnote/aggregate rows.")
print("\nTotal rows collected:", len(tidy))
print("Countries:", tidy['country'].nunique())
print("Bacteria:", tidy['bacterium'].unique())
print("Antibiotics:", tidy['antibiotic'].unique())
print("Years:", sorted(tidy['year'].unique()))
print("\nSample:")
print(tidy.head(10))

# ---------- FINAL CLEANUP & SAVE ----------
# Remove exact duplicate rows (same country/year/bacterium/antibiotic)
before = len(tidy)
tidy = tidy.drop_duplicates(subset=["country", "year", "bacterium", "antibiotic"])
print(f"Removed {before - len(tidy)} duplicate rows.")

# Sort for readability
tidy = tidy.sort_values(["bacterium", "antibiotic", "country", "year"]).reset_index(drop=True)

# Save to the raw data folder
import os
os.makedirs("data/raw", exist_ok=True)
output_path = "data/raw/ears_net.csv"
tidy.to_csv(output_path, index=False)

print(f"\nSaved {len(tidy)} rows to {output_path}")
print("Final columns:", list(tidy.columns))
print(tidy.head(10))