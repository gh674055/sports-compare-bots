import datetime
import json
print("Importing CPI")
import cpi
print("Updating CPI")
cpi.update()
print("Done Importing CPI")

start_year = 1913
end_year = datetime.date.today().year

def main():
    """The main function."""

    cpis = {}
    for year in range(start_year, end_year + 1):
        total_year_cpi = 0
        total_year_months = 0
        for i in range(1, 13):
            try:
                total_year_cpi += cpi.get(datetime.date(year, i, 1))
                total_year_months += 1
            except Exception:
                pass
        
        if total_year_months:
            cpis[str(year)] = {
                "total_cpi" : total_year_cpi,
                "total_months" : total_year_months
            }
    
    with open("cpis.json", "w") as file:
        file.write(json.dumps(cpis, indent=4, sort_keys=True))
    
if __name__ == "__main__":
    main()