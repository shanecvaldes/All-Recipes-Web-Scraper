
create table CATEGORIES
(
    id INT PRIMARY KEY,
    parent_id INT DEFAULT -1,
    link VARCHAR(255) UNIQUE,
    title VARCHAR(255)

);
create table RECIPES
(
    id INT PRIMARY KEY,
    category_id INT DEFAULT -1,
    link VARCHAR (255) UNIQUE,
    FOREIGN KEY (category_id) REFERENCES CATEGORIES ON DELETE CASCADE,
    title VARCHAR (255)
);

INSERT INTO CATEGORIES (id, link, title)
VALUES (-1, 'https://www.allrecipes.com/', 'HOME PAGE'),
        (0, 'https://www.allrecipes.com/recipes/', 'MAIN CATEGORY');

create table INGREDIENTS
(
    id INT PRIMARY KEY,
    name VARCHAR (255)
);
/*C:/Users/shane/OneDrive/Desktop/'Web Scraper'/db_template.sql*/
