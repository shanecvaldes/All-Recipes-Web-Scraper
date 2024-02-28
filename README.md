All-Recipes-Web-Scraper
A multithreaded program that scraps the website allrecipes.com, and inserts on a device's PSQL DB.

BACKGROUND:
The purpose of this project is to create a multi-threaded webscrapper that categorizes information on "realrecipes.com" and parsing/storing the information into a systems database. Currently the script scrapes recipe and category links from the website and filters then into separate tables in the database, as well as many of the relationships between pages and their titles.

HOW TO USE:
The file "web_scraper.py" can be ran in the terminal. The user is prompted with how many threads they want to begin webscraping, how many request cycles/iterations, as well as the username, password, and database name for the PSQL database on the system.

Before running the script, the "db_template.sql" file. This is the database schema expected by the program, and any changes to the schema must be accounted for the script as well. The modules BeautifulSoup, threading, psycopg2, asyncio, aiohttp, and time are used in this script, so make sure that these are installed through pip before running.

The script uses the default port number for the PSQL database, "5432". It should be possible to change these settings. To change, edit the db_connection variable information in the start function.

WARNING:
Before running, please be wary of the amount of requests being made. This program makes many requests at once, and the maximum amount of requests is defaulted to 500. To change this, the max_length variable in init_queue may be changed.

After all the iterations, the data zwithin the database will likely not be complete. Before using any of the data, please filter using the by the parent_id, as all ids with -1 are defaulted to be empty.