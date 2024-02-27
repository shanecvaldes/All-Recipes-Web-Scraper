TRUNCATE TABLE recipes CASCADE;
TRUNCATE TABLE categories CASCADE;

INSERT INTO CATEGORIES (id, link, title)
VALUES (-1, 'https://www.allrecipes.com/', 'HOME PAGE'),
        (0, 'https://www.allrecipes.com/recipes/', 'MAIN CATEGORY');