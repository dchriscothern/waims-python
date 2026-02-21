\# WAIMS Python - Athlete Monitoring Demo



SQLite database with 1,600+ integrated monitoring data points.



\## 🎯 Quick Demo

```python

import sqlite3

import pandas as pd



conn = sqlite3.connect('waims\_demo.db')



\# Show players

players = pd.read\_sql\_query('SELECT \* FROM players', conn)

print(players)

```



\## 📊 Database



\*\*6 tables, 1,637 data points:\*\*

\- players: 12 athletes

\- wellness: 600 records

\- training\_load: 600 sessions

\- acwr: 348 calculations

\- force\_plate: 84 tests

\- injuries: 5 events



\## 🔧 Setup

```bash

pip install -r requirements.txt

python generate\_database.py  # Regenerate

```



\## License

MIT

