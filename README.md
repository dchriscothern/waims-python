# WAIMS-R Production

Production monitoring for professional basketball.

## Features

✅ Multi-source integration
✅ wehoop - 2025 WNBA data
✅ Research-validated
✅ Automated workflows

## Quick Start
```r
install.packages(c("tidyverse","duckdb","wehoop"))
source("scripts/generate_sample_data.R")
```

## License
MIT
```

Save.

---

### **Step 5: Update .gitignore**

Open `.gitignore`, add at bottom:
```

# Data files
raw/*.csv
warehouse/*.duckdb
gold_export/*.csv
logs/*.log
desktop.ini
