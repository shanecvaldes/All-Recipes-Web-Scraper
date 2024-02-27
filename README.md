# All-Recipes-Web-Scraper
A multithreaded program that scraps the website allrecipes.com, and inserts on a device's PSQL DB.

After all the iterations, the data zwithin the database will likely not be complete. Before using any of the data, please filter using the by the parent_id, as all ids with -1 are defaulted to be empty.